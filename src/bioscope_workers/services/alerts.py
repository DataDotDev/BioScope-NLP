from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AlertResult:
    emitted: bool
    severity: str | None
    message: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"emitted": self.emitted, "severity": self.severity, "message": self.message}


class AlertService:
    def maybe_emit(self, envelope: dict[str, Any], classification: dict[str, Any], entities: dict[str, Any]) -> AlertResult:
        signal_class = str(classification.get("signal_class", ""))
        signal_types = classification.get("signal_types", [])

        if signal_class == "regulatory" and "safety_signal" in signal_types:
            return AlertResult(
                emitted=True,
                severity="high",
                message=self._build_message(envelope, entities, "high-risk regulatory safety signal detected"),
            )

        if signal_class in {"regulatory", "trial"}:
            return AlertResult(
                emitted=True,
                severity="medium",
                message=self._build_message(envelope, entities, f"{signal_class} signal detected"),
            )

        return AlertResult(emitted=False, severity=None, message=None)

    def _build_message(self, envelope: dict[str, Any], entities: dict[str, Any], suffix: str) -> str:
        source = envelope.get("source", "unknown")
        record_type = envelope.get("record_type", "unknown")
        company = ", ".join(entities.get("companies", [])[:2]) or "unknown company"
        drug = ", ".join(entities.get("drugs", [])[:2]) or "unknown drug"
        return f"{suffix} for {source}/{record_type} involving {company} and {drug}"
