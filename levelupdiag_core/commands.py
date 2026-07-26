"""Subprocess helpers shared by levels."""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

@dataclass(slots=True)
class StepResult:
    name: str
    command: str
    cwd: str
    status: str
    exit_code: int | None
    started_at: str
    ended_at: str
    duration_seconds: float
    output_tail: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def find_executable(name: str) -> str | None:
    return shutil.which(name)


def format_command(command: str | Sequence[str]) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def run_cmd(
    command: str | Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout: int | float = 120,
    name: str | None = None,
    env: Mapping[str, str] | None = None,
    shell: bool | None = None,
    tail_chars: int = 8000,
) -> StepResult:
    started = _dt.datetime.now()
    started_iso = started.isoformat(timespec="seconds")
    cmd_display = format_command(command)
    if shell is None:
        shell = isinstance(command, str)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            shell=shell,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=merged_env,
        )
        output = completed.stdout or ""
        status = "PASS" if completed.returncode == 0 else "FAIL"
        code: int | None = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output += f"\n[TIMEOUT after {timeout}s]"
        status = "INFRA_ERROR"
        code = None
    except Exception as exc:
        output = f"{type(exc).__name__}: {exc}"
        status = "INFRA_ERROR"
        code = None
    ended = _dt.datetime.now()
    return StepResult(
        name=name or cmd_display,
        command=cmd_display,
        cwd=str(Path(cwd).resolve()) if cwd else str(Path.cwd()),
        status=status,
        exit_code=code,
        started_at=started_iso,
        ended_at=ended.isoformat(timespec="seconds"),
        duration_seconds=round((ended - started).total_seconds(), 3),
        output_tail=output[-tail_chars:],
    )


def launch_console(command: str, cwd: str | Path, title: str = "LevelUpDiag") -> subprocess.Popen:
    if os.name == "nt":
        shell = shutil.which("pwsh.exe") or shutil.which("powershell.exe") or "powershell.exe"
        ps_command = f"$Host.UI.RawUI.WindowTitle = '{title}'; Set-Location -LiteralPath '{Path(cwd)}'; {command}"
        return subprocess.Popen([shell, "-NoLogo", "-NoExit", "-Command", ps_command], cwd=str(cwd), creationflags=0x00000010)
    return subprocess.Popen(command, cwd=str(cwd), shell=True)
