"""Wrap each schema's data in the standard envelope per data-model spec §4."""

SCHEMA_VERSION = "0.2.0"


def wrap(data: dict, generated_at: str, build_id: str, workspace_id: str | None = None) -> dict:
    env = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "build_id": build_id,
        "data": data,
    }
    if workspace_id is not None:
        env["workspace_id"] = workspace_id
    return env
