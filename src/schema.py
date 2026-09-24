"""
schema.py

Defines the structured record produced by the extractor, matching the
annotation schema in data/medication_nlp_annotation_schema.csv.

Core design rule (do not violate): any field not explicitly found in the
source text must be set to "NOT_STATED" — never inferred, never guessed.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

NOT_STATED = "NOT_STATED"


@dataclass
class MedicationRecord:
    note_id: str
    annotator_id: str = "AUTO_EXTRACTOR"

    entity_text: str = NOT_STATED
    entity_type: str = NOT_STATED          # DRUG_GENERIC | DRUG_BRAND | DRUG_VAGUE
    normalized_code: Optional[str] = None  # RxNorm/SNOMED if resolvable, else None

    dose_value: str = NOT_STATED
    dose_unit: str = NOT_STATED
    route: str = NOT_STATED
    frequency: str = NOT_STATED

    status: str = "unknown"                # active | stopped | PRN | held | new | unknown
    temporality: str = "current"           # current | historical | planned
    negation: bool = False
    assertion_source: str = "chart"        # patient | family | chart | inferred

    confidence: str = "Low"                # High | Medium | Low
    needs_human_review: bool = True
    review_reason: str = ""
    ambiguous_abbreviation_flag: bool = False

    source_sentence: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["normalized_code"] = d["normalized_code"] or ""
        return d
