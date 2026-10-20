# MedRec AI Lab — مختبر مطابقة الأدوية بالذكاء الاصطناعي

An interactive teaching simulator for clinical pharmacy students and fresh
graduates. It walks through AI-assisted medication reconciliation in five
stages, with mandatory clinical pharmacist verification at the end.

Open `index.html` in any browser — no installation, no server, no data leaves
the device. Progress is saved only in the viewer's own browser.

## Workflow

| Stage | What the learner does |
|---|---|
| 1. Case & sources | Runs a simulated NLP + CNN pipeline over three sources: the patient interview (NLP entity tagging), medication label photos (CNN + OCR with field-level confidence), and the community pharmacy dispensing record. |
| 2. AI BPMH by confidence | Reviews the Best Possible Medication History ranked by fused confidence: High ≥ 0.90, Moderate 0.70–0.89, Low < 0.70 (mandatory verification). |
| 3. Compare with EHR | Classifies each BPMH–EHR pair (no discrepancy / intentional documented / undocumented / unintentional) and checks the model answer. |
| 4. Guideline check | Reviews the regimen against current guidelines for the patient's diseases and labs, ranked by severity. |
| 5. Pharmacist verification | Records a verification method and outcome for every flagged item, signs off, and generates a reconciled record. Student/intern records require a licensed clinical pharmacist co-signature. |

## Confidence model

```
fused = Σ(wᵢ · sᵢ) / Σwᵢ   over available sources
w(NLP) = 0.35, w(CNN/OCR) = 0.45, w(refill record) = 0.20
single source        → × 0.90
conflicting sources  → − 0.18
```

## Cases (fictional)

- **Case A** — 72 M, acute decompensated HFrEF with T2DM and CKD (eGFR 28, K⁺ 5.3).
  Teaches dose transcription error, commission of a stopped drug, OTC NSAID
  capture, metformin in CKD, missing SGLT2 inhibitor.
- **Case B** — 66 F, COPD exacerbation on warfarin with INR 3.4.
  Teaches weekly warfarin schedules, CNN second-best OCR readings
  (levothyroxine 75 vs 50 mcg), herbal (St John's wort) capture,
  warfarin–clarithromycin interaction, DOAC preference in non-valvular AF.

- **Case C: Build your own case.** An empty template. Students enter a fictional
  patient (labs, diagnoses, allergies), an interview transcript (English, Arabic
  or mixed), label text with a label-quality setting, refill records and EHR
  orders with chart notes. A rule-based NLP engine (drug lexicon with brand,
  Arabic and lay terms such as "water pill" or "حبة الضغط") and a simulated CNN
  build the BPMH. The EHR comparison and a rule engine of about 25 guideline
  checks run on the student's own data. Students can add medicines the AI
  missed and their own guideline findings. Cases can be copied as JSON and
  imported, so an instructor can hand out or collect cases. A "Load example"
  button fills in a worked CKD/AF/T2DM case.

## Relation to the rest of this repository

The simulator's NLP stage illustrates the same principles as the annotation
schema in `data/` and the rule-based extractor in `src/`: vague terms
("water pill", "purple inhaler") are mapped with lower confidence, nothing
missing is silently inferred, and every low-confidence item goes to human review.

## Important

- Teaching simulation only. Model outputs are pre-scripted; no real model runs.
- All patients are fictional. Never add real patient data to this folder.
- Guideline references are named for study (2022 AHA/ACC/HFSA HF, ADA Standards
  of Care, KDIGO, AGS Beers 2023, GOLD 2025, 2023 ACC/AHA/ACCP/HRS AF).
  Confirm thresholds against the edition in force and the hospital formulary.

Author: Dr. Sara Essam Bauomy Ibrahim — Clinical Pharmacy, Al-Rayan National Colleges
