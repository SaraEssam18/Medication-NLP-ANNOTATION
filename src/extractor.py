"""
extractor.py

Rule-based medication extractor for Arabic / mixed Arabic-English clinical
text, built as a practical starting point ahead of a trained NER model
(see README.md, "Suggested next steps").

Design principles (do not weaken these):
  1. Never guess. Any dose/route/frequency not explicitly present in the
     text is left as NOT_STATED.
  2. Any vague drug reference (not a recognized generic/brand name) is
     tagged DRUG_VAGUE and automatically flagged for human review.
  3. Any high-risk / error-prone abbreviation (ISMP-style) found in the
     text raises ambiguous_abbreviation_flag = True.
  4. This tool produces DRAFT annotations only. It is not a diagnostic or
     prescribing tool and must not be used to make clinical decisions
     without pharmacist/physician review.

Usage:
    python -m src.extractor "input text" --note-id N010
    python -m src.extractor --file path/to/notes.txt
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import List

from src.schema import MedicationRecord, NOT_STATED

BASE_DIR = Path(__file__).resolve().parent.parent
LEXICON_PATH = BASE_DIR / "config" / "drug_lexicon.json"
ABBREV_PATH = BASE_DIR / "config" / "high_risk_abbreviations_reference.csv"

DOSE_PATTERN = re.compile(
    r"(?P<value>\d+(\.\d+)?)\s*(?P<unit>mg|ملغ|ملغم|mcg|ميكروغرام|ml|مل|unit|units|وحدة|وحدات)?",
    re.IGNORECASE,
)


def load_lexicon() -> dict:
    with open(LEXICON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_abbreviations() -> List[dict]:
    with open(ABBREV_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class MedicationExtractor:
    def __init__(self):
        self.lexicon = load_lexicon()
        self.abbreviations = load_abbreviations()

    # ---------- helpers ----------

    def _find_term(self, text: str, term_map: dict):
        """Return (matched_surface_text, canonical_value) for the first
        term from term_map found in text, else (None, None)."""
        lowered = text.lower()
        # sort by length desc so multi-word phrases match before single words
        for term in sorted(term_map.keys(), key=len, reverse=True):
            if term.lower() in lowered:
                return term, term_map[term]
        return None, None

    def _find_any(self, text: str, terms: list):
        lowered = text.lower()
        for term in sorted(terms, key=len, reverse=True):
            if term.lower() in lowered:
                return term
        return None

    def _extract_dose(self, text: str):
        match = DOSE_PATTERN.search(text)
        if not match:
            return NOT_STATED, NOT_STATED
        value = match.group("value") or NOT_STATED
        unit = match.group("unit") or NOT_STATED
        return value, unit

    def _flag_abbreviations(self, text: str):
        lowered = f" {text.lower()} "
        hits = []
        for row in self.abbreviations:
            abbr = row["abbreviation"].split(" ")[0].lower()  # e.g. "U (unit)" -> "u"
            abbr = abbr.strip("().,")
            if not abbr:
                continue
            pattern = r"(?<![a-zA-Z\u0600-\u06FF])" + re.escape(abbr) + r"(?![a-zA-Z\u0600-\u06FF])"
            if re.search(pattern, lowered):
                hits.append(row)
        return hits

    # ---------- main entry point ----------

    def extract(self, text: str, note_id: str = "N000",
                assertion_source: str = "chart") -> List[MedicationRecord]:
        records: List[MedicationRecord] = []

        # negation check (very conservative — flags for review, doesn't suppress)
        negation_markers = ["لا يأخذ", "ما يأخذ", "not taking", "denies", "stopped taking"]
        negated = any(m in text for m in negation_markers)

        # 1) generic names
        term, canonical = self._find_term(text, self.lexicon["generic"])
        # 2) truncated/ambiguous generic names (e.g. "Atorva")
        trunc_term, trunc_canonical = self._find_term(text, self.lexicon["generic_truncated"])
        # 3) brand names
        brand_term, brand_canonical = self._find_term(text, self.lexicon["brand"])
        # 4) vague terms
        vague_term = self._find_any(text, self.lexicon["vague_terms"])

        matches = []
        if term:
            matches.append(("DRUG_GENERIC", term, canonical, "High"))
        if trunc_term:
            matches.append(("DRUG_GENERIC", trunc_term, trunc_canonical, "Medium"))
        if brand_term:
            matches.append(("DRUG_BRAND", brand_term, brand_canonical, "Medium"))
        if vague_term:
            matches.append(("DRUG_VAGUE", vague_term, None, "Low"))

        if not matches:
            return records  # nothing recognized in this text

        abbrev_hits = self._flag_abbreviations(text)

        for entity_type, surface_text, canonical_name, base_confidence in matches:
            dose_value, dose_unit = self._extract_dose(text)

            route_term, route_val = self._find_term(text, self.lexicon["route_terms"])
            freq_term, freq_val = self._find_term(text, self.lexicon["frequency_terms"])
            status_term, status_val = self._find_term(text, self.lexicon["status_terms"])

            rec = MedicationRecord(
                note_id=note_id,
                entity_text=surface_text,
                entity_type=entity_type,
                normalized_code=canonical_name,
                dose_value=dose_value,
                dose_unit=dose_unit,
                route=route_val or NOT_STATED,
                frequency=freq_val or NOT_STATED,
                status=status_val or ("PRN" if "PRN" in (freq_val or "") else "unknown"),
                negation=negated,
                assertion_source=assertion_source,
                source_sentence=text.strip(),
            )

            # --- confidence + review policy (never silently trust) ---
            confidence = base_confidence
            reasons = []

            if dose_unit == NOT_STATED and entity_type != "DRUG_VAGUE":
                reasons.append("وحدة الجرعة غير مذكورة في النص")
                confidence = "Medium" if confidence == "High" else confidence
            if route_val is None:
                reasons.append("طريقة الإعطاء غير مذكورة")
            if entity_type == "DRUG_VAGUE":
                reasons.append("اسم الدواء العلمي غير محدد — يتطلب توضيح المريض/الأسرة")
            if entity_type == "DRUG_GENERIC" and surface_text.lower() in self.lexicon["generic_truncated"]:
                reasons.append("اسم مختصر يحتمل الالتباس مع أدوية مشابهة (LASA)")
            if negated:
                reasons.append("صيغة نفي محتملة في الجملة — تحقق قبل الاعتماد")
                confidence = "Low"

            ambiguous_flag = len(abbrev_hits) > 0
            if ambiguous_flag:
                abbr_names = ", ".join(h["abbreviation"] for h in abbrev_hits)
                reasons.append(f"اختصار عالي الخطورة موجود في الجملة: {abbr_names}")

            rec.confidence = confidence
            rec.ambiguous_abbreviation_flag = ambiguous_flag
            rec.needs_human_review = bool(
                reasons or confidence == "Low" or entity_type == "DRUG_VAGUE"
            )
            rec.review_reason = "؛ ".join(reasons) if reasons else ""

            records.append(rec)

        return records


def write_csv(records: List[MedicationRecord], out_path: Path):
    if not records:
        print("No medication mentions extracted — nothing written.", file=sys.stderr)
        return
    fieldnames = list(records[0].to_dict().keys())
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_dict())
    print(f"Wrote {len(records)} record(s) to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Rule-based medication extractor (draft-only, requires human review).")
    parser.add_argument("text", nargs="?", help="Raw clinical text / patient statement")
    parser.add_argument("--file", help="Path to a text file, one note per line")
    parser.add_argument("--note-id", default="N000")
    parser.add_argument("--source", default="chart", choices=["patient", "family", "chart", "inferred"])
    parser.add_argument("--out", default="output.csv", help="Output CSV path")
    args = parser.parse_args()

    extractor = MedicationExtractor()
    all_records: List[MedicationRecord] = []

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                nid = f"{args.note_id}_{i}"
                all_records.extend(extractor.extract(line, note_id=nid, assertion_source=args.source))
    elif args.text:
        all_records.extend(extractor.extract(args.text, note_id=args.note_id, assertion_source=args.source))
    else:
        parser.error("Provide either raw text or --file")

    write_csv(all_records, Path(args.out))

    flagged = [r for r in all_records if r.needs_human_review]
    if flagged:
        print(f"\n⚠️  {len(flagged)}/{len(all_records)} record(s) flagged for mandatory human review.")


if __name__ == "__main__":
    main()
