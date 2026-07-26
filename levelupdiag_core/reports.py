"""Common JSON/TXT report model for LevelUpDiag."""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .verdicts import PASS, normalize, worst

@dataclass(slots=True)
class Finding:
    id: str
    severity: str
    category: str
    message: str
    file: str | None = None
    route: str | None = None
    endpoint: str | None = None
    evidence: str | None = None
    recommendation: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class Artifact:
    kind: str
    path: str
    description: str = ""

@dataclass(slots=True)
class DiagReport:
    schema: str
    standard: str
    standard_version: str
    level: str
    name: str
    started_at: str
    finished_at: str
    app_name: str
    target_repo_root: str
    frontend_url: str
    backend_url: str
    verdict: str
    summary: dict[str, int]
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, *, level: str, name: str, app_name: str, target_repo_root: str, frontend_url: str, backend_url: str) -> "DiagReport":
        now = _dt.datetime.now().isoformat(timespec="seconds")
        return cls(
            schema="levelupdiag.report.v1",
            standard="LevelUpDiag",
            standard_version="0.2.0",
            level=level,
            name=name,
            started_at=now,
            finished_at=now,
            app_name=app_name,
            target_repo_root=target_repo_root,
            frontend_url=frontend_url,
            backend_url=backend_url,
            verdict=PASS,
            summary={"pass": 0, "warn": 0, "fail": 0, "skip": 0, "blocked": 0, "partial": 0, "infra_error": 0, "config_error": 0, "error": 0},
        )

    def add(self, id: str, severity: str, category: str, message: str, **kwargs: Any) -> None:
        self.findings.append(Finding(id=id, severity=severity, category=category, message=message, **kwargs))
        self.recompute()

    def recompute(self) -> None:
        counts = {key: 0 for key in self.summary}
        statuses: list[str] = []
        for finding in self.findings:
            sev = normalize(finding.severity)
            statuses.append(sev)
            counts[sev.lower()] = counts.get(sev.lower(), 0) + 1
        self.summary = counts
        self.verdict = worst(statuses)
        self.finished_at = _dt.datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        self.recompute()
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p

    def write_txt(self, path: str | Path) -> Path:
        self.recompute()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"LevelUpDiag report: {self.level} — {self.name}",
            f"Verdict: {self.verdict}",
            f"App: {self.app_name}",
            f"Target: {self.target_repo_root}",
            f"Started: {self.started_at}",
            f"Finished: {self.finished_at}",
            "",
            "Findings:",
        ]
        for item in self.findings:
            lines.append(f"- [{item.severity}] {item.id}: {item.message}")
            if item.recommendation:
                lines.append(f"  fix: {item.recommendation}")
            if item.evidence:
                lines.append(f"  evidence: {item.evidence}")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p
