"""
Python 3.12+ removed the stdlib `distutils` package entirely (PEP 632).
`undetected-chromedriver` (last released before that removal) still does
`from distutils.version import LooseVersion` at import time, which
raises ModuleNotFoundError on Python 3.12+ (confirmed on 3.14).

Rather than depend on setuptools' own distutils shim — which is fragile
and has itself been dropped in newer setuptools versions — this installs
a minimal, faithful reimplementation of `distutils.version.LooseVersion`
(a small, well-known class) directly into `sys.modules`, so
`undetected_chromedriver`'s import line resolves normally. Call
`ensure_distutils_shim()` before importing undetected_chromedriver
anywhere in this project.
"""
from __future__ import annotations

import re
import sys
import types


class _LooseVersion:
    """Faithful reimplementation of distutils.version.LooseVersion."""

    _component_re = re.compile(r"(\d+|[a-zA-Z]+|\.)")

    def __init__(self, vstring=None):
        self.vstring = ""
        self.version = []
        if vstring:
            self.parse(vstring)

    def parse(self, vstring):
        self.vstring = vstring
        components = [x for x in self._component_re.split(vstring) if x and x != "."]
        for i, obj in enumerate(components):
            try:
                components[i] = int(obj)
            except ValueError:
                pass
        self.version = components

    def __str__(self):
        return self.vstring

    def __repr__(self):
        return f"LooseVersion ('{self}')"

    def _cmp(self, other):
        if isinstance(other, str):
            other = _LooseVersion(other)
        if self.version == other.version:
            return 0
        return -1 if self.version < other.version else 1

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __lt__(self, other):
        return self._cmp(other) < 0

    def __le__(self, other):
        return self._cmp(other) <= 0

    def __gt__(self, other):
        return self._cmp(other) > 0

    def __ge__(self, other):
        return self._cmp(other) >= 0


def ensure_distutils_shim():
    if "distutils" in sys.modules:
        return
    try:
        import distutils  # noqa: F401 -- real distutils, Python < 3.12
        return
    except ModuleNotFoundError:
        pass

    distutils_mod = types.ModuleType("distutils")
    version_mod = types.ModuleType("distutils.version")
    version_mod.LooseVersion = _LooseVersion
    distutils_mod.version = version_mod
    sys.modules["distutils"] = distutils_mod
    sys.modules["distutils.version"] = version_mod
