"""
ingestion/extract_git_log.py

Runs `git log` inside the project checkout and yields one Chunk per
commit: subject line + list of changed files.

Uses \\x1e (record separator) between commits and \\x1f (unit separator)
between fields within a commit — both are non-printable control
characters that essentially never appear in commit messages, so parsing
is a plain split() instead of a fragile regex over git's normal
human-readable log format.
"""
import logging
import subprocess
from collections.abc import Iterator

from .chunking import Chunk

logger = logging.getLogger(__name__)

_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
_LOG_FORMAT = f"{_RECORD_SEP}%H{_FIELD_SEP}%ai{_FIELD_SEP}%s"


def _run_git_log(source_path: str) -> str:
    result = subprocess.run(
        ["git", "log", f"--pretty=format:{_LOG_FORMAT}", "--name-only"],
        cwd=source_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def extract(project: str, source_path: str) -> Iterator[Chunk]:
    try:
        raw = _run_git_log(source_path)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.warning("Skipping git log extraction for %s: %s", source_path, exc)
        return

    for record in raw.split(_RECORD_SEP):
        if not record.strip():
            continue

        header, _, files_block = record.partition("\n")
        commit_hash, date, subject = header.split(_FIELD_SEP, 2)

        changed_files = [line for line in files_block.strip().splitlines() if line.strip()]
        if changed_files:
            files_repr = "\n".join(f"- {f}" for f in changed_files)
            text = f"{subject}\n\nChanged files:\n{files_repr}"
        else:
            text = subject

        yield Chunk(
            text=text,
            source_file="git log",
            chunk_type="commit",
            project=project,
            extra={"commit_hash": commit_hash, "date": date},
        )
        