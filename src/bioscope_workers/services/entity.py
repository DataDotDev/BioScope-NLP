from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

COMPANY_SUFFIXES = (
    "inc",
    "inc.",
    "ltd",
    "ltd.",
    "llc",
    "plc",
    "gmbh",
    "corp",
    "corp.",
    "corporation",
    "company",
    "co",
    "co.",
    "sa",
    "ag",
)

DRUG_PATTERN = re.compile(r"\b([A-Z]{2,8}-?\d{2,6}|[A-Za-z][A-Za-z0-9]+(?:mab|nib|vir|stat|cept|ase|zumab|ciclib))\b")
PHASE_PATTERN = re.compile(r"\bphase\s*(i{1,3}|iv|1|2|3|4)\b", re.IGNORECASE)


@dataclass(slots=True)
class EntityResult:
    companies: list[str]
    drugs: list[str]
    phases: list[str]
    mentions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "companies": self.companies,
            "drugs": self.drugs,
            "phases": self.phases,
            "mentions": self.mentions,
        }


class EntityService:
    def extract(self, envelope: dict[str, Any]) -> EntityResult:
        normalized = envelope.get("normalized", {})
        raw = envelope.get("raw", {})

        text_parts = [
            str(normalized.get("title", "")),
            str(normalized.get("brief_title", "")),
            str(normalized.get("company", "")),
            str(normalized.get("sponsor", "")),
            str(normalized.get("product_name", "")),
            str(normalized.get("intervention_name", "")),
            str(raw.get("title", "")),
            str(raw.get("description", "")),
            str(raw.get("label", "")),
            str(raw.get("summary", "")),
        ]
        text = " ".join(part for part in text_parts if part).strip()

        companies = self._extract_companies(normalized, raw, text)
        drugs = self._extract_drugs(normalized, raw, text)
        phases = self._extract_phases(normalized, raw, text)
        mentions = self._extract_mentions(text)

        return EntityResult(companies=companies, drugs=drugs, phases=phases, mentions=mentions)

    def _extract_companies(self, normalized: dict[str, Any], raw: dict[str, Any], text: str) -> list[str]:
        candidates: list[str] = []
        for key in ("company", "sponsor", "manufacturer", "marketing_authorization_holder"):
            value = normalized.get(key) or raw.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value)

        if not candidates and text:
            head = text.split(".", 1)[0].split(",", 1)[0].strip()
            if head:
                candidates.append(head)

        normalized_candidates = [self._normalize_company_name(candidate) for candidate in candidates]
        return self._dedupe(normalized_candidates)

    def _normalize_company_name(self, value: str) -> str:
        tokens = value.replace("/", " ").replace("-", " ").split()
        filtered = [token for token in tokens if token.lower().rstrip(".,") not in COMPANY_SUFFIXES]
        return " ".join(filtered).strip() or value.strip()

    def _extract_drugs(self, normalized: dict[str, Any], raw: dict[str, Any], text: str) -> list[str]:
        explicit_candidates: list[str] = []
        for key in ("drug", "product_name", "intervention_name", "active_substance"):
            value = normalized.get(key) or raw.get(key)
            if isinstance(value, str) and value.strip():
                explicit_candidates.append(value.strip())

        regex_candidates = [
            match.group(1)
            for match in DRUG_PATTERN.finditer(text)
            if self._looks_like_drug(match.group(1))
        ]

        candidates = explicit_candidates + regex_candidates
        return self._dedupe([self._normalize_drug_name(candidate) for candidate in candidates])

    def _normalize_drug_name(self, value: str) -> str:
        return value.strip().replace("  ", " ")

    def _looks_like_drug(self, value: str) -> bool:
        token = value.strip().lower()
        if token in {"phase", "study", "trial", "signal", "company", "product", "update"}:
            return False
        return any(char.isdigit() for char in token) or "-" in token or token.endswith(("mab", "nib", "vir", "stat", "cept", "ase", "zumab", "ciclib"))

    def _extract_phases(self, normalized: dict[str, Any], raw: dict[str, Any], text: str) -> list[str]:
        values: list[str] = []
        for key in ("phase", "trial_phase"):
            value = normalized.get(key) or raw.get(key)
            if isinstance(value, str) and value.strip():
                values.append(self._normalize_phase(value))

        values.extend(self._normalize_phase(match.group(1)) for match in PHASE_PATTERN.finditer(text))
        return self._dedupe(values)

    def _normalize_phase(self, value: str) -> str:
        value = value.strip().lower().replace("phase", "").strip()
        roman_map = {"i": "Phase I", "ii": "Phase II", "iii": "Phase III", "iv": "Phase IV"}
        if value in roman_map:
            return roman_map[value]
        numeric_map = {"1": "Phase I", "2": "Phase II", "3": "Phase III", "4": "Phase IV"}
        return numeric_map.get(value, f"Phase {value.upper()}")

    def _extract_mentions(self, text: str) -> list[str]:
        mentions = []
        for token in re.findall(r"\b[A-Za-z][A-Za-z0-9-]{3,}\b", text):
            if token.lower() not in {"title", "study", "trial", "patient", "company"}:
                mentions.append(token)
        return self._dedupe(mentions[:12])

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = value.strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result
