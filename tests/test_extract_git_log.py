"""
Tests for ingestion/extract_git_log.py — control-character-delimited
git log parsing (ADR-010) and graceful degradation when there's no repo.
"""
import subprocess

from ingestion.extract_git_log import extract


def _init_repo_with_commit(repo_path, filename="foo.py", message="feat: add foo"):
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, check=True)

    (repo_path / filename).write_text("print('hi')\n")
    subprocess.run(["git", "add", filename], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo_path, check=True)


def test_extract_yields_one_chunk_per_commit(tmp_path):
    _init_repo_with_commit(tmp_path, "foo.py", "feat: add foo")

    chunks = list(extract("myproject", str(tmp_path)))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_type == "commit"
    assert chunk.source_file == "git log"
    assert "feat: add foo" in chunk.text
    assert "foo.py" in chunk.text
    assert "commit_hash" in chunk.extra
    assert "date" in chunk.extra


def test_extract_handles_commit_message_with_delimiter_like_characters(tmp_path):
    """
    The whole point of ADR-010: colons, dashes, pipes in the commit
    subject must not break parsing.
    """
    _init_repo_with_commit(tmp_path, "bar.py", "fix: handle edge-case | value: -1 -- retry")

    chunks = list(extract("myproject", str(tmp_path)))

    assert len(chunks) == 1
    assert "fix: handle edge-case | value: -1 -- retry" in chunks[0].text


def test_extract_returns_empty_for_non_git_directory(tmp_path):
    """No .git directory — must degrade to zero chunks, not raise."""
    chunks = list(extract("myproject", str(tmp_path)))
    assert chunks == []
    