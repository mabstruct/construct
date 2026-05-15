"""Parse YAML frontmatter from markdown files.

Returns (metadata_dict, body_string). On parse failure, raises ValueError
with a single-line reason; callers convert this to a warning entry.
"""
import yaml


def parse(text: str) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter dict, body text)."""
    if not text.startswith("---"):
        raise ValueError("missing leading frontmatter delimiter '---'")

    # Find closing delimiter
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end == -1:
        raise ValueError("missing closing frontmatter delimiter '---'")

    fm_text = rest[:end]
    body = rest[end + 4:]
    if body.startswith("\n"):
        body = body[1:]

    try:
        meta = yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {e}")

    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter is not a mapping (must be key:value pairs)")

    return meta, body
