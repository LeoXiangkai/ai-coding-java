"""Run the installed AICJ components against disposable repositories."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import doctor, manifest, settings


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


def _commit(repo: Path, *args: str) -> None:
    _git(repo, "-c", "user.name=aicj-selftest", "-c", "user.email=selftest@localhost", "commit", *args)


def _fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    remote = root / "remote.git"
    repo = root / "repo"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _git(repo, "remote", "add", "origin", str(remote))
    _commit(repo, "--allow-empty", "-m", "initial")
    _git(repo, "push", "-u", "origin", "main")
    (repo / "init.sql").write_text("CREATE TABLE selftest_table (id INTEGER);\n", encoding="utf-8")
    _git(repo, "add", "init.sql")
    _commit(repo, "-m", "database migration")
    return repo


def _payload(repo: Path, command: str) -> str:
    return json.dumps(
        {
            "session_id": "aicj-selftest",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": str(repo),
        },
        ensure_ascii=False,
    )


def _hook_rows(home: Path) -> List[dict]:
    payload = settings.load(home / ".claude/settings.json")
    container = payload.get("hooks")
    if not isinstance(container, dict):
        return []
    rows = []
    for group in container.get("PreToolUse", []) or []:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []) or []:
            if not isinstance(hook, dict):
                continue
            command = hook.get("command", "")
            args = settings._hook_args(hook)
            if settings._owned(command, args):
                rows.append({"command": str(command), "args": args})
    return rows


def _run_hook(row: dict, payload: str, cwd: Path, env: Dict[str, str]) -> subprocess.CompletedProcess:
    args = list(row["args"])
    command = row["command"]
    legacy_shell = not args and any(char.isspace() for char in command.strip())
    invocation = [command, *args] if not legacy_shell else command
    return subprocess.run(
        invocation,
        input=payload,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=legacy_shell,
        timeout=60,
    )


def _line(status: str, name: str, detail: str) -> Tuple[str, str, str]:
    return status, name, detail.replace("\n", " ").strip()


def _executor_mode(home: Path) -> str:
    try:
        data = json.loads((home / ".claude/aicj/config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "cc"
    return "worker" if isinstance(data, dict) and str(data.get("executor_mode", "")).strip().casefold() == "worker" else "cc"


def _worker_invocation(home: Path, *args: str) -> List[str]:
    worker = home / ".claude/bin/aicj-worker"
    if os.name == "nt":
        worker = worker.with_suffix(".cmd")
        if not worker.is_file():
            raise RuntimeError("未找到 aicj-worker.cmd")
        return [os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", str(worker), *args]
    if not worker.is_file():
        raise RuntimeError("未找到 aicj-worker")
    return [str(worker), *args]


def _linked_worktree(repo: Path, path: Path) -> None:
    _git(repo, "worktree", "add", "-b", "aicj-selftest-linked", str(path), "HEAD")


def _remove_linked_worktree(repo: Path, path: Path) -> None:
    _git(repo, "worktree", "remove", "--force", str(path), check=False)
    _git(repo, "worktree", "prune", check=False)


def _cpa_check(env: Dict[str, str]) -> Tuple[bool, str]:
    base_url = env.get("AICJ_EXECUTOR_BASE_URL", "").strip()
    token = env.get("AICJ_EXECUTOR_TOKEN", "").strip()
    if not base_url:
        return True, "未配置 AICJ_EXECUTOR_BASE_URL，未执行连通性检查"
    if not token:
        return False, "AICJ_EXECUTOR_TOKEN 未设置"
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/models",
        headers={"Authorization": "Bearer " + token},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=3) as response:
            if response.status != 200:
                return False, f"CPA 返回 HTTP {response.status}"
    except Exception as exc:
        return False, f"CPA 不可达：{exc}"
    return True, "CPA /v1/models 返回 200"


def _worker_checks(home: Path, root: Path, env: Dict[str, str], checks: List[Tuple[str, str, str]]) -> None:
    linked = root / "linked"
    try:
        repo = _fixture(root / "worker")
        _linked_worktree(repo, linked)
        dry = subprocess.run(
            _worker_invocation(home, "--cd", str(linked), "--tier", "low", "--dry-run", "selftest"),
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        token = env.get("AICJ_EXECUTOR_TOKEN", "").strip()
        dry_ok = dry.returncode == 0 and "claude" in dry.stdout and (not token or token not in dry.stdout)
        checks.append(_line("PASS" if dry_ok else "FAIL", "worker dry-run", "linked worktree 可执行且输出引擎命令" if dry_ok else f"exit={dry.returncode}，输出={dry.stdout[:500]} {dry.stderr[:200]}"))
        main = subprocess.run(
            _worker_invocation(home, "--cd", str(repo), "--tier", "low", "--dry-run", "selftest"),
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        main_ok = main.returncode == 2
        checks.append(_line("PASS" if main_ok else "FAIL", "worker 主工作区校验", "主工作区按约定拒绝" if main_ok else f"exit={main.returncode}，stderr={main.stderr[:300]}"))
    except Exception as exc:
        checks.extend(_line("FAIL", name, str(exc)) for name in ("worker dry-run", "worker 主工作区校验"))
    finally:
        if (root / "worker/repo").is_dir():
            _remove_linked_worktree(root / "worker/repo", linked)

    poll = next((row for row in _hook_rows(home) if "block-handoff-poll" in settings._script_path(row["command"], row["args"])), None)
    if poll is None:
        checks.append(_line("FAIL", "block-handoff-poll", "settings.json 未登记 block-handoff-poll"))
    else:
        poll_repo = root / "poll-repo"
        poll_repo.mkdir(parents=True, exist_ok=True)
        intercept = _run_hook(
            poll,
            _payload(poll_repo, "sleep 1; cat /tasks/job.output"),
            poll_repo,
            {**env, "AICJ_HOOK_MODE": "block"},
        )
        allow = _run_hook(poll, _payload(poll_repo, "git status"), poll_repo, {**env, "AICJ_HOOK_MODE": "block"})
        poll_ok = intercept.returncode == 2 and allow.returncode == 0
        checks.append(_line("PASS" if poll_ok else "FAIL", "block-handoff-poll", "轮询 payload 拦截、普通命令放行" if poll_ok else f"拦截 exit={intercept.returncode}，放行 exit={allow.returncode}"))

    cpa_ok, cpa_detail = _cpa_check(env)
    cpa_status = "N/A" if not env.get("AICJ_EXECUTOR_BASE_URL", "").strip() else ("PASS" if cpa_ok else "FAIL")
    checks.append(_line(cpa_status, "CPA connectivity", cpa_detail))

def _worker_claude_check(home: Path, root: Path, env: Dict[str, str], checks: List[Tuple[str, str, str]]) -> None:
    linked = root / "claude-linked"
    try:
        repo = _fixture(root / "claude-worker")
        _linked_worktree(repo, linked)
        result = subprocess.run(
            _worker_invocation(
                home,
                "--cd",
                str(linked),
                "--tier",
                "low",
                "在当前目录创建文件 selftest-worker.txt，内容为 ok，不做其他事",
            ),
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        target = linked / "selftest-worker.txt"
        if result.returncode == 0 and target.is_file() and "ok" in target.read_text(encoding="utf-8", errors="replace"):
            checks.append(_line("PASS", "aicj-worker claude", "执行体经 worker 在 linked worktree 创建文件"))
        elif result.returncode == 127 or any(word in output.casefold() for word in ("登录", "认证", "403", "authentication", "login", "not found")):
            checks.append(_line("SKIP", "aicj-worker claude", output[:500] + "；外部执行体不可用或未登录"))
        else:
            checks.append(_line("FAIL", "aicj-worker claude", output[:500]))
    except subprocess.TimeoutExpired:
        checks.append(_line("FAIL", "aicj-worker claude", "执行超时"))
    except Exception as exc:
        checks.append(_line("FAIL", "aicj-worker claude", str(exc)))
    finally:
        if (root / "claude-worker/repo").is_dir():
            _remove_linked_worktree(root / "claude-worker/repo", linked)


def _run(home: Path, source: Optional[Path], with_claude: bool) -> List[Tuple[str, str, str]]:
    checks = []
    mode = _executor_mode(home)
    checks.append(_line("PASS", "模式", mode))
    try:
        doctor_checks, doctor_code = doctor.run_doctor(home, source)
        failed = [name for status, name, _detail in doctor_checks if status == doctor.MISSING]
        checks.append(_line("PASS" if doctor_code == 0 else "FAIL", "doctor", "通过" if doctor_code == 0 else "失败项：" + ", ".join(failed)))
    except Exception as exc:
        checks.append(_line("FAIL", "doctor", str(exc)))

    try:
        loaded = manifest.load(home)
        if loaded is None:
            raise RuntimeError("manifest 不存在")
        skills = [entry.path for entry in loaded.entries if entry.kind in ("skill-dir", "skill-copy")]
        missing = [f"{path}/SKILL.md" for path in skills if not (home / path / "SKILL.md").is_file()]
        checks.append(_line("PASS" if not missing else "FAIL", "skills", "清单中的技能均存在" if not missing else "缺少：" + ", ".join(missing)))
    except Exception as exc:
        checks.append(_line("FAIL", "skills", str(exc)))

    try:
        rows = _hook_rows(home)
        checks.append(_line("PASS" if rows else "FAIL", "hook registration", "已登记 AICJ PreToolUse 钩子" if rows else "未找到属于 aicj 的 PreToolUse 钩子"))
    except Exception as exc:
        rows = []
        checks.append(_line("FAIL", "hook registration", str(exc)))

    temp_name = tempfile.mkdtemp(prefix="aicj-selftest-")
    root = Path(temp_name)
    try:
        repo = None
        logs = root / "logs"
        env_base = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
        for key in (
            "AICJ_EXECUTOR_BASE_URL",
            "AICJ_EXECUTOR_TOKEN",
            "AICJ_EXECUTOR_CONFIG_DIR",
            "AICJ_EXECUTOR_ENGINE",
            "AICJ_EXECUTOR_TIMEOUT",
            "AICJ_EXECUTOR_MODEL_LOW",
            "AICJ_EXECUTOR_MODEL_MID",
            "AICJ_EXECUTOR_MODEL_HIGH",
        ):
            if key in os.environ:
                env_base[key] = os.environ[key]
        env_base.update(
            {
                "AICJ_REVIEW_LOG_DIR": str(logs),
                "AICJ_CLAUDE_DIR": str(home / ".claude"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )

        if mode == "worker":
            _worker_checks(home, root, env_base, checks)
        else:
            for name in ("worker dry-run", "worker 主工作区校验", "block-handoff-poll", "CPA connectivity", "aicj-worker claude"):
                checks.append(_line("N/A", name, "cc 模式，未安装 executor 适配"))

        if rows:
            try:
                repo = _fixture(root / "hooks")
                push_row = next((row for row in rows if "push-review-gate" in settings._script_path(row["command"], row["args"])), None)
                if push_row is None:
                    raise RuntimeError("登记的 AICJ 钩子中没有 push-review-gate")
                warn_log = logs / "gate-events.jsonl"
                warn_before = _event_count(warn_log)
                warn = _run_hook(push_row, _payload(repo, "git push origin main"), repo, {**env_base, "AICJ_HOOK_MODE": "warn"})
                warn_event = _event_count(warn_log) > warn_before and _has_event(warn_log, "deny")
                warn_ok = warn.returncode == 0 and "push-review-gate" in warn.stderr and warn_event
                checks.append(_line("PASS" if warn_ok else "FAIL", "4a push-review-gate warn", f"exit={warn.returncode}，已记录 deny" if warn_ok else f"exit={warn.returncode}，stderr={warn.stderr[:160]}"))
                block = _run_hook(push_row, _payload(repo, "git push origin main"), repo, {**env_base, "AICJ_HOOK_MODE": "block"})
                block_ok = block.returncode == 2 and "拒绝 push" in block.stderr
                checks.append(_line("PASS" if block_ok else "FAIL", "4b push-review-gate block", "exit=2，已拦截" if block_ok else f"exit={block.returncode}，stderr={block.stderr[:160]}"))
                nonpush_before = _event_count(warn_log)
                nonpush = _run_hook(push_row, _payload(repo, "git status"), repo, {**env_base, "AICJ_HOOK_MODE": "block"})
                nonpush_after = _event_count(warn_log)
                nonpush_ok = nonpush.returncode == 0 and nonpush_after == nonpush_before
                checks.append(_line("PASS" if nonpush_ok else "FAIL", "4c push-review-gate non-push", "git status 放行且无新增拦截日志" if nonpush_ok else f"exit={nonpush.returncode}，日志 {nonpush_before}->{nonpush_after}"))
            except subprocess.TimeoutExpired:
                checks.extend(_line("FAIL", name, "钩子执行超时") for name in ("4a push-review-gate warn", "4b push-review-gate block", "4c push-review-gate non-push"))
            except Exception as exc:
                checks.extend(_line("FAIL", name, str(exc)) for name in ("4a push-review-gate warn", "4b push-review-gate block", "4c push-review-gate non-push"))
        else:
            checks.extend(_line("FAIL", name, "未找到 push-review-gate 登记") for name in ("4a push-review-gate warn", "4b push-review-gate block", "4c push-review-gate non-push"))

        rewrite = next((row for row in rows if "git-safe-rewrite" in settings._script_path(row["command"], row["args"])), None)
        if rewrite is None:
            checks.append(_line("SKIP", "5 git-safe-rewrite", "可选钩子未启用"))
        else:
            try:
                result = _run_hook(rewrite, _payload(root, "git commit -m x"), root, env_base)
                parsed = json.loads(result.stdout) if result.stdout.strip() else {}
                rewritten = isinstance(parsed, dict) and "git-safe" in result.stdout
                checks.append(_line("PASS" if result.returncode == 0 and rewritten else "FAIL", "5 git-safe-rewrite", "输出改写后的 JSON" if result.returncode == 0 and rewritten else f"exit={result.returncode}，输出={result.stdout[:160]}"))
            except Exception as exc:
                checks.append(_line("FAIL", "5 git-safe-rewrite", str(exc)))

        try:
            launcher = home / ".claude/bin/git-safe"
            if os.name == "nt":
                launcher = launcher.with_suffix(".cmd")
            result = subprocess.run([str(launcher), "status"], cwd=repo or root, env=env_base, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            checks.append(_line("PASS" if result.returncode == 0 else "FAIL", "6 git-safe launcher", "git-safe status 执行成功" if result.returncode == 0 else f"exit={result.returncode}，stderr={result.stderr[:160]}"))
        except Exception as exc:
            checks.append(_line("FAIL", "6 git-safe launcher", str(exc)))

        if mode == "worker" and with_claude:
            _worker_claude_check(home, root, env_base, checks)
        elif mode == "cc":
            if not with_claude:
                checks.append(_line("SKIP", "claude-code", "未请求（加 --with-claude）"))
            else:
                claude = shutil.which("claude")
                if not claude:
                    checks.append(_line("SKIP", "claude-code", "未找到 claude 命令"))
                else:
                    try:
                        claude_repo = _fixture(root / "claude-run")
                        claude_logs = root / "claude-logs"
                        claude_env = {**env_base, "AICJ_HOOK_MODE": "block", "AICJ_REVIEW_LOG_DIR": str(claude_logs)}
                        if home.resolve() != Path.home().resolve():
                            claude_env["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
                        result = subprocess.run(
                            [claude, "-p", "在当前目录执行这一条命令：git push origin main 。只执行这一条，然后原样报告输出。", "--allowedTools", "Bash(git push:*)", "--max-turns", "3", "--output-format", "text"],
                            cwd=claude_repo,
                            env=claude_env,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            timeout=300,
                        )
                        output = (result.stdout + "\n" + result.stderr).strip()
                        passed = _has_event(claude_logs / "gate-events.jsonl", "deny")
                        auth = any(word in output.casefold() for word in ("登录", "认证", "403", "authentication", "network", "login"))
                        if passed:
                            checks.append(_line("PASS", "claude-code", "Claude Code 调用了钩子并拦截"))
                        elif result.returncode != 0 and auth:
                            checks.append(_line("SKIP", "claude-code", output[:500] + "；先运行 claude 登录后重跑"))
                        else:
                            checks.append(_line("FAIL", "claude-code", output[:500]))
                    except subprocess.TimeoutExpired:
                        checks.append(_line("FAIL", "claude-code", "执行超时"))
                    except Exception as exc:
                        checks.append(_line("FAIL", "claude-code", str(exc)))
        else:
            checks.append(_line("SKIP", "claude-code", "未请求（加 --with-claude）"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return checks


def _event_count(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _has_event(path: Path, event: str) -> bool:
    try:
        return any(json.loads(line).get("event") == event for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except (OSError, json.JSONDecodeError, TypeError):
        return False


def run_selftest(home: Path, source: Optional[Path] = None, with_claude: bool = False) -> int:
    checks = _run(home, source, with_claude)
    for status, name, detail in checks:
        print(f"{status:<4}  {name}  {detail}")
    counts = Counter(status for status, _name, _detail in checks)
    print("summary          " + " ".join(f"{name}={counts[name]}" for name in ("PASS", "FAIL", "SKIP", "N/A")))
    return 1 if counts["FAIL"] else 0
