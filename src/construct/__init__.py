"""CONSTRUCT package.

Version numbering:

- ``_release.py`` holds the release line (``0.3``) read by hatchling for package metadata.
- ``_build.py`` holds the build stamp (``YYYYMMDDHHMMSS``), regenerated on install/build.
- ``__version__`` is the combined form ``0.3.20260620171439`` used by ``construct --version``
  and stamped into workspace ``.construct/VERSION`` markers.
"""

from construct.versioning import version_string

__version__ = version_string()
