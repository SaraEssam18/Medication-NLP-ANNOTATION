# Medication NLP Annotation Schema

A clinical annotation schema and reference dataset for building a hospital-specific
NLP system to extract medications (generic name, dose, route, frequency, status)
from unstructured clinical notes — including Arabic dialect and mixed
Arabic/English documentation.

## Why this exists

Off-the-shelf medical NLP tools (e.g. cTAKES, generic RxNorm matchers) are built
primarily for structured English clinical text. They struggle with:

- Local/dialect Arabic phrasing (e.g. "حبة الضغط", "إبرة الليل")
- Vague drug references that need human clarification before use
- Error-prone abbreviations (ISMP "Do Not Use" list)
- Missing dose units that must never be silently assumed

This repo provides the **annotation schema** and **high-risk abbreviation
reference** needed to build and train such a system safely — with an explicit
"never guess" policy baked into the schema itself.

## Contents

```
data/
  medication_nlp_annotation_schema.csv     # Annotation template + worked examples
  high_risk_abbreviations_reference.csv    # ISMP-style abbreviation risk list

config/
  drug_lexicon.json                        # Generic/brand/vague term dictionary (extend this)
  high_risk_abbreviations_reference.csv    # Same list, loaded at runtime by the extractor

src/
  schema.py                                # MedicationRecord dataclass matching the CSV schema
  extractor.py                             # Rule-based extraction engine + CLI

tests/
  test_extractor.py                        # Tests using this project's real worked examples

requirements.txt
```

## Running the extractor

The extractor is dependency-free (standard library only); `pytest` is only
needed to run the test suite.

```bash
pip install -r requirements.txt   # only needed for tests

# Single note from the command line
python -m src.extractor "lisinopril 10mg od" --note-id N001 --source family --out output.csv

# Batch mode: one note per line in a text file
python -m src.extractor --file notes.txt --note-id N001 --out output.csv

# Run the test suite
python -m pytest tests/ -v
```

Output is a CSV matching the columns in
`data/medication_nlp_annotation_schema.csv`, so extractor output and
human-annotated gold-standard data stay directly comparable — useful later
for measuring the rule-based system against real annotations, or as
weak-labeled training data for a fine-tuned model.

### What the extractor currently does

- Matches known generic names, brand names, truncated/ambiguous names
  (e.g. "Atorva"), and vague references (e.g. "حبة الضغط") from
  `config/drug_lexicon.json` — **extend this file** with your hospital's
  real drug list and local shorthand.
- Extracts dose value/unit, route, and frequency only when explicitly
  present in the text; everything else is `NOT_STATED`.
- Flags any high-risk abbreviation from `config/high_risk_abbreviations_reference.csv`.
- Auto-sets `needs_human_review = True` for vague drug names, missing dose
  units, negation phrases, or any detected high-risk abbreviation.

### What it is *not*

This is a **rule-based, dictionary-driven prototype** — a starting point,
not a trained NER model. It will miss any drug name or phrasing not in
`drug_lexicon.json`. See "Suggested next steps" below for moving to a
fine-tuned model once annotated data is available.

### `medication_nlp_annotation_schema.csv`

Defines the entity types and attributes annotators must tag for every
medication mention in a clinical note:

| Field | Description |
|---|---|
| `entity_type` | `DRUG_GENERIC` / `DRUG_BRAND` / `DRUG_VAGUE` |
| `normalized_code` | RxNorm/SNOMED code if resolvable, else `NULL` |
| `dose_value`, `dose_unit`, `route`, `frequency` | Structured fields — use `NOT_STATED` if absent from source text, never inferred |
| `status` | `active` / `stopped` / `PRN` / `held` / `new` / `unknown` |
| `assertion_source` | `patient` / `family` / `chart` / `inferred` |
| `confidence` | `High` / `Medium` / `Low` |
| `needs_human_review` | Boolean — auto-true for `DRUG_VAGUE`, low confidence, or negation |
| `ambiguous_abbreviation_flag` | Boolean — true if a high-risk abbreviation was used |

Row 2 documents allowed values for each column. Rows `N001`–`N005` are worked
examples from real annotation sessions (metformin, an unnamed antihypertensive,
a brand-name analgesic, an unnamed insulin, and a truncated statin name).

### `high_risk_abbreviations_reference.csv`

A lookup table of abbreviations known to cause clinical errors (modeled on the
ISMP Do-Not-Use list), each with its risk description and safer alternative.
Intended to drive an automatic flagging layer in the NLP pipeline.

## Core design principle: never guess

Every field the schema defines follows one rule: **if it isn't explicitly
stated in the source text, it is marked `NOT_STATED` — never inferred, never
auto-filled.** Ambiguous drug names (`DRUG_VAGUE`) and low-confidence
extractions are automatically routed to human review rather than passed
through as fact. This mirrors safe clinical medication-reconciliation practice
and is meant to reduce, not introduce, dosing risk.

## Suggested next steps for building the full system

1. Collect a de-identified sample (300–500 notes) representative of your
   hospital's real documentation style, including dialect and shorthand.
2. Have two independent clinical annotators (pharmacist/nurse) label the
   sample using this schema; measure inter-annotator agreement (Cohen's Kappa)
   per field, prioritizing dose and status fields.
3. Fine-tune an Arabic-capable NER model (e.g. AraBERT/CAMeL-BERT) on the
   annotated data, layered with rule-based matching for local abbreviations.
4. Route every low-confidence or `DRUG_VAGUE` extraction to mandatory human
   review before any clinical use — never fully automate dosing decisions.
5. Re-audit a sample of live outputs monthly to catch model drift and new
   local shorthand.

## Data & privacy

This repository must **never** contain real, identifiable patient notes.
Only de-identified or synthetic examples belong here — see `.gitignore`,
which blocks common raw-data and credential paths by default. Any dataset
used to train a production model must be de-identified in line with your
institution's health data protection policy before it ever touches version
control.

## Disclaimer

This schema and any system built from it are **clinical decision-support
aids only**. They do not replace pharmacist or physician judgment, and no
extraction should be acted upon clinically without human verification —
particularly for dose, route, and status fields.

## License

Add a license appropriate for your institution (e.g. MIT for tooling, or an
internal/proprietary license if this will hold hospital-specific data or
IP). None is applied by default.
