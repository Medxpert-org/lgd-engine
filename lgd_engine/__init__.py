"""lgd-engine: LGD (有籍有证有门禁) minimal kernel.

Version: 0.1.0
Domain-agnostic gate + memory + judge skeleton, with the 510(k) change
classification judge as the first concrete domain adapter.
"""

try:  # single source of truth: the installed distribution version
    from importlib.metadata import version as _dist_version

    __version__ = _dist_version("lgd-engine")
except Exception:  # source tree without an installed distribution
    __version__ = "0.0.0"
__all__ = ["__version__"]
