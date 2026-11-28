"""Design inputs: HDL files plus include directories, defines and SystemVerilog mode.

A `DesignSource` is what the engines read into Yosys. It can be built from
plain paths or from simulator-style file lists (``.f`` files), which use the
usual VCS / Xcelium / Verilator conventions:

* one file per token; ``//`` and ``#`` start a comment
* ``+incdir+<dir>[+<dir>...]`` and ``-I<dir>`` / ``-I <dir>`` add include directories
* ``+define+<NAME>[=<value>][+...]`` and ``-D<NAME>[=<value>]`` add macros
* ``-v <file>`` adds a library file
* ``-f <list>`` nests a list whose relative paths resolve from the current
  directory; ``-F <list>`` nests one whose paths resolve from that list's folder
* ``$VAR`` / ``${VAR}`` environment variables are expanded

Other ``+``/``-`` options (``-y``, ``+libext+``, ``-timescale`` ...) are not
supported; they are reported in `FileList.ignored` and otherwise skipped.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from openlec.engine.yosys_runner import quote_path

SV_SUFFIXES = frozenset({".sv", ".svh"})

_DEFINE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_TOKEN_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'|(\S+)')
# Unsupported options whose next token is their argument (skipped together).
_UNSUPPORTED_WITH_ARG = frozenset({"-y", "-l", "-o", "-top", "-timescale"})


class DesignSourceError(ValueError):
    """A file list or design-source option that cannot be used."""


def _check_define(name: str, value: str | None) -> None:
    if not _DEFINE_NAME_RE.match(name):
        raise DesignSourceError(f"Invalid macro name '{name}'.")
    if value is not None and (not value or re.search(r'[\s"]', value)):
        raise DesignSourceError(
            f"Unsupported value for macro '{name}': '{value}' "
            "(must be non-empty, with no spaces or double quotes)."
        )


def parse_define(text: str) -> tuple[str, str | None]:
    """Split ``NAME`` or ``NAME=value`` and validate it."""
    name, sep, value = text.partition("=")
    parsed = value if sep else None
    _check_define(name, parsed)
    return name, parsed


def _include_arg(directory: Path) -> str:
    """Yosys keeps quotes as part of an -I value, so the path must have no spaces."""
    text = directory.as_posix()
    if '"' in text:
        raise DesignSourceError(f"Unsupported character '\"' in include directory: {text}")
    if not re.search(r"\s", text):
        return f"-I{text}"
    try:
        rel = Path(os.path.relpath(directory)).as_posix()  # Yosys runs in our cwd
    except ValueError:  # different drive on Windows
        rel = text
    if not re.search(r"\s", rel):
        return f"-I{rel}"
    raise DesignSourceError(
        f"Include directory '{text}' contains a space, which Yosys's -I option "
        "cannot accept. Use a directory path without spaces (or run OpenLEC from "
        "a folder so that the relative path has none)."
    )


@dataclass(frozen=True)
class DesignSource:
    """The files that make up one side (golden or revised) of a comparison."""

    files: tuple[Path, ...]
    include_dirs: tuple[Path, ...] = ()
    defines: tuple[tuple[str, str | None], ...] = ()
    sv: bool = False  # parse every file as SystemVerilog (.sv/.svh always are)

    @classmethod
    def from_paths(
        cls,
        files: Iterable[str | Path],
        include_dirs: Iterable[str | Path] = (),
        defines: Mapping[str, str | None] | None = None,
        sv: bool = False,
    ) -> DesignSource:
        items = tuple((defines or {}).items())
        for name, value in items:
            _check_define(name, value)
        return cls(
            files=tuple(Path(f) for f in files),
            include_dirs=tuple(Path(d) for d in include_dirs),
            defines=items,
            sv=sv,
        )

    def is_sv(self, path: Path) -> bool:
        return self.sv or path.suffix.lower() in SV_SUFFIXES

    def missing(self) -> list[tuple[str, Path]]:
        """(kind, path) for every file or include directory that does not exist."""
        gone: list[tuple[str, Path]] = [("file", f) for f in self.files if not f.is_file()]
        gone += [("include directory", d) for d in self.include_dirs if not d.is_dir()]
        return gone

    def read_script(self) -> str:
        """Yosys commands that load this design, starting from a clean macro state."""
        if not self.files:
            raise DesignSourceError("No design files given.")
        options = [_include_arg(d) for d in self.include_dirs]
        options += [f"-D{n}" if v is None else f"-D{n}={v}" for n, v in self.defines]
        # Macros from earlier read_verilog calls persist; clear them so the golden
        # and revised designs cannot see each other's `define`s.
        lines = ["design -reset-vlog"]
        for path in self.files:
            flags = (["-sv"] if self.is_sv(path) else []) + options
            lines.append(" ".join(["read_verilog", *flags, quote_path(path)]))
        return "\n".join(lines) + "\n"

    def cache_key(self) -> tuple[object, ...]:
        """Changes whenever an input file changes (used to cache Yosys stats)."""

        def mtime(path: Path) -> int:
            try:
                return path.stat().st_mtime_ns
            except OSError:
                return -1

        return (
            tuple((str(f), mtime(f)) for f in self.files),
            tuple(str(d) for d in self.include_dirs),
            self.defines,
            self.sv,
        )

    def __str__(self) -> str:
        shown = ", ".join(str(f) for f in self.files[:3])
        extra = len(self.files) - 3
        return shown + (f" (+{extra} more)" if extra > 0 else "")


NetlistLike = str | Path | DesignSource


def as_source(netlist: NetlistLike) -> DesignSource:
    """Accept a single path wherever a DesignSource is expected."""
    if isinstance(netlist, DesignSource):
        return netlist
    return DesignSource(files=(Path(netlist),))


# ---------------------------------------------------------------- file lists
@dataclass
class FileList:
    files: list[Path] = field(default_factory=list)
    include_dirs: list[Path] = field(default_factory=list)
    defines: dict[str, str | None] = field(default_factory=dict)
    ignored: list[str] = field(default_factory=list)  # unsupported options, as written


def parse_filelist(path: str | Path, relative_to_list: bool = False) -> FileList:
    """Parse a ``.f`` file list (see the module docstring for the syntax).

    ``relative_to_list`` selects ``-F`` semantics (relative paths resolve from
    the list's own folder) instead of ``-f`` semantics (from the current directory).
    """
    result = FileList()
    _parse_into(Path(path), relative_to_list, result, stack=())
    return result


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.split("//", 1)[0]
        if line.lstrip().startswith("#"):
            continue
        for m in _TOKEN_RE.finditer(line):
            token = next(g for g in m.groups() if g is not None)
            out.append(os.path.expandvars(token))
    return out


def _parse_into(path: Path, relative_to_list: bool, out: FileList, stack: tuple[Path, ...]) -> None:
    resolved = path.resolve()
    if resolved in stack:
        chain = " -> ".join(str(p) for p in (*stack, resolved))
        raise DesignSourceError(f"File list includes itself: {chain}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DesignSourceError(f"Cannot read file list {path}: {exc.strerror or exc}") from None

    base = path.parent if relative_to_list else Path.cwd()

    def resolve(token: str) -> Path:
        p = Path(token)
        return p if p.is_absolute() else base / p

    tokens = _tokens(text)
    i = 0

    def take_arg(option: str) -> str:
        nonlocal i
        if i + 1 >= len(tokens):
            raise DesignSourceError(f"{path}: option {option} needs an argument")
        i += 1
        return tokens[i]

    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("+incdir+"):
            out.include_dirs += [resolve(d) for d in tok[len("+incdir+"):].split("+") if d]
        elif tok.startswith("+define+"):
            for item in tok[len("+define+"):].split("+"):
                if item:
                    name, value = parse_define(item)
                    out.defines[name] = value
        elif tok in ("-f", "-F"):
            nested = take_arg(tok)
            _parse_into(resolve(nested), tok == "-F", out, (*stack, resolved))
        elif tok == "-v":
            out.files.append(resolve(take_arg(tok)))
        elif tok == "-I":
            out.include_dirs.append(resolve(take_arg(tok)))
        elif tok.startswith("-I"):
            out.include_dirs.append(resolve(tok[2:]))
        elif tok == "-D":
            name, value = parse_define(take_arg(tok))
            out.defines[name] = value
        elif tok.startswith("-D"):
            name, value = parse_define(tok[2:])
            out.defines[name] = value
        elif tok in _UNSUPPORTED_WITH_ARG:
            out.ignored.append(f"{tok} {take_arg(tok)}")
        elif tok.startswith(("+", "-")):
            out.ignored.append(tok)
        else:
            out.files.append(resolve(tok))
        i += 1
