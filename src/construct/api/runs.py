"""Starting a run — the one non-capability route on this surface (HTTP-06, D-12).

**Why this route exists at all.** Every other thing a browser can ask for goes
through ``POST /api/capabilities/{cap_id}``, because the capability envelope can
express it. Starting a workflow run is the one operation it structurally cannot:
a capability call is synchronous, and HTTP-06 requires the id to come back
*immediately*, with the run pollable while it is still going. Those two
sentences cannot both be true of one synchronous dispatch, so this is a route
rather than a capability — and it is the only one. Polling and resume stay on the
envelope (``curation.inspect`` / ``curation.review`` and their research siblings),
which is what keeps the non-capability surface exactly one route wide.

**D-12 — a run is a detached subprocess.** Three properties fall out for free,
and each was the reason an alternative was rejected:

* *Crash isolation.* An in-process worker thread dies with the server, so a
  restart would silently kill a run the user was told had started.
* *No cross-thread database question.* The child owns its own sqlite connection
  to the checkpoint; nothing is shared with the request loop.
* *Browser/CLI symmetry.* Both sides become ordinary processes writing the same
  checkpoint file, so "started in the browser, resumed from the CLI" needs no
  mechanism — it is the same mechanism, twice.

A bounded worker pool was rejected for a subtler reason: a run that is *queued
but not started* is a status the checkpoint knows nothing about, so the server
would have to own a second, non-durable status vocabulary beside the one the
inspect capabilities already reconstruct from persisted state.

**D-15 — progress is polled, not streamed.** Server-sent events are Phase 21's
call. Polling costs no new server surface, works identically for a run this
server did not start, and degrades to reloading the page; streaming means
long-lived connections and reconnection logic inside the phase everything
downstream already depends on.

**D-26 — the child's error stream goes to a file under the workspace, never to a
pipe.** This is the project's named silent-failure mode wearing a new costume. A
bad credential, an import error or a wrong working directory makes the child die
before it writes any checkpoint, and the run then reads as *no such run* forever
— indistinguishable from a run that was never started. So the start response
names ``RUN_LOG_RELPATH`` up front, the path is derivable from the run id alone,
and a failed start leaves a readable trace exactly where the caller was told to
look. A pipe would be worse than useless: nobody reads it, and once its buffer
fills the child blocks.

**Both** of the child's streams are captured, and the tempting alternative is
worth naming because it was measured and rejected. Sending only ``stderr`` looks
tidier — a file that holds nothing but errors — but ``construct.cli`` reports a
failed capability with ``typer.echo(f"ERROR {exc}")``, which is **stdout**. A
stderr-only capture would therefore discard exactly the sentence a failed run
needs to leave behind, while faithfully preserving the logging warnings a
*healthy* run emits. The cost of capturing both is that a non-empty log no longer
means "something went wrong" — a degraded-but-fine run writes to it too — so this
file answers "what did this run say", and the *run's status* is read from the
checkpoint by the inspect capabilities, where it belongs.

**The API layer never drives the workflow graph directly.** A resume is submitted
through the review capabilities (``curation.review`` / ``research.review``),
which wrap the payload before handing it to LangGraph. This is not a layering
preference, it is a correctness requirement: a bare id-keyed dictionary handed to
``Command(resume=...)`` is read as an *interrupt-id* mapping — a proposal id has
exactly the shape of an interrupt id — so the graph consumes it as an **empty**
resume, and the run stays paused with zero writes and no error. A well-formed
response for a decision that was silently discarded is the worst available
outcome, and routing every resume through the review capabilities is what makes
it unreachable from here.

**T-19-09 / T-19-25 — what reaches the argument vector.** The spawn is a list of
arguments with no shell anywhere; the workflow name is checked against a set
*derived from the registry's run capabilities*, so an unregistered command group
is unreachable by construction rather than by an opt-out (which is what keeps
``spike run --tool-path``, a remote-code-execution primitive, off this surface —
it is not in the registry at all); and the run id is kebab-validated by the
existing ``construct.llm.curation_run._validate_run_id`` before it is placed in
the vector. The workspace is addressed by id and resolved by the same seam helper
the envelope uses, and any path-shaped key is refused before anything else runs.

**T-19-10 is accepted, not mitigated.** Nothing bounds how many runs a caller may
start; ``COVERAGE.md`` records the acceptance and the condition under which it
expires.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, model_validator

from construct.api.errors import status_for_seam_error
from construct.capabilities.catalog import get_registry
from construct.capabilities.errors import CapabilityError
from construct.capabilities.results import sanitize_exception
from construct.capabilities.workspaces import (
    PATH_SHAPED_KEYS,
    WORKSPACE_ID_KEY,
    launch_install_root,
    resolve_workspace_id,
)


#: Where a run's captured error output lives, relative to its workspace, as a
#: format string over the run id (D-26).
#:
#: Under ``.construct/workflow/`` beside ``curation-run.sqlite`` and the
#: ``daily/`` receipts, because it is durable state about a run rather than a
#: temporary file — an operator looking for "what this run left behind" should
#: find all of it in one tree.
#:
#: It is a *derivation* from the run id, not a value the server has to remember.
#: That is what lets the start response advertise the path before the child has
#: written a byte, and lets a caller holding only a run id find the log later
#: without a second round trip — including from a process that did not start it.
RUN_LOG_RELPATH = ".construct/workflow/logs/{run_id}.err"

#: The suffix that marks a capability as a workflow *run-start*.
#:
#: The startable set is computed from this against the live registry, never
#: hand-listed: a hand-listed set is one more table a future registration has to
#: trip, and the failure mode of forgetting it is a capability that exists,
#: dispatches over the envelope, and is silently unstartable.
_RUN_CAPABILITY_SUFFIX = ".run"

#: ``request field -> the CLI flag that carries it`` for the optional,
#: workflow-specific fields a run capability may declare.
#:
#: Hand-written, and the reason is worth stating rather than hiding: the flag
#: *spelling* is genuinely not derivable. ``research.run`` declares
#: ``provider_override`` and the CLI spells it ``--provider``, so a generic
#: ``field -> --field-with-hyphens`` rule would emit an option no command has.
#: What *is* derived is the part that matters for safety — whether a given
#: workflow accepts the field at all is read from that capability's own input
#: model, so sending it to a workflow that never declared it is refused rather
#: than passed through to an argument vector.
_OPTION_FLAG: dict[str, str] = {"provider_override": "--provider"}


def startable_workflows() -> dict[str, str]:
    """``workflow name -> capability id``, derived from the live registry.

    ``curation.run`` is startable as ``"curation"``. The mapping is recomputed
    per request rather than cached at import, for the same reason D-02 rescans
    the install root per request: a set frozen at launch answers for the process
    that started, not for the registry as it is.
    """
    return {
        capability.id[: -len(_RUN_CAPABILITY_SUFFIX)]: capability.id
        for capability in get_registry().list()
        if capability.id.endswith(_RUN_CAPABILITY_SUFFIX)
    }


class RunStartRequest(BaseModel):
    """The run-start body. ``extra="forbid"``, like every model in this project.

    ``workspace_id``, never a path — HTTP-03's literal wording is that this trust
    boundary refuses caller-supplied filesystem paths, and the model-level
    refusal below makes that true with the envelope's own reason rather than
    pydantic's generic "extra inputs are not permitted".
    """

    model_config = ConfigDict(extra="forbid")

    workflow: str
    workspace_id: str
    #: The one workflow-specific field a run capability declares today. Accepted
    #: only for a workflow whose own input model declares it (checked in
    #: :func:`start_run` against the registry), so this is not a field the route
    #: forwards on trust.
    provider_override: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _refuse_path_shaped_keys(cls, data):
        """Refuse a path-shaped key with the envelope's own reason (D-10).

        A ``mode="before"`` validator runs *ahead* of ``extra="forbid"``, which
        is the whole point: ``extra="forbid"`` would reject ``workspace_path``
        too, but with a reason that says nothing about ``workspace_id`` being
        the way to address a workspace. Two refusals of the same mistake giving
        two different explanations is the small, cheap fork this project keeps
        declining to introduce.
        """
        if not isinstance(data, dict):
            return data
        offending = sorted(set(data) & PATH_SHAPED_KEYS)
        if offending:
            raise ValueError(
                "path-shaped payload keys are refused at the HTTP boundary: "
                f"{', '.join(offending)} — address a workspace by id with "
                f"'{WORKSPACE_ID_KEY}' instead"
            )
        return data


class RunStarted(BaseModel):
    """What a caller gets back the instant the child is running.

    ``checkpoint_id`` is **always ``None`` here**, and it is present anyway. At
    the moment this is built the child has not reached its first node, so there
    is no checkpoint to name — but the field is what a later phase's optimistic
    concurrency needs, and a response shape that grows a field later is a shape
    every existing caller has to be told about. Declaring it null now costs
    nothing and forecloses nothing; the poll responses
    (``curation.inspect`` and friends) carry the real handle.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow: str
    #: Not the run's *outcome*. It is the one thing this response can honestly
    #: claim: a process was started. Everything after that is read from the
    #: checkpoint by the inspect capabilities, which own the run's real status
    #: vocabulary — inventing a second one here is exactly what D-12 rejected the
    #: worker pool for.
    status: str = "starting"
    #: Relative to the workspace, so it is meaningful to a caller that has never
    #: been told an absolute path and never should be (T-19-05).
    log_path: str
    #: The child's process id. Present because it is the only thing that
    #: distinguishes "the run has not written a checkpoint yet" from "the run
    #: died before it could" during the first second of a run's life — the exact
    #: window D-26 exists to make legible.
    pid: int
    checkpoint_id: str | None = None


#: Where the run-start route lives. Recorded in ``COVERAGE.md``'s
#: non-capability-routes table, which a contract guard parses, so this path
#: existing without a row there is a failing test rather than an undocumented
#: surface (D-20).
RUNS_ROUTE = "/api/runs"

#: The CLI option every run-start command spells for its workspace.
#:
#: The *spelling* is the CLI's, not the capability's — the capability declares
#: ``workspace_path`` — and it is shared by ``curation run``, ``research run``
#: and ``daily run``. Named here rather than inlined so that a run command which
#: ever spells it differently has to walk past this constant.
_WORKSPACE_FLAG = "--workspace"

#: The CLI option carrying the caller-minted run handle (D-12).
_RUN_ID_FLAG = "--run-id"

runs_router = APIRouter()

#: Child handles this process has started and not yet waited on.
#:
#: This is **not** run state. A run's state is its checkpoint, which is why this
#: list is empty after a server restart while every run it started stays
#: addressable — the property D-12 was chosen for. It exists only so a long-lived
#: server does not accumulate zombie process-table entries for children it will
#: never wait on.
_SPAWNED: list[subprocess.Popen] = []


def _reap() -> None:
    """Wait on every child that has already exited, and forget it."""
    for child in list(_SPAWNED):
        if child.poll() is not None:
            _SPAWNED.remove(child)


def _mint_run_id(input_model: type[BaseModel], workflow: str) -> str:
    """Mint a run id with the generator the workflow's own module already owns.

    Not a new scheme. ``construct.llm.curation_run._new_run_id`` is the canonical
    form — a UTC stamp joined with ``-`` rather than ISO ``T`` so the handle
    satisfies ``KEBAB_CASE_PATTERN``, plus a ``secrets`` suffix — and
    ``research_run`` and ``daily_run`` each define the same function with their
    own prefix. Reaching the right one is *derived*: a capability declares its
    ``input_model``, and that model is defined in the module that owns the
    workflow (deliberately, to avoid a circular import through ``catalog.py``),
    so the module is registry data rather than a lookup table to maintain.

    Using one workflow's generator for all three would have been simpler and
    would have written ``cur-`` on the front of every research run — a handle
    that says the wrong thing about what it names.

    The minted id is then run through the *existing* validator before it can
    reach an argument vector (T-19-09). Validating a value this function just
    produced looks redundant and is not: it is the assertion that the generator
    and the boundary agree, and it is the only thing standing between a future
    change to a generator and a run id that reaches ``subprocess`` unchecked.
    """
    from construct.llm.curation_run import _validate_run_id

    module = importlib.import_module(input_model.__module__)
    generator = getattr(module, "_new_run_id", None)
    if generator is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"workflow '{workflow}' declares no run-id generator, so a run "
                "id cannot be minted before the run starts — register the "
                "capability's module with one rather than starting an "
                "unaddressable run"
            ),
        )
    run_id = generator()
    try:
        _validate_run_id(run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"the run-id generator for workflow '{workflow}' produced a "
                "handle the run-id validator rejects; refusing to place it in "
                "a process argument list"
            ),
        ) from exc
    return run_id


def _child_environment() -> dict[str, str]:
    """The child's environment: this process's, plus a pin to this process's code.

    Inheriting is deliberate — a workflow needs whatever credential variables
    the user launched the server with, and re-deriving them here would be a
    second configuration path to keep in step with the first.

    The pin is the part worth explaining. ``sys.executable`` is the interpreter
    running *this* process, which is right; but ``-m construct.cli`` then imports
    whatever ``construct`` that interpreter's environment resolves — for an
    editable install, the checkout the install points at, which is **not
    necessarily the checkout this server is running from**. A server started
    from one tree would spawn children running another tree's code, and the two
    would disagree silently. Prepending this process's own package root to
    ``PYTHONPATH`` makes the child import the code its parent imported. It is
    the same argument ``tests/integration/test_surface_parity.py::_cli`` makes
    for pinning ``PYTHONPATH`` instead of hardcoding an interpreter path.
    """
    import construct

    environment = dict(os.environ)
    package_root = str(Path(construct.__file__).resolve().parent.parent)
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        package_root + os.pathsep + existing if existing else package_root
    )
    return environment


@runs_router.post(RUNS_ROUTE)
async def start_run(body: RunStartRequest) -> RunStarted:
    """Start a workflow run and answer with its id, without waiting for it.

    The order below is the control, not an implementation detail:

    1. the workflow name is resolved against the **registry-derived** startable
       set, so an unknown name never reaches step 2;
    2. ``workspace_id`` is resolved by the same seam helper the envelope uses —
       shape gate first, allowlist second, both before any path is built
       (T-19-03);
    3. the run id is minted and kebab-validated;
    4. only then is an argument *list* assembled and a process started.

    Every refusal leaves this function as an ``HTTPException``, which
    ``install_error_handlers`` renders through ``api/errors.py::error_body`` —
    the same one body as the envelope, the guard and the framework's own 404
    (HTTP-04). There is no second body builder here, deliberately.
    """
    startable = startable_workflows()
    capability_id = startable.get(body.workflow)
    if capability_id is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"unknown workflow '{body.workflow}' — startable workflows: "
                f"{', '.join(sorted(startable)) or '<none>'}"
            ),
        )

    capability = get_registry().get(capability_id)
    declared = set(capability.input_model.model_fields)
    if "run_id" not in declared:
        raise HTTPException(
            status_code=422,
            detail=(
                f"workflow '{body.workflow}' declares no 'run_id', so its run "
                "cannot be addressed before it finishes; it is not startable "
                "over HTTP"
            ),
        )
    if capability.cli_name is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"workflow '{body.workflow}' declares no CLI name, so there is "
                "no command for a detached run to invoke"
            ),
        )

    options: list[str] = []
    for field, flag in _OPTION_FLAG.items():
        value = getattr(body, field, None)
        if value is None:
            continue
        # Derived, not trusted: whether *this* workflow accepts the field is
        # read from its own declared input model, so a field that belongs to
        # one workflow cannot be forwarded into another's argument vector.
        if field not in declared:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"workflow '{body.workflow}' does not declare '{field}'"
                ),
            )
        options.extend([flag, value])

    try:
        workspace = resolve_workspace_id(
            capability_id, body.workspace_id, launch_install_root()
        )
    except CapabilityError as exc:
        status = status_for_seam_error(exc)
        if status is None:
            raise HTTPException(
                status_code=500, detail=sanitize_exception(exc)
            ) from exc
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    run_id = _mint_run_id(capability.input_model, body.workflow)
    log_relpath = RUN_LOG_RELPATH.format(run_id=run_id)
    log_path = workspace / log_relpath

    argv = [
        sys.executable,
        "-m",
        "construct.cli",
        *capability.cli_name.split("."),
        _WORKSPACE_FLAG,
        str(workspace),
        _RUN_ID_FLAG,
        run_id,
        *options,
    ]

    _reap()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Opened here and closed immediately after the fork: the child holds its
        # own duplicated descriptor, so the parent keeping one open would only
        # delay the file being flushed to a reader.
        with log_path.open("wb") as log_handle:
            child = subprocess.Popen(  # noqa: S603 — a list, and no shell (T-19-09)
                argv,
                # Spelled out rather than left to the default. The default is
                # already ``False``, but "the argument vector is never handed to
                # a shell" is the security property of this whole module, and a
                # property that holds only by inherited default is one a reader
                # has to know the default to verify.
                shell=False,
                cwd=str(launch_install_root()),
                env=_child_environment(),
                stdin=subprocess.DEVNULL,
                # D-26: never ``subprocess.PIPE`` for either stream. Nobody reads
                # it, and once its buffer fills the child blocks forever — a run
                # that is neither running nor finished. Both streams land in the
                # one file because the CLI reports a failure on *stdout*; see the
                # module docstring.
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except Exception as exc:  # noqa: BLE001 — the boundary, deliberately broad
        # Sanitized, never ``str(exc)``: an ``OSError`` here embeds the absolute
        # path it failed on (T-18-10), and this surface answers a browser.
        raise HTTPException(status_code=500, detail=sanitize_exception(exc)) from exc

    _SPAWNED.append(child)

    return RunStarted(
        run_id=run_id,
        workflow=body.workflow,
        log_path=log_relpath,
        pid=child.pid,
    )
