"""
Basic tests using the real example sentences from this project's clinical
walkthrough (BPMH patient statement + admission reconciliation examples).

Run with: python -m pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractor import MedicationExtractor
from src.schema import NOT_STATED


def test_generic_drug_with_dose_and_frequency():
    ext = MedicationExtractor()
    records = ext.extract("Metformin 500 bid", note_id="T1", assertion_source="family")
    assert len(records) == 1
    rec = records[0]
    assert rec.entity_type == "DRUG_GENERIC"
    assert rec.dose_value == "500"
    # unit was never stated in the source -> must NOT be guessed
    assert rec.dose_unit == NOT_STATED
    assert rec.frequency == "twice daily"
    assert rec.needs_human_review is True  # missing dose unit triggers review


def test_vague_drug_flagged_for_review():
    ext = MedicationExtractor()
    records = ext.extract("آخذ حبة الضغط الصبح", note_id="T2", assertion_source="patient")
    assert len(records) == 1
    rec = records[0]
    assert rec.entity_type == "DRUG_VAGUE"
    assert rec.needs_human_review is True
    assert rec.confidence == "Low"


def test_truncated_drug_name_flagged_as_ambiguous():
    ext = MedicationExtractor()
    records = ext.extract("Atorva stopped ~1 month ago - muscle pain",
                           note_id="T3", assertion_source="family")
    assert len(records) == 1
    rec = records[0]
    assert rec.normalized_code == "atorvastatin"
    assert rec.status == "stopped"
    assert rec.needs_human_review is True


def test_no_recognized_drug_returns_empty():
    ext = MedicationExtractor()
    records = ext.extract("Patient reports feeling generally well today.", note_id="T4")
    assert records == []


def test_high_risk_abbreviation_flagged():
    ext = MedicationExtractor()
    records = ext.extract("lisinopril 10mg od", note_id="T5", assertion_source="family")
    assert len(records) == 1
    rec = records[0]
    assert rec.ambiguous_abbreviation_flag is True


if __name__ == "__main__":
    test_generic_drug_with_dose_and_frequency()
    test_vague_drug_flagged_for_review()
    test_truncated_drug_name_flagged_as_ambiguous()
    test_no_recognized_drug_returns_empty()
    test_high_risk_abbreviation_flagged()
    print("All tests passed.")
