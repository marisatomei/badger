"""Path virtualization (/system -> badge, /state -> .badge_state) and OS/import hooks."""

from __future__ import annotations

import builtins
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BADGE_ROOT = REPO_ROOT / "badge"
APPS_DIR = BADGE_ROOT / "apps"
STATE_DIR = REPO_ROOT / ".badge_state"


def map_system_path(p: str | Path) -> str:
    """Map '/system/...' and remote paths to local badge tree."""
    s = str(p)
    if s.startswith("/system"):
        tail = s[len("/system"):].lstrip("/\\")
        return str(BADGE_ROOT / tail) if tail else str(BADGE_ROOT)
    if s.startswith(":/system"):
        tail = s[len(":/system"):].lstrip("/\\")
        return str(BADGE_ROOT / tail) if tail else str(BADGE_ROOT)
    if s.startswith("/state"):
        tail = s[len("/state"):].lstrip("/\\")
        return str(STATE_DIR / tail) if tail else str(STATE_DIR)
    return s


# Intercept os.chdir, os.listdir, os.rename, os.remove, and open
_real_chdir = os.chdir
_real_listdir = os.listdir
_real_rename = os.rename
_real_remove = os.remove
_real_mkdir = os.mkdir
_real_open = builtins.open
_real_import = builtins.__import__
_orig_find_spec = importlib.machinery.PathFinder.find_spec


def _safe_mkdir(path: Any, mode: int = 0o777) -> None:
    _real_mkdir(map_system_path(path), mode)


def _safe_rename(src: Any, dst: Any) -> None:
    s = map_system_path(src)
    d = map_system_path(dst)
    parent = Path(d).parent
    parent.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "replace"):
        os.replace(s, d)
    else:
        try:
            os.remove(d)
        except OSError:
            pass
        _real_rename(s, d)


def _safe_remove(path: Any) -> None:
    resolved = map_system_path(path)
    if os.path.exists(resolved):
        _real_remove(resolved)


def _safe_chdir(path: str | Path) -> None:
    _real_chdir(map_system_path(path))


def _safe_listdir(path: Any = ".") -> list[str]:
    if isinstance(path, (list, tuple)):
        path = path[0] if path else "."
    return _real_listdir(map_system_path(path))


def _safe_ilistdir(path: Any = "."):
    resolved = Path(map_system_path(path))
    if not resolved.exists():
        return []
    result = []
    for entry in resolved.iterdir():
        type_flag = 0x4000 if entry.is_dir() else 0x8000
        result.append((entry.name, type_flag, 0))
    return result


def _safe_open(file: Any, *args, **kwargs):
    if isinstance(file, (str, Path)):
        file = map_system_path(file)
    return _real_open(file, *args, **kwargs)


class PathList(list):
    def __fspath__(self) -> str:
        return self[0] if self else ""

    def __add__(self, other: Any) -> Any:
        if isinstance(other, str):
            return (self[0] if self else "") + other
        return super().__add__(other)

    def __radd__(self, other: Any) -> Any:
        if isinstance(other, str):
            return other + (self[0] if self else "")
        return super().__radd__(other)


def hooked_find_spec(fullname: str, path: Any = None, target: Any = None):
    spec = _orig_find_spec(fullname, path, target)
    if spec and spec.submodule_search_locations is not None:
        spec.submodule_search_locations = PathList(spec.submodule_search_locations)
    return spec


class DictModule(ModuleType):
    def keys(self) -> Any:
        return getattr(self, "demos", self.__dict__).keys()

    def values(self) -> Any:
        return getattr(self, "demos", self.__dict__).values()

    def items(self) -> Any:
        return getattr(self, "demos", self.__dict__).items()

    def __getitem__(self, k: Any) -> Any:
        d = getattr(self, "demos", self.__dict__)
        return d[k]

    def __iter__(self) -> Any:
        d = getattr(self, "demos", self.__dict__)
        return iter(d)

    def __len__(self) -> int:
        d = getattr(self, "demos", self.__dict__)
        return len(d)


def _safe_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    if "/" in name or "\\" in name:
        p = Path(map_system_path(name))
        if not p.suffix:
            p = p.with_suffix(".py")
        mod_key = p.stem
        spec = importlib.util.spec_from_file_location(mod_key, str(p))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            sys.modules[mod_key] = mod
            spec.loader.exec_module(mod)
            return mod

    try:
        mod = _real_import(name, globals, locals, fromlist, level)
    except ModuleNotFoundError:
        mod = None
        for entry in list(sys.path):
            mapped_entry = Path(map_system_path(entry))
            candidate = mapped_entry / f"{name}.py"
            candidate_src = mapped_entry / "src" / f"{name}.py"
            target_file = candidate if candidate.exists() else (candidate_src if candidate_src.exists() else None)
            if target_file:
                spec = importlib.util.spec_from_file_location(name, str(target_file))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[name] = mod
                    spec.loader.exec_module(mod)
                    break
            candidate_pkg = mapped_entry / name / "__init__.py"
            if candidate_pkg.exists():
                spec = importlib.util.spec_from_file_location(name, str(candidate_pkg))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[name] = mod
                    spec.loader.exec_module(mod)
                    break
        if mod is None:
            raise

    if hasattr(mod, "demos") and isinstance(mod.demos, dict):
        mod.__class__ = DictModule
    return mod


def install_vfs_hooks() -> None:
    """Install OS, builtins, and import hooks for badge path virtualization."""
    importlib.machinery.PathFinder.find_spec = staticmethod(hooked_find_spec)
    os.chdir = _safe_chdir  # type: ignore
    os.listdir = _safe_listdir  # type: ignore
    os.ilistdir = _safe_ilistdir  # type: ignore
    os.rename = _safe_rename  # type: ignore
    os.remove = _safe_remove  # type: ignore
    os.mkdir = _safe_mkdir  # type: ignore
    builtins.open = _safe_open  # type: ignore
    builtins.__import__ = _safe_import  # type: ignore
