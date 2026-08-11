#!/usr/bin/env python3
"""Read-only, low-resource audit of versioned project files.

The command deliberately has no output-file option.  It only reads the tree
and writes a JSON or Markdown report to stdout::

    python3 audit_versions.py summary PROJECT
    python3 audit_versions.py manifest PROJECT --format markdown

``summary`` reports metadata and storage accounting without reading file
contents.  ``manifest`` additionally computes a complete SHA-256 for every
regular file that was readable.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence


# These are directory *names*, rather than paths.  A report always includes
# this list and the concrete paths skipped in the current tree.  The list is
# intentionally conservative: it contains generated/dependency trees that
# are normally recoverable from source control or a package manager.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".cache",
    "coverage",
    "DerivedData",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".gradle",
    "target",
)
DEFAULT_EXCLUDE_SET = frozenset(DEFAULT_EXCLUDES)

# A version token is accepted in a directory name when it occupies the whole
# name, and in a file name when it has an alphanumeric boundary.  ``PRD-001``
# is deliberately not a version token: PRD identifiers are frequently not
# release numbers.  The final look-ahead prevents a three-component match
# from silently accepting the ``v1.2.3`` part of ``v1.2.3.4``.
VERSION_TOKEN_RE = re.compile(
    r"(?i)(?<![a-z0-9])(?:v|version|release)[ _.-]*"
    r"(\d+)(?:[._-](\d+))?(?:[._-](\d+))?"
    r"(?![a-z0-9])(?!(?:[._-])\d)"
)
VERSION_DIRECTORY_RE = re.compile(
    r"(?i)^(?:v|version|release)[ _.-]*"
    r"(\d+)(?:[._-](\d+))?(?:[._-](\d+))?$"
)

HASH_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_FILES = 100_000
DEFAULT_MAX_ENTRIES = 1_000_000
ALLOCATED_BLOCK_BYTES = 512  # st_blocks is specified in 512-byte units.
SCHEMA_VERSION = "1.0"
SCANNER_VERSION = "2.0"
STORAGE_NOTE = (
    "logical_bytes is the apparent file size; allocated_bytes uses st_blocks "
    "when available (null means unavailable) and is folded by (device, inode) for hard links. APFS/COW "
    "clones can share physical blocks without sharing an inode, so this is an "
    "estimate of per-file allocation rather than unique physical storage."
)

# Keep references to the standard functions.  Tests and callers may wrap
# ``os.scandir`` to exercise race/error paths; capability detection should not
# mistake such a wrapper for a platform that lacks descriptor support.
_ORIGINAL_SCANDIR = os.scandir
_ORIGINAL_OPEN = os.open


class CapabilityError(RuntimeError):
    """The descriptor/no-follow primitives required for a safe scan failed."""


class _ValidatedRoot(type(Path())):
    """Path value carrying the first ``lstat`` snapshot used for validation.

    ``Path`` instances are immutable, so a tiny concrete-path subclass lets
    :func:`validate_root` preserve the trusted identity without changing its
    long-standing return type.  The snapshot is consumed by ``TreeScanner``
    before it opens anything; if the path now names another directory the
    scan fails closed instead of silently auditing the replacement.
    """

    def __new__(
        cls,
        path: Path | str,
        trusted_stat: os.stat_result,
    ) -> "_ValidatedRoot":
        value = super().__new__(cls, path)
        value._trusted_stat = trusted_stat
        return value

    def __init__(
        self,
        path: Path | str,
        trusted_stat: os.stat_result,
    ) -> None:
        # Python 3.13 moved concrete Path parsing into ``__init__``.  Older
        # versions inherit ``object.__init__`` and must not receive arguments.
        # Accept the trusted snapshot in both cases, but only forward the path
        # when the runtime provides a real pathlib initializer.
        if type(Path()).__init__ is not object.__init__:
            super().__init__(path)

    def with_segments(self, *pathsegments: Path | str) -> Path:
        """Return ordinary paths for descendants on Python 3.12+.

        The trusted stat belongs only to the validated root.  Propagating this
        subclass through ``/`` would make pathlib feed child path segments into
        the snapshot constructor on newer Python versions.
        """

        return Path(*pathsegments)


class HashStabilityError(OSError):
    """A hash was read from a descriptor whose metadata was not stable."""

    def __init__(self, err: int, message: str, stability_status: str) -> None:
        super().__init__(err, message)
        self.stability_status = stability_status


def _detect_capabilities() -> tuple[dict[str, bool], list[str]]:
    """Return conservative capability facts without touching the tree.

    Static support tables are only a first check.  Actual calls still catch
    ``TypeError``/``NotImplementedError`` because embedded Python builds and
    monkey-patched platform shims can disagree with those tables.
    """

    gaps: list[str] = []
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    supports_fd = getattr(os, "supports_fd", set())
    try:
        dir_fd_open = _ORIGINAL_OPEN in supports_dir_fd
    except (TypeError, NotImplementedError):
        dir_fd_open = False
    try:
        scandir_fd = _ORIGINAL_SCANDIR in supports_fd
    except (TypeError, NotImplementedError):
        scandir_fd = False
    try:
        stat_dir_fd = getattr(os, "stat", None) in supports_dir_fd
    except (TypeError, NotImplementedError):
        stat_dir_fd = False
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    capabilities = {
        "dir_fd": dir_fd_open and hasattr(os, "open"),
        "scandir_fd": scandir_fd and hasattr(os, "scandir"),
        "o_nofollow": isinstance(nofollow, int) and nofollow != 0,
        "o_directory": isinstance(directory, int) and directory != 0,
        "fstat": hasattr(os, "fstat"),
        "stat_dir_fd": stat_dir_fd,
    }
    if not capabilities["dir_fd"]:
        gaps.append("dir_fd/openat is unavailable")
    if not capabilities["scandir_fd"]:
        gaps.append("os.scandir(fd) is unavailable")
    if not capabilities["o_nofollow"]:
        gaps.append("O_NOFOLLOW is unavailable")
    if not capabilities["o_directory"]:
        gaps.append("O_DIRECTORY is unavailable")
    if not capabilities["fstat"]:
        gaps.append("fstat is unavailable")
    if not capabilities["stat_dir_fd"]:
        gaps.append("descriptor-relative stat is unavailable")
    return capabilities, gaps


def _identity(value: object) -> tuple[int, int] | None:
    """Return a valid device/inode pair, or ``None`` when it is unknown.

    A missing or zero identity cannot safely establish that a path is still
    inside the originally opened tree, so callers fail closed instead of
    treating it as a real identity.
    """

    try:
        device = int(getattr(value, "st_dev"))
        inode = int(getattr(value, "st_ino"))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    if device <= 0 or inode <= 0:
        return None
    return device, inode


def _metadata_signature(value: object) -> tuple[tuple[int, int], int, int, int, int]:
    """Capture fields needed to prove a manifest hash was stable."""

    identity = _identity(value)
    if identity is None:
        raise CapabilityError("file identity (device/inode) is missing or zero")
    missing = object()
    size = getattr(value, "st_size", missing)
    mtime_ns = getattr(value, "st_mtime_ns", missing)
    ctime_ns = getattr(value, "st_ctime_ns", missing)
    mode = getattr(value, "st_mode", missing)
    if missing in (size, mtime_ns, ctime_ns, mode):
        raise CapabilityError("file size/mtime/ctime/mode metadata is unavailable")
    try:
        return identity, int(size), int(mtime_ns), int(ctime_ns), int(mode)
    except (TypeError, ValueError, OverflowError) as error:
        raise CapabilityError("file metadata is not numeric") from error


def _canonical_version(groups: Sequence[str | None]) -> str:
    """Return a normalized heuristic label (never a source-of-truth name)."""

    parts = [str(int(part)) for part in groups if part is not None]
    return "v" + ".".join(parts)


def version_from_directory(name: str) -> str | None:
    """Return the exact directory token when *name* is version-labelled.

    The original spelling is intentionally retained.  A normalized heuristic
    is available from :func:`normalized_version_from_directory`; callers must
    not use it to rename or align project artifacts.
    """

    match = VERSION_DIRECTORY_RE.fullmatch(name)
    return match.group(0) if match else None


def normalized_version_from_directory(name: str) -> str | None:
    """Return a normalized heuristic for a version-labelled directory."""

    match = VERSION_DIRECTORY_RE.fullmatch(name)
    return _canonical_version(match.groups()) if match else None


def _filename_version_matches(name: str) -> list[tuple[str, str]]:
    """Return ``(raw_token, normalized_token)`` pairs in source order."""

    matches: list[tuple[str, str]] = []
    for match in VERSION_TOKEN_RE.finditer(name):
        raw = match.group(0)
        normalized = _canonical_version(match.groups())
        pair = (raw, normalized)
        if pair not in matches:
            matches.append(pair)
    return matches


def versions_from_filename(name: str) -> list[str]:
    """Return exact version labels found in a filename, in source order."""

    return [raw for raw, _normalized in _filename_version_matches(name)]


def normalized_versions_from_filename(name: str) -> list[str]:
    """Return normalized version heuristics found in a filename."""

    labels: list[str] = []
    for _raw, normalized in _filename_version_matches(name):
        if normalized not in labels:
            labels.append(normalized)
    return labels


def version_from_filename(name: str) -> str | None:
    """Return the first version label found in *name*, if any."""

    labels = versions_from_filename(name)
    return labels[0] if labels else None


def normalized_version_from_filename(name: str) -> str | None:
    """Return the first normalized filename heuristic, if any."""

    labels = normalized_versions_from_filename(name)
    return labels[0] if labels else None


def _allocated_bytes(file_stat: os.stat_result) -> int | None:
    """Read allocated bytes without assuming a platform-specific stat field."""

    blocks = getattr(file_stat, "st_blocks", None)
    if blocks is None:
        return None
    try:
        value = int(blocks)
        return value * ALLOCATED_BLOCK_BYTES if value >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def file_sha256(
    path: Path | str,
    expected_stat: os.stat_result | None = None,
    *,
    dir_fd: int | None = None,
) -> str:
    """Compute a complete SHA-256 in bounded memory without following swaps.

    ``O_NOFOLLOW`` prevents a path replaced by a symlink between the scan and
    hash phases from redirecting the read on platforms that provide it.
    ``fstat`` verifies that the opened descriptor is still the regular file
    identified during the no-follow scan.  Hashing the descriptor (rather than
    reopening the path) then remains safe if the directory entry is replaced
    while the hash is in progress.
    """

    flags = os.O_RDONLY
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(nofollow, int) or nofollow == 0:
        raise CapabilityError("O_NOFOLLOW is unavailable")
    flags |= nofollow
    try:
        descriptor = os.open(path, flags, dir_fd=dir_fd)
    except (TypeError, NotImplementedError) as error:
        raise CapabilityError("descriptor-relative open is unavailable") from error
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise OSError(errno.ELOOP, "opened path is not a regular file")
        if expected_stat is not None:
            expected_identity = _identity(expected_stat)
            opened_identity = _identity(opened_stat)
            if expected_identity is None or opened_identity is None:
                raise CapabilityError("file identity (device/inode) is missing or zero")
            if opened_identity != expected_identity:
                raise HashStabilityError(
                    errno.ESTALE,
                    "file replaced between scan and hash",
                    "replaced",
                )

        hasher = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _stable_file_sha256(
    path: Path | str,
    expected_stat: os.stat_result,
    *,
    dir_fd: int | None = None,
) -> str:
    """Hash one opened descriptor and reject in-place metadata changes.

    The descriptor is opened with no-follow semantics and never reopened
    during the read.  Both the scan metadata and the descriptor's final
    ``fstat`` must match identity, size, mtime, ctime, and mode.
    """

    flags = os.O_RDONLY
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(nofollow, int) or nofollow == 0:
        raise CapabilityError("O_NOFOLLOW is unavailable")
    flags |= nofollow
    try:
        descriptor = os.open(path, flags, dir_fd=dir_fd)
    except (TypeError, NotImplementedError) as error:
        raise CapabilityError("descriptor-relative open is unavailable") from error
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise OSError(errno.ELOOP, "opened path is not a regular file")
        expected_signature = _metadata_signature(expected_stat)
        opened_signature = _metadata_signature(opened_stat)
        if opened_signature != expected_signature:
            status = (
                "replaced"
                if opened_signature[0] != expected_signature[0]
                else "changed"
            )
            raise HashStabilityError(
                errno.ESTALE,
                "file metadata changed between scan and hash",
                status,
            )
        hasher = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
                hasher.update(chunk)
            # fstat after EOF is intentionally performed before the handle is
            # closed.  Any in-place write, chmod, or timestamp update is a
            # stability failure even when the final path still names the same
            # inode.
            final_signature = _metadata_signature(os.fstat(handle.fileno()))
            if final_signature != opened_signature:
                status = (
                    "replaced"
                    if final_signature[0] != opened_signature[0]
                    else "changed"
                )
                raise HashStabilityError(
                    errno.EAGAIN,
                    "file metadata changed during hash",
                    status,
                )
        return hasher.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _same_identity(actual: os.stat_result, expected: os.stat_result) -> bool:
    actual_identity = _identity(actual)
    expected_identity = _identity(expected)
    return actual_identity is not None and actual_identity == expected_identity


def _metadata_change_error(
    expected: os.stat_result,
    actual: os.stat_result,
    *,
    phase: str,
) -> HashStabilityError:
    """Describe a post-hash path check without confusing replacement and edits."""

    expected_identity = _identity(expected)
    actual_identity = _identity(actual)
    if expected_identity is None or actual_identity is None or expected_identity != actual_identity:
        return HashStabilityError(
            errno.ESTALE,
            f"file replaced after hash ({phase})",
            "replaced",
        )
    return HashStabilityError(
        errno.EAGAIN,
        f"file metadata changed after hash ({phase})",
        "changed",
    )


def _hash_error_status(error: BaseException) -> str:
    """Classify hash failures without calling every ``OSError`` a change."""

    explicit = getattr(error, "stability_status", None)
    if isinstance(explicit, str):
        return explicit
    if isinstance(error, PermissionError):
        return "unreadable"
    err = getattr(error, "errno", None)
    if err in (errno.EACCES, errno.EPERM):
        return "unreadable"
    if err in (errno.ENOENT, errno.ENOTDIR, errno.ESTALE, errno.ELOOP):
        return "replaced"
    if err in (errno.EAGAIN,):
        return "changed"
    # EIO and platform-specific read failures do not prove either a rewrite
    # or a replacement; keep them explicitly unknown.
    return "unknown"


def _open_directory(
    path: Path | str,
    expected_stat: os.stat_result,
    *,
    dir_fd: int | None = None,
) -> int:
    """Open a directory without following a replacement symlink.

    When ``dir_fd`` is supplied, *path* is a single child name and the open is
    relative to the already-held parent descriptor (openat semantics).  The
    descriptor identity is checked against the no-follow ``DirEntry.stat``
    result, so replacement by another directory is also rejected.
    """

    directory = getattr(os, "O_DIRECTORY", None)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if not isinstance(directory, int) or directory == 0:
        raise CapabilityError("O_DIRECTORY is unavailable")
    if not isinstance(nofollow, int) or nofollow == 0:
        raise CapabilityError("O_NOFOLLOW is unavailable")
    flags = os.O_RDONLY | directory | nofollow
    try:
        descriptor = os.open(path, flags, dir_fd=dir_fd)
    except (TypeError, NotImplementedError) as error:
        raise CapabilityError("descriptor-relative directory open is unavailable") from error
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISDIR(opened_stat.st_mode):
            raise OSError(errno.ENOTDIR, "opened path is not a directory")
        if not _same_identity(opened_stat, expected_stat):
            raise OSError(errno.ESTALE, "directory changed between scan and open")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@dataclass
class FileRecord:
    path: str
    directory_version: str | None
    file_version: str | None
    version: str | None
    version_status: str
    logical_bytes: int
    allocated_bytes: int | None
    device: int
    inode: int
    raw_name: str = ""
    file_versions: list[str] = field(default_factory=list)
    mode: int = 0
    filemode: str = "----------"
    executable: bool = False
    mtime_ns: int | None = None
    ctime_ns: int | None = None
    sha256: str | None = None
    read_error: str | None = None
    stability_status: str = "not-hashed"
    normalized_directory_version: str | None = None
    normalized_file_version: str | None = None
    normalized_file_versions: list[str] = field(default_factory=list)

    def as_dict(self, *, include_hash: bool) -> dict[str, object]:
        labels = list(self.file_versions)
        if not labels and self.file_version is not None:
            labels = [self.file_version]
        normalized_labels = list(self.normalized_file_versions)
        if not normalized_labels and self.normalized_file_version is not None:
            normalized_labels = [self.normalized_file_version]
        result: dict[str, object] = {
            "path": self.path,
            "raw_name": self.raw_name or Path(self.path).name,
            "directory_version": self.directory_version,
            "file_version": self.file_version,
            "file_versions": labels,
            "raw_directory_version": self.directory_version,
            "raw_file_version": self.file_version,
            "raw_file_versions": labels,
            "normalized_directory_version": self.normalized_directory_version,
            "normalized_file_version": self.normalized_file_version,
            "normalized_file_versions": normalized_labels,
            # Keep explicit aliases so consumers do not lose labels when a
            # filename contains more than one version token.
            "file_labels": labels,
            "labels": labels,
            "version": self.version,
            "version_status": self.version_status,
            "logical_bytes": self.logical_bytes,
            "allocated_bytes": self.allocated_bytes,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "filemode": self.filemode,
            "executable": self.executable,
            "mtime_ns": self.mtime_ns,
            "ctime_ns": self.ctime_ns,
        }
        if include_hash:
            result["sha256"] = self.sha256
            result["stability_status"] = self.stability_status
            if self.read_error is not None:
                result["error"] = self.read_error
        return result


@dataclass
class ScanResult:
    root: Path
    root_device: int
    max_files: int
    files: list[FileRecord] = field(default_factory=list)
    version_directories: list[dict[str, str]] = field(default_factory=list)
    version_mismatches: list[dict[str, str]] = field(default_factory=list)
    version_collisions: list[dict[str, object]] = field(default_factory=list)
    symlinks: list[dict[str, str | None]] = field(default_factory=list)
    special_entries: list[dict[str, str]] = field(default_factory=list)
    excluded_directories: list[dict[str, str]] = field(default_factory=list)
    cross_filesystem: list[dict[str, object]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    max_entries: int = DEFAULT_MAX_ENTRIES
    status: str = "complete"
    coverage_gaps: list[str] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    raw_root_entries: list[str] = field(default_factory=list)
    entries_seen: int = 0


class RootError(ValueError):
    """Raised when the requested root is not a safe directory."""


def _is_broad_root(root: Path) -> bool:
    """Return true for filesystem root or the current user's home directory."""

    try:
        filesystem_root = Path(root.anchor or os.sep).absolute()
        home = Path.home().absolute()
    except (OSError, RuntimeError):
        return False
    return root == filesystem_root or root == home


def validate_root(value: Path | str, *, allow_broad_root: bool = False) -> Path:
    """Validate without resolving a final symlink (which would hide it)."""

    root = Path(value).expanduser()
    try:
        root_stat = root.lstat()
    except OSError as error:
        raise RootError(f"cannot inspect root {root}: {error}") from error
    if stat.S_ISLNK(root_stat.st_mode):
        raise RootError(f"root must not be a symbolic link: {root}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise RootError(f"root is not a directory: {root}")
    if _is_broad_root(root.absolute()) and not allow_broad_root:
        raise RootError(
            f"broad root refused by default: {root}; pass --allow-broad-root to opt in"
        )
    if _identity(root_stat) is None:
        raise RootError(f"root identity is unavailable or zero: {root}")
    # absolute() normalizes the report root but, unlike resolve(), does not
    # follow a symlink in the final path component.
    return _ValidatedRoot(root.absolute(), root_stat)


@dataclass
class _DirectoryFrame:
    """A held directory descriptor and its entries for iterative DFS."""

    descriptor: int
    relative: Path
    inherited_version: str | None
    entries: Iterator[os.DirEntry]
    iterator_close: object | None = None


class TreeScanner:
    """Iterative descriptor-based scanner that never follows symlinks."""

    def __init__(
        self,
        root: Path,
        *,
        include_excluded: bool,
        hash_files: bool,
        max_files: int,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        allow_broad_root: bool = False,
    ) -> None:
        if max_files < 0:
            raise ValueError("max_files must be non-negative")
        if max_entries < 0:
            raise ValueError("max_entries must be non-negative")
        self.root = root
        self.include_excluded = include_excluded
        self.hash_files = hash_files
        self.max_files = max_files
        self.max_entries = max_entries
        self.allow_broad_root = allow_broad_root
        trusted_root_stat = getattr(root, "_trusted_stat", None)
        root_stat = root.lstat()
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise RootError(f"root changed while scanning and is no longer a directory: {root}")
        if trusted_root_stat is not None:
            trusted_identity = _identity(trusted_root_stat)
            current_identity = _identity(root_stat)
            if (
                trusted_identity is None
                or current_identity is None
                or trusted_identity != current_identity
            ):
                raise RootError(
                    f"root identity changed after validation; refusing replacement: {root}"
                )
        if _is_broad_root(root) and not allow_broad_root:
            raise RootError(
                f"broad root refused by default: {root}; pass --allow-broad-root to opt in"
            )
        # Keep the first trusted snapshot for the descriptor open.  The
        # current stat was checked against it above, so a path swap between
        # validation and construction cannot become a complete scan.
        self._root_stat = trusted_root_stat or root_stat
        try:
            root_device = int(getattr(root_stat, "st_dev", 0))
        except (TypeError, ValueError, OverflowError):
            root_device = 0
        self.result = ScanResult(
            root=root,
            root_device=root_device,
            max_files=max_files,
            max_entries=max_entries,
        )
        capabilities, capability_gaps = _detect_capabilities()
        self.result.capabilities = capabilities
        identity_gap = _identity(root_stat) is None
        self._capability_unsupported = bool(capability_gaps) or identity_gap
        if identity_gap:
            capability_gaps = [*capability_gaps, "root identity (device/inode) is missing or zero"]
        if capability_gaps:
            self.result.status = "unsupported"
            self.result.coverage_gaps.extend(capability_gaps)
            self.result.errors.append(
                "safe descriptor traversal is unsupported: " + "; ".join(capability_gaps)
            )
        self._regular_seen = 0
        self._entry_count = 0
        self._limit_hit = False
        self._abort_scan = False

    def scan(self) -> ScanResult:
        if self._capability_unsupported:
            return self._sorted_result()
        root_version = version_from_directory(self.root.name)
        if root_version is not None:
            self.result.version_directories.append(
                {
                    "path": ".",
                    "version": root_version,
                    "raw_name": self.root.name,
                    "normalized_version": normalized_version_from_directory(self.root.name),
                }
            )

        try:
            root_descriptor = _open_directory(self.root, self._root_stat)
        except (OSError, CapabilityError, TypeError, NotImplementedError) as error:
            if isinstance(error, (CapabilityError, TypeError, NotImplementedError)):
                self._unsupported(str(error))
            self._error(self.root, error)
            return self._sorted_result()

        root_frame = self._make_frame(root_descriptor, Path(), root_version)
        if root_frame is None:
            return self._sorted_result()

        frames: list[_DirectoryFrame] = [root_frame]
        try:
            while frames and not self._limit_hit and not self._abort_scan:
                frame = frames[-1]
                if not self._verify_scope(frame):
                    self._abort_scan = True
                    break
                try:
                    entry = next(frame.entries)
                except StopIteration:
                    self._close_frame(frame)
                    frames.pop()
                    continue

                self._entry_count += 1
                self.result.entries_seen = self._entry_count
                entry_relative = frame.relative / entry.name
                report_path = entry_relative.as_posix()
                path = self.root / entry_relative
                if self._entry_count > self.max_entries:
                    self._record_entry_limit(report_path)
                    break
                entry_stat_for_verify: os.stat_result | None = None
                try:
                    if frame.relative == Path() and entry.name not in self.result.raw_root_entries:
                        self.result.raw_root_entries.append(entry.name)
                    if entry.is_symlink():
                        try:
                            entry_stat_for_verify = entry.stat(follow_symlinks=False)
                        except (OSError, TypeError, NotImplementedError) as error:
                            if isinstance(error, (TypeError, NotImplementedError)):
                                self._unsupported(str(error))
                            self._error(path, error)
                            self._abort_scan = True
                            break
                        if _identity(entry_stat_for_verify) is None:
                            self._unsupported(f"{report_path}: symlink identity is missing or zero")
                            self._error(path, CapabilityError("symlink identity is unavailable"))
                            self._abort_scan = True
                            break
                        self._record_symlink(path, report_path, frame.descriptor, entry.name)
                    else:
                        entry_stat = entry.stat(follow_symlinks=False)
                        entry_stat_for_verify = entry_stat
                        mode = int(entry_stat.st_mode)
                        entry_device = _identity(entry_stat)
                        if entry_device is None:
                            self._unsupported(
                                f"{report_path}: entry identity (device/inode) is missing or zero"
                            )
                            self._error(path, CapabilityError("entry identity is unavailable"))
                            self._abort_scan = True
                            break
                        if entry_device[0] != self.result.root_device:
                            self._record_cross_filesystem(report_path, mode, entry_device[0])
                            continue
                        if not self._verify_entry_identity(frame, entry.name, entry_stat, path):
                            self._abort_scan = True
                            break

                        if stat.S_ISDIR(mode):
                            child_version = version_from_directory(entry.name)
                            if child_version is not None:
                                self.result.version_directories.append(
                                    {
                                        "path": report_path,
                                        "version": child_version,
                                        "raw_name": entry.name,
                                        "normalized_version": normalized_version_from_directory(
                                            entry.name
                                        ),
                                    }
                                )
                            if not self.include_excluded and entry.name in DEFAULT_EXCLUDE_SET:
                                self.result.excluded_directories.append(
                                    {
                                        "path": report_path,
                                        "name": entry.name,
                                        "reason": "heuristic candidate; verify project-specific recovery first",
                                    }
                                )
                                self._limited(
                                    f"default exclusion not accepted: {report_path}"
                                )
                                continue
                            try:
                                child_descriptor = _open_directory(
                                    entry.name,
                                    entry_stat,
                                    dir_fd=frame.descriptor,
                                )
                            except (
                                OSError,
                                CapabilityError,
                                TypeError,
                                NotImplementedError,
                            ) as error:
                                if isinstance(
                                    error, (CapabilityError, TypeError, NotImplementedError)
                                ):
                                    self._unsupported(str(error))
                                self._error(path, error)
                                self._abort_scan = True if isinstance(error, CapabilityError) else self._abort_scan
                                continue
                            child_frame = self._make_frame(
                                child_descriptor,
                                entry_relative,
                                child_version or frame.inherited_version,
                            )
                            if child_frame is not None:
                                frames.append(child_frame)
                        elif stat.S_ISREG(mode):
                            if self._regular_seen >= self.max_files:
                                self._record_file_limit(report_path)
                                break
                            self._regular_seen += 1
                            self._record_file(
                                path,
                                report_path,
                                frame.inherited_version,
                                entry_stat,
                                dir_fd=frame.descriptor,
                                name=entry.name,
                            )
                        else:
                            self.result.special_entries.append(
                                {"path": report_path, "type": stat.filemode(mode)}
                            )
                            self._limited(f"special entry skipped: {report_path}")
                except (CapabilityError, TypeError, NotImplementedError) as error:
                    self._unsupported(str(error))
                    self._error(path, error)
                    self._abort_scan = True
                except OSError as error:
                    self._error(path, error)
                    self._abort_scan = True
                finally:
                    if (
                        not self._abort_scan
                        and entry_stat_for_verify is not None
                        and not self._verify_entry_identity(
                            frame, entry.name, entry_stat_for_verify, path
                        )
                    ):
                        self._abort_scan = True
                    # A frame may have been replaced while its child was
                    # opened or hashed.  Stop before obtaining another entry
                    # from a descriptor whose path is no longer trusted.
                    if not self._abort_scan and not self._verify_scope(frame):
                        self._abort_scan = True
        finally:
            for frame in reversed(frames):
                self._close_frame(frame)

        return self._sorted_result()

    def _make_frame(
        self,
        descriptor: int,
        relative: Path,
        inherited_version: str | None,
    ) -> _DirectoryFrame | None:
        path = self.root / relative
        iterator = None
        keep_descriptor = False
        try:
            if not self._verify_directory_identity(descriptor, relative):
                return None
            iterator = os.scandir(descriptor)
            try:
                entries = iter(iterator)
            except TypeError as error:
                raise CapabilityError("os.scandir(fd) did not return an iterator") from error
            # A replacement can occur while scandir is reading the iterator.
            # The descriptor remains safe, but the path is now unresolved and
            # must not be presented as a complete scan.
            if not self._verify_directory_identity(descriptor, relative):
                return None
            keep_descriptor = True
            return _DirectoryFrame(
                descriptor,
                relative,
                inherited_version,
                entries,
                iterator_close=getattr(iterator, "close", None),
            )
        except (OSError, CapabilityError, TypeError, NotImplementedError) as error:
            if isinstance(error, (CapabilityError, TypeError, NotImplementedError)):
                self._unsupported(str(error))
            self._error(path, error)
            return None
        finally:
            if iterator is not None and not keep_descriptor:
                close_iterator = getattr(iterator, "close", None)
                if close_iterator is not None:
                    close_iterator()
            if not keep_descriptor:
                self._close_descriptor(descriptor)

    def _verify_directory_identity(self, descriptor: int, relative: Path) -> bool:
        """Check the held FD against its path without making the path trusted."""

        path = self.root / relative
        try:
            opened_stat = os.fstat(descriptor)
            path_stat = path.lstat()
        except (OSError, TypeError, NotImplementedError) as error:
            if isinstance(error, (TypeError, NotImplementedError)):
                self._unsupported(str(error))
            self._error(path, error)
            return False
        if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISDIR(path_stat.st_mode):
            self._error(path, OSError(errno.ESTALE, "directory path replaced while scanning"))
            return False
        if _identity(opened_stat) is None or _identity(path_stat) is None:
            self._unsupported(f"{path}: directory identity is missing or zero")
            self._error(path, CapabilityError("directory identity is unavailable"))
            return False
        if not _same_identity(opened_stat, path_stat):
            self._error(path, OSError(errno.ESTALE, "directory identity changed while scanning"))
            return False
        opened_identity = _identity(opened_stat)
        if opened_identity is None:
            self._unsupported(f"{path}: directory identity is missing or zero")
            return False
        if opened_identity[0] != self.result.root_device:
            self._record_cross_filesystem(
                relative.as_posix() or ".",
                opened_stat.st_mode,
                opened_identity[0],
            )
            return False
        return True

    def _verify_scope(self, frame: _DirectoryFrame) -> bool:
        """Recheck root and current frame before/after every entry."""

        if not self._verify_directory_identity(frame.descriptor, frame.relative):
            return False
        return True

    def _verify_entry_identity(
        self,
        frame: _DirectoryFrame,
        name: str,
        expected: os.stat_result,
        path: Path,
    ) -> bool:
        try:
            actual = os.stat(name, dir_fd=frame.descriptor, follow_symlinks=False)
        except (OSError, TypeError, NotImplementedError) as error:
            if isinstance(error, (TypeError, NotImplementedError)):
                self._unsupported(str(error))
            self._error(path, error)
            return False
        if _identity(actual) is None or not _same_identity(actual, expected):
            self._error(path, OSError(errno.ESTALE, "entry identity changed while scanning"))
            return False
        return True

    def _close_descriptor(self, descriptor: int) -> None:
        try:
            os.close(descriptor)
        except OSError as error:
            self._error(self.root, error)

    def _close_frame(self, frame: _DirectoryFrame) -> None:
        close_iterator = frame.iterator_close
        if callable(close_iterator):
            try:
                close_iterator()
            except OSError as error:
                self._error(self.root / frame.relative, error)
        self._close_descriptor(frame.descriptor)

    def _sorted_result(self) -> ScanResult:
        self._detect_version_collisions()
        self.result.files.sort(key=lambda item: item.path)
        self.result.version_directories.sort(
            key=lambda item: (str(item.get("path", "")), str(item.get("raw_name", "")))
        )
        self.result.version_mismatches.sort(
            key=lambda item: (
                str(item.get("path", "")),
                str(item.get("directory_version", "")),
                str(item.get("file_version", "")),
            )
        )
        self.result.symlinks.sort(
            key=lambda item: (str(item.get("path", "")), str(item.get("target", "")))
        )
        self.result.special_entries.sort(
            key=lambda item: (str(item.get("path", "")), str(item.get("type", "")))
        )
        self.result.excluded_directories.sort(
            key=lambda item: (str(item.get("path", "")), str(item.get("name", "")))
        )
        self.result.cross_filesystem.sort(
            key=lambda item: (str(item.get("path", "")), str(item.get("device", "")))
        )
        self.result.version_collisions.sort(key=lambda item: str(item.get("normalized_version", "")))
        self.result.raw_root_entries = sorted(set(self.result.raw_root_entries))
        self.result.errors = sorted(set(self.result.errors))
        self.result.coverage_gaps = sorted(set(self.result.coverage_gaps))
        return self.result

    def _detect_version_collisions(self) -> None:
        """Find distinct raw labels that share one normalized heuristic.

        Normalization is only a grouping aid.  The raw variants and their
        paths remain in the finding so the project naming convention is left
        for a human to resolve.
        """

        observations: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        def add_observation(normalized: object, raw: object, source: dict[str, str]) -> None:
            normalized_text = str(normalized) if normalized is not None else ""
            raw_text = str(raw) if raw is not None else ""
            if not normalized_text or not raw_text:
                return
            observations[normalized_text][raw_text].append(source)

        for item in self.result.version_directories:
            raw = item.get("version") or item.get("raw_name")
            normalized = item.get("normalized_version")
            if normalized is None and raw is not None:
                normalized = normalized_version_from_directory(str(raw))
            add_observation(
                normalized,
                raw,
                {
                    "kind": "directory",
                    "path": str(item.get("path", "")),
                    "raw": str(raw or ""),
                },
            )

        for record in self.result.files:
            raw_name = record.raw_name or Path(record.path).name
            for raw, normalized in _filename_version_matches(raw_name):
                add_observation(
                    normalized,
                    raw,
                    {"kind": "file", "path": record.path, "raw": raw},
                )

        collisions: list[dict[str, object]] = []
        for normalized in sorted(observations):
            variants = observations[normalized]
            if len(variants) < 2:
                continue
            raw_variants = sorted(variants)
            sources: list[dict[str, str]] = []
            for raw in raw_variants:
                sources.extend(variants[raw])
            sources.sort(key=lambda item: (item["kind"], item["path"], item["raw"]))
            collisions.append(
                {
                    "normalized_version": normalized,
                    "raw_variants": raw_variants,
                    "sources": sources,
                    "reason": (
                        "multiple raw version labels share one normalized heuristic; "
                        "project naming convention is unresolved"
                    ),
                }
            )
        self.result.version_collisions = collisions
        for collision in collisions:
            variants = ", ".join(str(item) for item in collision["raw_variants"])
            self._limited(
                f"version naming collision (normalized {collision['normalized_version']}): "
                f"raw variants {variants}"
            )

    def _record_cross_filesystem(self, report_path: str, mode: int, device: int) -> None:
        entry_type = "directory" if stat.S_ISDIR(mode) else "file" if stat.S_ISREG(mode) else stat.filemode(mode)
        item: dict[str, object] = {
            "path": report_path,
            "type": entry_type,
            "device": device,
            "root_device": self.result.root_device,
            "reason": "cross-filesystem boundary; not traversed",
        }
        self.result.cross_filesystem.append(item)
        self.result.errors.append(
            f"{report_path}: cross-filesystem boundary (device {device}, root device {self.result.root_device})"
        )
        self._limited(f"cross-filesystem boundary: {report_path}")

    def _record_file_limit(self, report_path: str) -> None:
        self._limit_hit = True
        self._limited(f"scan truncated by max_files={self.max_files}")
        self.result.errors.append(
            f"{report_path}: file limit exceeded (max_files={self.max_files}); scan truncated"
        )

    def _record_entry_limit(self, report_path: str) -> None:
        self._limit_hit = True
        self._limited(f"scan truncated by max_entries={self.max_entries}")
        self.result.errors.append(
            f"{report_path}: entry limit exceeded (max_entries={self.max_entries}); scan truncated"
        )

    def _record_symlink(
        self,
        path: Path,
        report_path: str,
        dir_fd: int,
        name: str,
    ) -> None:
        target: str | None
        try:
            target = os.readlink(name, dir_fd=dir_fd)
        except (OSError, TypeError, NotImplementedError) as error:
            target = None
            if isinstance(error, (TypeError, NotImplementedError)):
                self._unsupported(str(error))
            self._error(path, error)
        self.result.symlinks.append({"path": report_path, "target": target})
        self._limited(f"symbolic link not followed: {report_path}")

    def _record_file(
        self,
        path: Path,
        report_path: str,
        directory_version: str | None,
        file_stat: os.stat_result,
        *,
        dir_fd: int,
        name: str,
    ) -> None:
        file_versions = versions_from_filename(path.name)
        normalized_file_versions = normalized_versions_from_filename(path.name)
        raw_match_count = sum(1 for _match in VERSION_TOKEN_RE.finditer(path.name))
        file_version = file_versions[0] if file_versions else None
        normalized_file_version = (
            normalized_file_versions[0] if normalized_file_versions else None
        )
        normalized_directory_version = normalized_version_from_directory(
            directory_version or ""
        )
        if raw_match_count > 1 or len(file_versions) > 1:
            version = None
            version_status = "ambiguous"
            self._limited(f"multiple version labels: {report_path}")
        elif directory_version and file_version:
            if directory_version == file_version:
                version = directory_version
                version_status = "aligned"
            elif (
                normalized_directory_version is not None
                and normalized_file_version is not None
                and normalized_directory_version == normalized_file_version
            ):
                # Matching only after normalization is not proof that the
                # project uses one naming grammar (V01 vs v1, release-1.0
                # vs v1.0, and similar differences remain unresolved).
                version = None
                version_status = "ambiguous"
                self._limited(f"version label spelling differs: {report_path}")
            else:
                version = None
                version_status = "mismatch"
                self.result.version_mismatches.append(
                    {
                        "path": report_path,
                        "directory_version": directory_version,
                        "file_version": file_version,
                    }
                )
                self._limited(f"version mismatch: {report_path}")
        elif directory_version:
            version = directory_version
            version_status = "directory-only"
        elif file_version:
            version = file_version
            version_status = "file-only"
        else:
            version = None
            version_status = "unversioned"

        try:
            device, inode = _identity(file_stat) or (0, 0)
            mode = int(file_stat.st_mode)
            logical_bytes = int(file_stat.st_size)
            mtime_ns = int(file_stat.st_mtime_ns)
            ctime_ns = int(file_stat.st_ctime_ns)
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            self._unsupported(f"{report_path}: file metadata unavailable")
            self._error(path, error)
            return
        if device <= 0 or inode <= 0:
            self._unsupported(f"{report_path}: file identity is missing or zero")
            self._error(path, CapabilityError("file identity is unavailable"))
            return
        record = FileRecord(
            path=report_path,
            raw_name=path.name,
            directory_version=directory_version,
            file_version=file_version,
            file_versions=file_versions,
            version=version,
            version_status=version_status,
            logical_bytes=logical_bytes,
            allocated_bytes=_allocated_bytes(file_stat),
            device=device,
            inode=inode,
            mode=mode,
            filemode=stat.filemode(mode),
            executable=bool(mode & 0o111),
            mtime_ns=mtime_ns,
            ctime_ns=ctime_ns,
            normalized_directory_version=normalized_directory_version,
            normalized_file_version=normalized_file_version,
            normalized_file_versions=normalized_file_versions,
        )
        if self.hash_files:
            try:
                digest = _stable_file_sha256(name, file_stat, dir_fd=dir_fd)
                # ``_stable_file_sha256`` proves descriptor stability through
                # EOF.  Recheck the directory entry after it returns and
                # before publishing ``stable``: a replacement or same-inode
                # edit in this point-in-time boundary is unresolved.
                final_entry_stat = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                if not stat.S_ISREG(final_entry_stat.st_mode):
                    raise HashStabilityError(
                        errno.ELOOP,
                        "file replaced after hash",
                        "replaced",
                    )
                expected_signature = _metadata_signature(file_stat)
                final_signature = _metadata_signature(final_entry_stat)
                if final_signature != expected_signature:
                    raise _metadata_change_error(
                        file_stat,
                        final_entry_stat,
                        phase="entry verification",
                    )
                record.sha256 = digest
                record.stability_status = "stable"
            except (OSError, CapabilityError, TypeError, NotImplementedError) as error:
                record.read_error = str(error)
                record.sha256 = None
                record.stability_status = _hash_error_status(error)
                if isinstance(error, (CapabilityError, TypeError, NotImplementedError)):
                    self._unsupported(str(error))
                self._error(path, error)
        self.result.files.append(record)

    def _limited(self, reason: str) -> None:
        if self.result.status != "unsupported":
            self.result.status = "limited"
        if reason not in self.result.coverage_gaps:
            self.result.coverage_gaps.append(reason)

    def _unsupported(self, reason: str) -> None:
        self.result.status = "unsupported"
        if reason not in self.result.coverage_gaps:
            self.result.coverage_gaps.append(reason)

    def _error(self, path: Path, error: BaseException) -> None:
        message = f"{path}: {error}"
        self.result.errors.append(message)
        if message not in self.result.coverage_gaps:
            self.result.coverage_gaps.append(message)
        if self.result.status != "unsupported":
            self.result.status = "limited"


def scan(
    root: Path | str,
    *,
    include_excluded: bool = False,
    hash_files: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    allow_broad_root: bool = False,
) -> ScanResult:
    """Scan *root* and return a structured result.

    This function is intentionally public so callers and unit tests can use
    the same root validation and no-follow traversal as the CLI.
    """

    if max_files < 0:
        raise ValueError("max_files must be non-negative")
    if max_entries < 0:
        raise ValueError("max_entries must be non-negative")
    # ``main`` validates the CLI root before calling this function so it can
    # keep RootError handling structured.  Preserve that first snapshot rather
    # than lstat'ing a replacement path a second time; TreeScanner will compare
    # the held identity before opening the directory.
    if isinstance(root, _ValidatedRoot):
        validated = root
        if _is_broad_root(validated) and not allow_broad_root:
            raise RootError(
                f"broad root refused by default: {validated}; pass --allow-broad-root to opt in"
            )
    else:
        validated = validate_root(root, allow_broad_root=allow_broad_root)
    capabilities, capability_gaps = _detect_capabilities()
    try:
        root_stat = validated.lstat()
        root_device = int(getattr(root_stat, "st_dev", 0))
    except OSError:
        root_device = 0
    if capability_gaps:
        return ScanResult(
            root=validated,
            root_device=root_device,
            max_files=max_files,
            max_entries=max_entries,
            status="unsupported",
            capabilities=capabilities,
            coverage_gaps=capability_gaps,
            errors=["safe descriptor traversal is unsupported: " + "; ".join(capability_gaps)],
        )
    try:
        scanner = TreeScanner(
            validated,
            include_excluded=include_excluded,
            hash_files=hash_files,
            max_files=max_files,
            max_entries=max_entries,
            allow_broad_root=allow_broad_root,
        )
    except (OSError, RootError, CapabilityError, TypeError, NotImplementedError) as error:
        # The root can be replaced after validate_root and before the scanner
        # takes its first descriptor.  Preserve a stdout report and non-zero
        # status instead of emitting a traceback or following the replacement.
        unsupported = isinstance(error, (CapabilityError, TypeError, NotImplementedError))
        return ScanResult(
            root=validated,
            root_device=root_device,
            max_files=max_files,
            max_entries=max_entries,
            status="unsupported" if unsupported else "limited",
            capabilities=capabilities,
            coverage_gaps=[str(error)],
            errors=[f"{validated}: {error}"],
        )
    result = scanner.scan()
    result.capabilities = capabilities
    return result


def _sorted_unique_strings(values: Sequence[str]) -> list[str]:
    """Return stable, duplicate-free public diagnostic strings."""

    return sorted(set(values))


def _hardlink_groups(result: ScanResult) -> list[dict[str, object]]:
    groups: dict[tuple[int, int], list[FileRecord]] = defaultdict(list)
    for record in result.files:
        groups[(record.device, record.inode)].append(record)
    output: list[dict[str, object]] = []
    for (device, inode), records in groups.items():
        if len(records) >= 2:
            first = records[0]
            output.append(
                {
                    "device": device,
                    "inode": inode,
                    "count": len(records),
                    "paths": [item.path for item in records],
                    "logical_bytes": first.logical_bytes,
                    "allocated_bytes": first.allocated_bytes,
                }
            )
    output.sort(key=lambda item: str(item["paths"][0]))
    return output


def _sum_allocated(records: Sequence[FileRecord]) -> int | None:
    if not records:
        return 0
    if any(item.allocated_bytes is None for item in records):
        return None
    return sum(int(item.allocated_bytes) for item in records if item.allocated_bytes is not None)


def _totals(result: ScanResult) -> dict[str, object]:
    groups: dict[tuple[int, int], FileRecord] = {}
    for record in result.files:
        groups.setdefault((record.device, record.inode), record)
    return {
        "regular_files": len(result.files),
        "unique_files": len(groups),
        "logical_bytes": sum(item.logical_bytes for item in groups.values()),
        "allocated_bytes": _sum_allocated(list(groups.values())),
        "path_logical_bytes": sum(item.logical_bytes for item in result.files),
        "path_allocated_bytes": _sum_allocated(result.files),
    }


def _base_report(result: ScanResult, command: str) -> dict[str, object]:
    totals = _totals(result)
    status = result.status
    if status == "complete":
        if (
            result.errors
            or result.version_mismatches
            or result.version_collisions
            or result.symlinks
            or result.special_entries
            or result.cross_filesystem
            or result.excluded_directories
            or any(item.version_status == "ambiguous" for item in result.files)
        ):
            status = "limited"
    # Top-level byte values are convenient for shell users; the complete
    # totals object retains the path-vs-inode distinction for auditability.
    return {
        "command": command,
        "schema_version": SCHEMA_VERSION,
        "scanner_version": SCANNER_VERSION,
        "status": status,
        "coverage_gaps": _sorted_unique_strings(result.coverage_gaps),
        "capabilities": dict(result.capabilities),
        "root": str(result.root),
        "root_device": result.root_device,
        "max_files": result.max_files,
        "max_entries": result.max_entries,
        "entries_seen": result.entries_seen,
        "raw_root_entries": sorted(set(result.raw_root_entries)),
        "totals": totals,
        "logical_bytes": totals["logical_bytes"],
        "allocated_bytes": totals["allocated_bytes"],
        "hardlink_groups": _hardlink_groups(result),
        "version_directories": sorted(
            result.version_directories,
            key=lambda item: (str(item.get("path", "")), str(item.get("raw_name", ""))),
        ),
        "version_mismatches": sorted(
            result.version_mismatches,
            key=lambda item: (
                str(item.get("path", "")),
                str(item.get("directory_version", "")),
                str(item.get("file_version", "")),
            ),
        ),
        "version_collisions": sorted(
            result.version_collisions,
            key=lambda item: str(item.get("normalized_version", "")),
        ),
        "symlinks": sorted(
            result.symlinks,
            key=lambda item: (str(item.get("path", "")), str(item.get("target", ""))),
        ),
        "special_entries": sorted(
            result.special_entries,
            key=lambda item: (str(item.get("path", "")), str(item.get("type", ""))),
        ),
        "cross_filesystem": sorted(
            result.cross_filesystem,
            key=lambda item: (str(item.get("path", "")), str(item.get("device", ""))),
        ),
        "default_excludes": list(DEFAULT_EXCLUDES),
        "excluded_directories": sorted(
            result.excluded_directories,
            key=lambda item: (str(item.get("path", "")), str(item.get("name", ""))),
        ),
        "include_excluded": False,
        "exclusion_policy": {
            "mode": "default-excludes",
            "default_directory_names": list(DEFAULT_EXCLUDES),
            "include_excluded": False,
        },
        "errors": _sorted_unique_strings(result.errors),
        # scan_errors is an explicit alias for consumers that distinguish
        # traversal failures from other report findings.
        "scan_errors": _sorted_unique_strings(result.errors),
        "storage_note": STORAGE_NOTE,
    }


def summary_report(result: ScanResult, *, include_excluded: bool) -> dict[str, object]:
    report = _base_report(result, "summary")
    report["include_excluded"] = include_excluded
    report["exclusion_policy"] = {
        "mode": "include-excluded" if include_excluded else "default-excludes",
        "default_directory_names": list(DEFAULT_EXCLUDES),
        "include_excluded": include_excluded,
    }
    report["files"] = [record.as_dict(include_hash=False) for record in result.files]
    return report


def manifest_report(result: ScanResult, *, include_excluded: bool) -> dict[str, object]:
    report = _base_report(result, "manifest")
    report["include_excluded"] = include_excluded
    report["exclusion_policy"] = {
        "mode": "include-excluded" if include_excluded else "default-excludes",
        "default_directory_names": list(DEFAULT_EXCLUDES),
        "include_excluded": include_excluded,
    }
    report["files"] = [record.as_dict(include_hash=True) for record in result.files]
    return report


def _markdown_escape(value: object) -> str:
    """Escape a table cell, including paths containing pipes/backticks/newlines."""

    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if "`" not in text:
        return f"`{text}`"
    max_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (max_run + 1)
    return f"{fence} {text} {fence}"


def _plain_markdown_escape(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", "\\r").replace("\n", "\\n")


def _markdown_header(result: dict[str, object], title: str) -> list[str]:
    lines = [
        f"# {title}: {_markdown_escape(result['root'])}",
        "",
        f"Status: `{_plain_markdown_escape(result['status'])}`  ",
        f"Schema: `{_plain_markdown_escape(result['schema_version'])}`  ",
        f"Scanner: `{_plain_markdown_escape(result['scanner_version'])}`",
        "",
        f"> {_plain_markdown_escape(result['storage_note'])}",
        "",
    ]
    gaps = result.get("coverage_gaps") or []
    if gaps:
        lines.extend(["Coverage gaps:", "", *[f"- {_plain_markdown_escape(item)}" for item in gaps], ""])
    return lines


def _markdown_summary(report: dict[str, object]) -> str:
    lines = _markdown_header(report, "Version audit summary")
    totals = report["totals"]
    lines.extend(
        [
            "## Storage totals",
            "",
            "| Metric | Bytes/files |",
            "|---|---:|",
            f"| Logical bytes (unique inodes) | {totals['logical_bytes']} |",
            f"| Allocated bytes (unique inodes) | {totals['allocated_bytes']} |",
            f"| Regular file paths | {totals['regular_files']} |",
            f"| Unique files by device+inode | {totals['unique_files']} |",
            f"| Logical bytes (all paths) | {totals['path_logical_bytes']} |",
            f"| Allocated bytes (all paths) | {totals['path_allocated_bytes']} |",
            "",
            "## Version directories",
            "",
            "| Version | Path |",
            "|---|---|",
        ]
    )
    version_dirs = report["version_directories"]
    if version_dirs:
        for item in version_dirs:
            lines.append(f"| {_plain_markdown_escape(item['version'])} | {_markdown_escape(item['path'])} |")
    else:
        lines.append("| — | — |")

    lines.extend(["", "## Version directory/file mismatches", "", "| Path | Directory label | File label |", "|---|---|---|"])
    mismatches = report["version_mismatches"]
    if mismatches:
        for item in mismatches:
            lines.append(
                f"| {_markdown_escape(item['path'])} | {_plain_markdown_escape(item['directory_version'])} | {_plain_markdown_escape(item['file_version'])} |"
            )
    else:
        lines.append("| — | — | — |")

    collisions = report.get("version_collisions") or []
    if collisions:
        lines.extend(
            [
                "",
                "## Version naming collisions (unresolved)",
                "",
                "| Normalized heuristic | Raw variants | Sources |",
                "|---|---|---|",
            ]
        )
        for item in collisions:
            variants = ", ".join(str(value) for value in item["raw_variants"])
            sources = "<br>".join(
                _markdown_escape(f"{source['kind']}:{source['path']} ({source['raw']})")
                for source in item["sources"]
            )
            lines.append(
                f"| {_plain_markdown_escape(item['normalized_version'])} | "
                f"{_plain_markdown_escape(variants)} | {sources} |"
            )

    lines.extend(["", "## Regular files", "", "| Path | Directory label | File label | Version status | Logical | Allocated |", "|---|---|---|---|---:|---:|"])
    files = report["files"]
    if files:
        for item in files:
            lines.append(
                f"| {_markdown_escape(item['path'])} | {_plain_markdown_escape(item['directory_version'] or '—')} | "
                f"{_plain_markdown_escape(item['file_version'] or '—')} | {_plain_markdown_escape(item['version_status'])} | "
                f"{item['logical_bytes']} | {item['allocated_bytes']} |"
            )
    else:
        lines.append("| — | — | — | — | — | — |")

    lines.extend(["", "## Hard-link groups", "", "| Device | Inode | Paths | Logical | Allocated |", "|---:|---:|---|---:|---:|"])
    groups = report["hardlink_groups"]
    if groups:
        for item in groups:
            paths = "<br>".join(_markdown_escape(path) for path in item["paths"])
            lines.append(f"| {item['device']} | {item['inode']} | {paths} | {item['logical_bytes']} | {item['allocated_bytes']} |")
    else:
        lines.append("| — | — | None found | — | — |")

    _append_common_markdown_sections(lines, report)
    return "\n".join(lines) + "\n"


def _markdown_manifest(report: dict[str, object]) -> str:
    lines = _markdown_header(report, "Version manifest")
    lines.extend(
        [
            "## Regular files (complete SHA-256)",
            "",
            "| Path | Directory label | File label | Status | Logical | Allocated | SHA-256 |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    files = report["files"]
    if files:
        for item in files:
            digest = item.get("sha256") or "ERROR"
            lines.append(
                f"| {_markdown_escape(item['path'])} | {_plain_markdown_escape(item['directory_version'] or '—')} | "
                f"{_plain_markdown_escape(item['file_version'] or '—')} | {_plain_markdown_escape(item['version_status'])} | "
                f"{item['logical_bytes']} | {item['allocated_bytes']} | {_markdown_escape(digest)} |"
            )
    else:
        lines.append("| — | — | — | — | — | — | — |")
    lines.extend(["", "## Storage totals", "", "| Metric | Bytes/files |", "|---|---:|"])
    totals = report["totals"]
    for label, key in (
        ("Logical bytes (unique inodes)", "logical_bytes"),
        ("Allocated bytes (unique inodes)", "allocated_bytes"),
        ("Regular file paths", "regular_files"),
        ("Unique files by device+inode", "unique_files"),
    ):
        lines.append(f"| {label} | {totals[key]} |")
    _append_common_markdown_sections(lines, report)
    return "\n".join(lines) + "\n"


def _append_common_markdown_sections(lines: list[str], report: dict[str, object]) -> None:
    lines.extend(["", "## Symbolic links (not followed)", "", "| Path | Target |", "|---|---|"])
    links = report["symlinks"]
    if links:
        for item in links:
            lines.append(f"| {_markdown_escape(item['path'])} | {_markdown_escape(item['target'] or 'unreadable')} |")
    else:
        lines.append("| — | None found |")

    boundaries = report["cross_filesystem"]
    if boundaries:
        lines.extend(["", "## Cross-filesystem boundaries (unresolved)", "", "| Path | Type | Device | Root device | Reason |", "|---|---|---:|---:|---|"])
        for item in boundaries:
            lines.append(
                f"| {_markdown_escape(item['path'])} | {_plain_markdown_escape(item['type'])} | {item['device']} | "
                f"{item['root_device']} | {_plain_markdown_escape(item['reason'])} |"
            )

    lines.extend(["", "## Default exclusions", "", "The following directory names are excluded by default (heuristics; verify project-specific recovery first): " + ", ".join(_markdown_escape(name) for name in report["default_excludes"]) + ".", "", "| Skipped path | Name | Reason |", "|---|---|---|"])
    excluded = report["excluded_directories"]
    if excluded:
        for item in excluded:
            lines.append(f"| {_markdown_escape(item['path'])} | {_markdown_escape(item['name'])} | {_plain_markdown_escape(item['reason'])} |")
    else:
        lines.append("| — | — | None encountered |")

    special = report["special_entries"]
    if special:
        lines.extend(["", "## Non-regular entries skipped", "", "| Path | Type |", "|---|---|"])
        for item in special:
            lines.append(f"| {_markdown_escape(item['path'])} | {_plain_markdown_escape(item['type'])} |")

    errors = report["errors"]
    if errors:
        lines.extend(["", "## Scan errors", ""])
        lines.extend(f"- {_plain_markdown_escape(error)}" for error in errors)


def render(report: dict[str, object], output_format: str) -> str:
    """Render a report as JSON or Markdown."""

    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output_format == "markdown":
        if report["command"] == "summary":
            return _markdown_summary(report)
        return _markdown_manifest(report)
    raise ValueError(f"unsupported format: {output_format}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("json", "markdown"),
        default="json",
        help="report format (default: json)",
    )
    parser.add_argument(
        "--max-files",
        dest="max_files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"maximum regular files to retain in memory (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--max-entries",
        dest="max_entries",
        type=int,
        default=DEFAULT_MAX_ENTRIES,
        help=f"maximum directory entries to inspect (default: {DEFAULT_MAX_ENTRIES})",
    )
    parser.add_argument(
        "--include-excluded",
        "--include-regenerable",
        dest="include_excluded",
        action="store_true",
        help="scan default regenerable directories too",
    )
    parser.add_argument(
        "--allow-broad-root",
        dest="allow_broad_root",
        action="store_true",
        help="explicitly allow scanning filesystem root or home directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    for command in ("summary", "manifest"):
        subparser = subparsers.add_parser(
            command,
            help=(
                "metadata/storage summary without content hashes"
                if command == "summary"
                else "per-file manifest with complete SHA-256 hashes"
            ),
        )
        subparser.add_argument("root", type=Path, help="directory to scan")
        # SUPPRESS means a global --format remains effective when supplied
        # before the subcommand, while the natural trailing form also works.
        subparser.add_argument(
            "--format",
            dest="output_format",
            choices=("json", "markdown"),
            default=argparse.SUPPRESS,
            help="report format (default: json)",
        )
        subparser.add_argument(
            "--include-excluded",
            "--include-regenerable",
            dest="include_excluded",
            action="store_true",
            default=argparse.SUPPRESS,
            help="scan default regenerable directories too",
        )
        subparser.add_argument(
            "--max-files",
            type=int,
            default=argparse.SUPPRESS,
            help=f"maximum regular files to retain in memory (default: {DEFAULT_MAX_FILES})",
        )
        subparser.add_argument(
            "--max-entries",
            type=int,
            default=argparse.SUPPRESS,
            help=f"maximum directory entries to inspect (default: {DEFAULT_MAX_ENTRIES})",
        )
        subparser.add_argument(
            "--allow-broad-root",
            action="store_true",
            default=argparse.SUPPRESS,
            help="explicitly allow scanning filesystem root or home directory",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.max_files < 0:
        parser.error("--max-files must be non-negative")
    if args.max_entries < 0:
        parser.error("--max-entries must be non-negative")

    include_excluded = bool(getattr(args, "include_excluded", False))
    allow_broad_root = bool(getattr(args, "allow_broad_root", False))
    try:
        root = validate_root(args.root, allow_broad_root=allow_broad_root)
    except RootError as error:
        # CLI failures are reports, not tracebacks: callers can make the
        # unsupported/limited decision from the same schema as a scan.
        candidate = Path(args.root).expanduser().absolute()
        status = "limited" if "broad root" in str(error) else "unsupported"
        result = ScanResult(
            root=candidate,
            root_device=0,
            max_files=args.max_files,
            max_entries=args.max_entries,
            status=status,
            coverage_gaps=[str(error)],
            errors=[str(error)],
        )
        report = (
            summary_report(result, include_excluded=include_excluded)
            if args.command == "summary"
            else manifest_report(result, include_excluded=include_excluded)
        )
        sys.stdout.write(render(report, args.output_format))
        return 1
    result = scan(
        root,
        include_excluded=include_excluded,
        hash_files=args.command == "manifest",
        max_files=args.max_files,
        max_entries=args.max_entries,
        allow_broad_root=allow_broad_root,
    )
    report = (
        summary_report(result, include_excluded=include_excluded)
        if args.command == "summary"
        else manifest_report(result, include_excluded=include_excluded)
    )
    sys.stdout.write(render(report, args.output_format))
    return 1 if report["status"] != "complete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
