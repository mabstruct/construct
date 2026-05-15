"""Compute a deterministic build_id over data file contents.

Excludes envelope `generated_at` from the hash so two runs against
unchanged workspace state produce the same build_id.
"""
import hashlib
import json


def compute(files: dict[str, dict]) -> str:
    """files: {relative_path: data_dict_without_envelope}.

    Returns 8-char hex truncation of sha256 over sorted concatenation.
    """
    h = hashlib.sha256()
    for path in sorted(files.keys()):
        h.update(path.encode("utf-8"))
        h.update(b"\0")
        # Use sorted-keys serialisation for determinism
        h.update(json.dumps(files[path], sort_keys=True, ensure_ascii=False).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:8]
