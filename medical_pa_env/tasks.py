"""
Clinical guidelines database and task definitions for the Medical PA environment.

Contains fictional but plausible clinical guidelines, task scenarios,
and grading logic for the 3 prior authorization tasks.
"""

from typing import Any, Dict, List, Optional


# =============================================================================
# Clinical Guidelines Database
# =============================================================================

GUIDELINES: Dict[str, Dict[str, Any]] = {
    "GL-ORTHO-001": {
        "id": "GL-ORTHO-001",
        "title": "MRI of the Knee for Suspected Ligament Injury",
        "procedure_codes": ["73721", "73722"],
        "diagnosis_codes": ["S83.511A", "S83.512A", "M23.611", "M23.612"],
        "criteria": [
            "Documented physical examination findings consistent with ligament injury",
            "Failed conservative treatment of at least 4 weeks OR acute traumatic injury",
            "Clinical notes referencing positive Lachman test, pivot shift, or MRI indication",
        ],
        "required_documents": ["clinical_notes", "physical_exam_report"],
        "decision_if_met": "approve",
        "step_therapy_required": False,
        "notes": "Approval is straightforward when clinical exam documents ACL injury with positive Lachman test.",
    },
    "GL-GI-002": {
        "id": "GL-GI-002",
        "title": "Adalimumab (Humira) for Crohn's Disease",
        "procedure_codes": ["J0135"],
        "diagnosis_codes": ["K50.00", "K50.10", "K50.80", "K50.90"],
        "criteria": [
            "Confirmed diagnosis of moderate-to-severe Crohn's disease",
            "Documented failure of at least 2 conventional therapies (e.g., mesalamine, corticosteroids, azathioprine, methotrexate)",
            "Step therapy: must show trial and failure of at least 2 prior biologic or conventional agents",
            "No active untreated infections (TB screening required)",
        ],
        "required_documents": [
            "clinical_notes",
            "prior_treatment_records",
            "tb_screening_results",
            "step_therapy_documentation",
        ],
        "decision_if_met": "approve",
        "step_therapy_required": True,
        "notes": "Requires documented failure of 2 conventional therapies before biologic approval.",
    },
    "GL-SPINE-003": {
        "id": "GL-SPINE-003",
        "title": "Lumbar Spinal Fusion for Degenerative Disc Disease",
        "procedure_codes": ["22612", "22630", "22633"],
        "diagnosis_codes": ["M51.16", "M51.17", "M47.816", "M47.817"],
        "criteria": [
            "Documented degenerative disc disease at 1-2 levels on imaging",
            "Failed conservative treatment for minimum 6 months including physical therapy and pain management",
            "Psychological evaluation completed if chronic pain >12 months",
            "No active contraindications: uncontrolled diabetes (HbA1c > 8.0), active smoking without cessation program, BMI > 40 without documented weight management",
            "Concordant findings between imaging and clinical symptoms",
        ],
        "required_documents": [
            "clinical_notes",
            "imaging_reports",
            "physical_therapy_records",
            "pain_management_records",
            "psychological_evaluation",
        ],
        "decision_if_met": "approve",
        "step_therapy_required": True,
        "notes": "Complex case. Multiple criteria must be met. Contraindications in clinical notes must be identified.",
    },
    "GL-SPINE-004": {
        "id": "GL-SPINE-004",
        "title": "Lumbar Spinal Fusion — Alternative Criteria (Network B)",
        "procedure_codes": ["22612", "22630", "22633"],
        "diagnosis_codes": ["M51.16", "M51.17", "M47.816", "M47.817"],
        "criteria": [
            "Documented degenerative disc disease at 1-2 levels on imaging",
            "Failed conservative treatment for minimum 3 months including physical therapy",
            "No active contraindications to surgery",
            "BMI < 35",
        ],
        "required_documents": [
            "clinical_notes",
            "imaging_reports",
            "physical_therapy_records",
        ],
        "decision_if_met": "approve",
        "step_therapy_required": False,
        "notes": "Network B has shorter conservative treatment requirement but stricter BMI cutoff.",
    },
}

# =============================================================================
# Formulary Database
# =============================================================================

FORMULARY: Dict[str, Dict[str, Any]] = {
    "adalimumab": {
        "brand_name": "Humira",
        "generic_name": "adalimumab",
        "tier": 4,
        "requires_pa": True,
        "step_therapy": ["mesalamine", "azathioprine"],
        "status": "covered_with_pa",
    },
    "infliximab": {
        "brand_name": "Remicade",
        "generic_name": "infliximab",
        "tier": 4,
        "requires_pa": True,
        "step_therapy": ["mesalamine", "azathioprine"],
        "status": "covered_with_pa",
    },
    "mesalamine": {
        "brand_name": "Asacol",
        "generic_name": "mesalamine",
        "tier": 2,
        "requires_pa": False,
        "step_therapy": [],
        "status": "covered",
    },
}

# =============================================================================
# Task Definitions
# =============================================================================


def get_task_easy() -> Dict[str, Any]:
    """Task 1 (Easy): Knee MRI for documented ACL injury.

    All documentation is present. Clear approval criteria are met.
    Agent just needs to look up guideline + approve with correct rationale.
    """
    return {
        "task_id": "easy_knee_mri",
        "task_name": "Knee MRI — ACL Injury (Easy)",
        "difficulty": "easy",
        "request": {
            "request_id": "PA-2024-00147",
            "patient_age": 32,
            "patient_gender": "male",
            "plan_id": "PLAN-PPO-5000",
            "diagnosis_codes": ["S83.511A"],
            "procedure_code": "73721",
            "clinical_notes": (
                "32-year-old male presents after acute sports injury during basketball game 3 days ago. "
                "Patient reports hearing a 'pop' in the left knee followed by immediate swelling and instability. "
                "Physical examination reveals positive Lachman test (Grade 2), positive anterior drawer sign, "
                "and moderate joint effusion. Range of motion limited to 10-90 degrees due to pain and swelling. "
                "McMurray test equivocal. No distal neurovascular deficit. "
                "Assessment: Suspected complete ACL tear, left knee. "
                "Plan: MRI of left knee to confirm diagnosis and evaluate meniscal pathology before surgical consultation. "
                "Criterion GL-ORTHO-001 applies: acute traumatic injury with positive Lachman test."
            ),
            "prior_treatments": [],
            "attachments": ["clinical_notes", "physical_exam_report"],
        },
        "ground_truth": {
            "correct_decision": "approve",
            "applicable_guideline": "GL-ORTHO-001",
            "required_criteria_ids": [
                "Documented physical examination findings consistent with ligament injury",
                "Failed conservative treatment of at least 4 weeks OR acute traumatic injury",
                "Clinical notes referencing positive Lachman test, pivot shift, or MRI indication",
            ],
            "missing_fields": [],
            "correct_denial_code": None,
            "key_findings": [
                "positive Lachman test",
                "acute traumatic injury",
                "ACL tear",
            ],
        },
        "patient_history": {
            "history": "No prior orthopedic procedures. No chronic conditions. Active lifestyle.",
            "prior_auths": [],
        },
    }


def get_task_medium() -> Dict[str, Any]:
    """Task 2 (Medium): Humira for Crohn's Disease — missing step therapy docs.

    Patient has Crohn's, requesting Humira. Clinical notes mention prior treatment
    with mesalamine (failed) but step therapy documentation for the second failed
    conventional therapy is missing. Agent must identify missing docs, request them,
    then make decision after receiving them.
    """
    return {
        "task_id": "medium_humira_crohns",
        "task_name": "Humira for Crohn's Disease (Medium)",
        "difficulty": "medium",
        "request": {
            "request_id": "PA-2024-00283",
            "patient_age": 28,
            "patient_gender": "female",
            "plan_id": "PLAN-HMO-3000",
            "diagnosis_codes": ["K50.10"],
            "procedure_code": "J0135",
            "clinical_notes": (
                "28-year-old female with moderate-to-severe Crohn's disease (ileal involvement) diagnosed 3 years ago. "
                "Disease activity confirmed by colonoscopy showing deep ulcerations and elevated CRP (28 mg/L) and ESR (42 mm/hr). "
                "Harvey-Bradshaw Index score of 11 (moderate-to-severe). "
                "Treatment history: Patient was started on mesalamine 4.8g/day in 2022, which provided minimal improvement "
                "over 4 months. She was then transitioned to azathioprine 150mg/day but developed significant leukopenia "
                "(WBC 2.1) after 8 weeks, requiring discontinuation. "
                "A trial of methotrexate was discussed but the patient reports she 'couldn't tolerate the injections' — "
                "unclear if this constitutes a documented therapeutic failure or was never formally initiated. "
                "TB screening: QuantiFERON-TB Gold negative (dated 2024-01-15). "
                "No active infections. Hepatitis B surface antigen negative. "
                "Requesting adalimumab (Humira) 160mg induction followed by 80mg at week 2, then 40mg every other week. "
                "Guideline GL-GI-002 requires documented failure of at least 2 conventional therapies."
            ),
            "prior_treatments": [
                "mesalamine 4.8g/day — 4 months, minimal improvement",
                "azathioprine 150mg/day — 8 weeks, discontinued due to leukopenia",
            ],
            "attachments": ["clinical_notes", "tb_screening_results"],
        },
        "ground_truth": {
            "correct_decision": "request_info",
            "applicable_guideline": "GL-GI-002",
            "required_criteria_ids": [
                "Confirmed diagnosis of moderate-to-severe Crohn's disease",
                "Documented failure of at least 2 conventional therapies (e.g., mesalamine, corticosteroids, azathioprine, methotrexate)",
                "Step therapy: must show trial and failure of at least 2 prior biologic or conventional agents",
                "No active untreated infections (TB screening required)",
            ],
            "missing_fields": [
                "step_therapy_documentation",
                "prior_treatment_records",
            ],
            "correct_denial_code": None,
            "key_findings": [
                "mesalamine failed",
                "azathioprine discontinued due to leukopenia",
                "methotrexate unclear if formally trialed",
                "step therapy documentation missing",
            ],
            "post_info_decision": "approve",
            "post_info_rationale": (
                "After receiving step therapy documentation confirming azathioprine failure "
                "qualifies as second conventional therapy failure (adverse event is valid failure), "
                "criteria GL-GI-002 are met. Approve."
            ),
        },
        "patient_history": {
            "history": (
                "Diagnosed with Crohn's disease in 2021. Multiple ER visits for flares. "
                "Failed mesalamine (2022), azathioprine discontinued for leukopenia (2023). "
                "Methotrexate was prescribed but patient reports intolerance — records show "
                "a single injection was attempted with severe nausea, no further doses given."
            ),
            "prior_auths": [
                "PA-2022-01045: mesalamine — approved",
                "PA-2023-00512: azathioprine — approved",
            ],
        },
        "supplemental_info": {
            "step_therapy_documentation": (
                "Step therapy documentation received: "
                "1) Mesalamine 4.8g/day for 4 months — documented inadequate response (CDAI remained >300). "
                "2) Azathioprine 150mg/day for 8 weeks — discontinued due to severe leukopenia (WBC 2.1 × 10^9/L). "
                "Per policy, adverse event requiring discontinuation qualifies as therapeutic failure. "
                "Two conventional therapy failures confirmed."
            ),
            "prior_treatment_records": (
                "Prior treatment records confirm: mesalamine trial from March 2022 to July 2022. "
                "Azathioprine trial from January 2023 to March 2023. "
                "Both documented in electronic medical records with provider attestation."
            ),
        },
    }


def get_task_hard() -> Dict[str, Any]:
    """Task 3 (Hard): Spinal fusion with buried contraindication and conflicting guidelines.

    Complex case: Patient has degenerative disc disease requesting spinal fusion.
    Some criteria met. However, a contraindication (uncontrolled diabetes, HbA1c 8.4)
    is buried in the clinical notes. Two applicable guidelines (GL-SPINE-003 and
    GL-SPINE-004) give different requirements. Agent must find the contraindication,
    resolve the conflict, and correctly deny.
    """
    return {
        "task_id": "hard_spinal_fusion",
        "task_name": "Spinal Fusion — Complex Denial (Hard)",
        "difficulty": "hard",
        "request": {
            "request_id": "PA-2024-00519",
            "patient_age": 56,
            "patient_gender": "female",
            "plan_id": "PLAN-PPO-7500",
            "diagnosis_codes": ["M51.16", "M47.816"],
            "procedure_code": "22633",
            "clinical_notes": (
                "56-year-old female with longstanding lower back pain and bilateral radiculopathy. "
                "MRI lumbar spine (2024-02-10) demonstrates grade 2 spondylolisthesis at L4-L5 with "
                "moderate central canal stenosis and bilateral foraminal narrowing. Degenerative disc disease "
                "at L4-L5 and L5-S1 with disc desiccation and loss of disc height. "
                "Conservative treatment history: Physical therapy 3x/week for 8 months (completed). "
                "Epidural steroid injections x3 (last one 2024-01-05 with minimal relief lasting <2 weeks). "
                "NSAID therapy (meloxicam 15mg daily) ongoing. Gabapentin 300mg TID for neuropathic pain. "
                "Pain management program completed December 2023. "
                "\n"
                "Comorbidities: Type 2 diabetes mellitus — last HbA1c 8.4% (drawn 2024-03-01), up from 7.9% "
                "six months ago. Patient reports difficulty with medication compliance. Endocrinologist consulted "
                "but no formal glycemic optimization plan documented. BMI 33.2. Former smoker, quit 2019. "
                "History of depression, currently managed with sertraline 100mg daily. "
                "\n"
                "Psychological evaluation completed 2024-02-20 by Dr. Martinez — patient cleared for surgery "
                "with recommendation for continued mental health support post-operatively. "
                "\n"
                "Surgical plan: L4-L5 posterior lumbar interbody fusion (PLIF) with instrumentation. "
                "Dr. Ramirez (orthopedic spine surgeon) notes that patient's symptoms are concordant with "
                "imaging findings and conservative measures have been exhausted. "
                "\n"
                "Additional note from primary care (Dr. Chen, 2024-03-05): Patient's diabetes remains "
                "suboptimally controlled. Recommended referral to diabetes education program. HbA1c target "
                "for surgical clearance per institutional protocol is <8.0%. Current level of 8.4% represents "
                "a surgical risk factor. Dr. Chen did not provide surgical clearance pending glycemic improvement."
            ),
            "prior_treatments": [
                "Physical therapy — 8 months, 3x/week",
                "Epidural steroid injections x3 — last 2024-01-05, minimal relief",
                "Meloxicam 15mg daily — ongoing, partial relief",
                "Gabapentin 300mg TID — ongoing, moderate neuropathic pain control",
                "Pain management program — completed December 2023",
            ],
            "attachments": [
                "clinical_notes",
                "imaging_reports",
                "physical_therapy_records",
                "pain_management_records",
                "psychological_evaluation",
            ],
        },
        "ground_truth": {
            "correct_decision": "deny",
            "applicable_guideline": "GL-SPINE-003",
            "conflicting_guideline": "GL-SPINE-004",
            "required_criteria_ids": [
                "Documented degenerative disc disease at 1-2 levels on imaging",
                "Failed conservative treatment for minimum 6 months including physical therapy and pain management",
                "Psychological evaluation completed if chronic pain >12 months",
                "No active contraindications: uncontrolled diabetes (HbA1c > 8.0), active smoking without cessation program, BMI > 40 without documented weight management",
                "Concordant findings between imaging and clinical symptoms",
            ],
            "missing_fields": [],
            "correct_denial_code": "CONTRAINDICATION_ACTIVE",
            "alternative_denial_codes": [
                "CRITERIA_NOT_MET",
                "MEDICAL_NECESSITY_NOT_ESTABLISHED",
                "SAFETY_CONCERN",
            ],
            "key_findings": [
                "HbA1c 8.4% exceeds 8.0% threshold — uncontrolled diabetes",
                "Primary care did not provide surgical clearance",
                "GL-SPINE-003 requires HbA1c ≤ 8.0",
                "GL-SPINE-004 has stricter BMI cutoff (35 vs 40) but patient BMI 33.2 would pass",
                "GL-SPINE-003 applies — plan is PPO network, not Network B",
                "Conservative treatment met (8 months PT + pain management)",
                "Psychological eval completed",
                "Imaging concordant with symptoms",
            ],
            "contraindication": {
                "type": "uncontrolled_diabetes",
                "detail": "HbA1c 8.4% > 8.0% threshold",
                "location_hint": "buried in comorbidities paragraph and primary care note",
            },
        },
        "patient_history": {
            "history": (
                "Chronic low back pain for 5+ years. Multiple conservative treatment attempts. "
                "Type 2 diabetes since 2018, historically borderline controlled. "
                "Prior orthopedic procedures: left knee arthroscopy 2020. "
                "No prior spinal surgeries."
            ),
            "prior_auths": [
                "PA-2023-00210: epidural steroid injection series — approved",
                "PA-2023-00456: lumbar MRI — approved",
            ],
        },
    }


ALL_TASKS = {
    "easy_knee_mri": get_task_easy,
    "medium_humira_crohns": get_task_medium,
    "hard_spinal_fusion": get_task_hard,
}


def get_task(task_id: str) -> Dict[str, Any]:
    """Retrieve a task by ID."""
    if task_id not in ALL_TASKS:
        raise ValueError(f"Unknown task_id: {task_id}. Available: {list(ALL_TASKS.keys())}")
    return ALL_TASKS[task_id]()
