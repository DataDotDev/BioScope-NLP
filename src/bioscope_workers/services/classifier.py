from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PHASE_KEYWORDS = {
    "phase i": "trial_phase",
    "phase ii": "trial_phase",
    "phase iii": "trial_phase",
    "phase iv": "trial_phase",
    "first-in-human": "trial_phase",
    "pivotal": "trial_phase",
}

REGULATORY_KEYWORDS = {
    "fda": "regulatory",
    "ema": "regulatory",
    "warning": "regulatory",
    "recall": "regulatory",
    "label change": "regulatory",
    "approval": "regulatory",
    "safety communication": "regulatory",
}

SIGNAL_KEYWORDS = {
    "adverse event": "safety_signal",
    "serious adverse event": "safety_signal",
    "signal": "signal",
    "efficacy": "efficacy_signal",
    "supply": "manufacturing_signal",
    "launch": "commercial_signal",
    "partnership": "company_signal",
}


@dataclass(slots=True)
class ClassificationResult:
    signal_class: str
    signal_types: list[str]
    evidence: list[str]
    source_family: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_class": self.signal_class,
            "signal_types": self.signal_types,
            "evidence": self.evidence,
            "source_family": self.source_family,
        }


class ClassifierService:
    def classify(self, envelope: dict[str, Any], entities: dict[str, Any]) -> ClassificationResult:
        normalized = envelope.get("normalized", {})
        raw = envelope.get("raw", {})
        source = str(envelope.get("source", "")).lower()
        record_type = str(envelope.get("record_type", "")).lower()
        text = " ".join(
            str(part)
            for part in (
                normalized.get("title", ""),
                normalized.get("brief_title", ""),
                normalized.get("summary", ""),
                raw.get("title", ""),
                raw.get("description", ""),
                raw.get("label", ""),
            )
            if part
        ).lower()

        signal_types = self._classify_signals(text, source, record_type, entities)
        evidence = self._collect_evidence(envelope, entities)
        signal_class = self._resolve_signal_class(signal_types, source, record_type)
        source_family = self._infer_source_family(source, record_type)

        return ClassificationResult(
            signal_class=signal_class,
            signal_types=signal_types,
            evidence=evidence,
            source_family=source_family,
        )

    def _classify_signals(self, text: str, source: str, record_type: str, entities: dict[str, Any]) -> list[str]:
        signal_types: list[str] = []

        for keyword, signal_type in PHASE_KEYWORDS.items():
            if keyword in text:
                signal_types.append(signal_type)

        for keyword, signal_type in REGULATORY_KEYWORDS.items():
            if keyword in text or keyword in source or keyword in record_type:
                signal_types.append(signal_type)

        for keyword, signal_type in SIGNAL_KEYWORDS.items():
            if keyword in text:
                signal_types.append(signal_type)

        if entities.get("companies"):
            signal_types.append("company_signal")
        if entities.get("drugs"):
            signal_types.append("drug_signal")

        return self._dedupe(signal_types)

    def _collect_evidence(self, envelope: dict[str, Any], entities: dict[str, Any]) -> list[str]:
        evidence: list[str] = []
        for key in ("source", "record_type", "observed_at", "ingested_at"):
            value = envelope.get(key)
            if isinstance(value, str) and value:
                evidence.append(f"{key}:{value}")

        for company in entities.get("companies", []):
            evidence.append(f"company:{company}")

        for drug in entities.get("drugs", []):
            evidence.append(f"drug:{drug}")

        return evidence[:10]

    def _resolve_signal_class(self, signal_types: list[str], source: str, record_type: str) -> str:
        if "regulatory" in signal_types:
            return "regulatory"
        if "trial_phase" in signal_types:
            return "trial"
        if "safety_signal" in signal_types:
            return "safety"
        if source.startswith("clinicaltrials") or "trial" in record_type:
            return "trial"
        if source.startswith("fda") or source.startswith("ema"):
            return "regulatory"
        if any(signal in signal_types for signal in ("company_signal", "commercial_signal")):
            return "company"
        return "general"

    def _infer_source_family(self, source: str, record_type: str) -> str:
        if "clinicaltrials" in source:
            return "clinical_trials"
        if "fda" in source:
            return "fda_openfda"
        if "ema" in source:
            return "ema_rss"
        if "trial" in record_type:
            return "clinical_trials"
        return "unknown"

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = value.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result
