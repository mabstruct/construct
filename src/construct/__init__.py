"""CONSTRUCT package.

`__version__` is the single source of truth for the CONSTRUCT version.
`pyproject.toml` reads it dynamically (hatchling), `construct --version`
prints it, and `setup-construct.sh` stamps it into each workspace's
`.construct/VERSION` marker — so the version is set in exactly one place.
"""

__version__ = "0.3.0"
