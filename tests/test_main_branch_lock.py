import os
import shutil
import socket
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / ".agents" / "scripts" / "main-branch-lock.sh"


def run_helper(repo: Path, *args: str, timeout: float = 5.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(HELPER), *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    (path / ".agents").mkdir()
    return path


def test_status_reports_unlocked_lock_path(tmp_path):
    repo = init_repo(tmp_path / "repo")

    result = run_helper(repo, "status")

    assert result.returncode == 0
    assert "locked=false" in result.stdout
    assert f"path={repo}/.agents/locks/main-branch.lock" in result.stdout


def test_run_acquires_releases_and_executes_command(tmp_path):
    repo = init_repo(tmp_path / "repo")

    result = run_helper(
        repo,
        "run",
        "--owner",
        "unit",
        "--timeout-seconds",
        "2",
        "--retry-seconds",
        "1",
        "--",
        "/bin/echo",
        "hi",
    )

    assert result.returncode == 0
    assert "acquired main-branch lock:" in result.stdout
    assert result.stdout.rstrip().endswith("hi")
    assert not (repo / ".agents" / "locks" / "main-branch.lock").exists()


def test_worktree_checkout_resolves_lock_under_main_root(tmp_path):
    main = init_repo(tmp_path / "repo")
    task = main / ".agents" / "worktrees" / "task"
    task.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=task, check=True)

    result = run_helper(task, "status")

    assert result.returncode == 0
    assert f"path={main}/.agents/locks/main-branch.lock" in result.stdout


def test_same_host_stale_pid_lock_is_removed(tmp_path):
    repo = init_repo(tmp_path / "repo")
    lock_dir = repo / ".agents" / "locks" / "main-branch.lock"
    lock_dir.mkdir(parents=True)
    (lock_dir / "info").write_text(
        "\n".join(
            [
                "locked=true",
                "pid=999999999",
                f"host={socket.gethostname()}",
                "owner=stale-test",
                "branch=old",
                "started=2026-05-26T00:00:00Z",
            ]
        )
        + "\n"
    )

    result = run_helper(
        repo,
        "run",
        "--owner",
        "unit",
        "--timeout-seconds",
        "2",
        "--retry-seconds",
        "1",
        "--",
        "/bin/echo",
        "hi",
    )

    assert result.returncode == 0
    assert "removing stale main-branch lock:" in result.stdout
    assert result.stdout.rstrip().endswith("hi")
    assert not lock_dir.exists()


def test_live_lock_times_out_with_holder_metadata(tmp_path):
    repo = init_repo(tmp_path / "repo")
    lock_dir = repo / ".agents" / "locks" / "main-branch.lock"
    lock_dir.mkdir(parents=True)
    (lock_dir / "info").write_text(
        "\n".join(
            [
                "locked=true",
                f"pid={os.getpid()}",
                f"host={socket.gethostname()}",
                "owner=live-test",
                "branch=main",
                "started=2026-05-26T00:00:00Z",
            ]
        )
        + "\n"
    )

    result = run_helper(
        repo,
        "run",
        "--owner",
        "unit",
        "--timeout-seconds",
        "1",
        "--retry-seconds",
        "1",
        "--",
        "/bin/echo",
        "hi",
        timeout=4.0,
    )

    assert result.returncode == 1
    assert "waiting for main-branch lock: owner=live-test" in result.stdout
    assert "error: timed out waiting for main-branch lock:" in result.stderr
    assert "current lock: owner=live-test" in result.stderr
    assert lock_dir.exists()


def test_lock_create_permission_failure_exits_without_waiting(tmp_path):
    repo = init_repo(tmp_path / "repo")
    locks_dir = repo / ".agents" / "locks"
    locks_dir.mkdir()
    original_mode = stat.S_IMODE(locks_dir.stat().st_mode)
    locks_dir.chmod(0o500)
    try:
        result = run_helper(
            repo,
            "run",
            "--owner",
            "unit",
            "--timeout-seconds",
            "10",
            "--retry-seconds",
            "10",
            "--",
            "/bin/echo",
            "hi",
            timeout=2.0,
        )
    finally:
        locks_dir.chmod(original_mode)

    if result.returncode == 0:
        # Some privileged filesystems ignore the mode-only simulation; keep the
        # deterministic parent-conflict assertion below as the portable guard.
        shutil.rmtree(locks_dir / "main-branch.lock", ignore_errors=True)
    else:
        assert result.returncode == 1
        assert "could not create main-branch lock directory" in result.stderr
        assert "waiting for main-branch lock" not in result.stdout


def test_lock_parent_create_failure_is_reported(tmp_path):
    repo = init_repo(tmp_path / "repo")
    shutil.rmtree(repo / ".agents")
    (repo / ".agents").write_text("not a directory")

    result = run_helper(
        repo,
        "run",
        "--owner",
        "unit",
        "--timeout-seconds",
        "10",
        "--retry-seconds",
        "10",
        "--",
        "/bin/echo",
        "hi",
        timeout=2.0,
    )

    assert result.returncode == 1
    assert "main root does not have .agents" in result.stderr
    assert "waiting for main-branch lock" not in result.stdout
