---
title: Medical PA Environment
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
---

# Medical Prior Authorization Environment

A realistic OpenEnv environment simulating insurance prior authorization (PA) review — one of the most expensive administrative processes in US healthcare ($50B+ annual burden). An AI agent reviews medical procedure requests against clinical guidelines and makes coverage decisions.

## Why This Matters

Prior authorization is the process where a doctor submits a request to an insurance company before performing a procedure. A human reviewer checks the request against clinical guidelines and either approves, denies, or asks for more information. This happens millions of times per day and is a notorious bottleneck in healthcare delivery. It's a perfect agent task: rule-followable, but complex enough to challenge frontier models.

## Environment Overview

### Observation Space

The agent observes a structured PA request containing:

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | `str` | Unique PA request identifier |
| `patient_age` | `int` | Patient age in years |
| `patient_gender` | `str` | Patient gender |
| `plan_id` | `str` | Insurance plan identifier |
| `diagnosis_codes` | `list[str]` | ICD-10 diagnosis codes |
| `procedure_code` | `str` | CPT procedure code |
| `clinical_notes` | `str` | Free-text clinical notes (may contain buried findings) |
| `prior_treatments` | `list[str]` | Prior treatment history |
| `attachments` | `list[str]` | Documents attached to the request |
| `guideline_result` | `str \| None` | Result of last guideline lookup |
| `formulary_result` | `str \| None` | Result of last formulary check |
| `patient_history_result` | `str \| None` | Result of patient history retrieval |
| `info_request_result` | `str \| None` | Result of requesting additional info |
| `step_number` | `int` | Current step (max 8) |
| `message` | `str` | Status message |
| `reward_breakdown` | `dict \| None` | Per-component scores (terminal only) |

### Action Space

| Action | Payload | Description |
|--------|---------|-------------|
| `approve` | `{}` | Approve the PA request (requires rationale) |
| `deny` | `{"reason_code": "CODE"}` | Deny with a reason code (requires rationale) |
| `request_info` | `{"fields": ["field1", ...]}` | Request additional documentation |
| `lookup_guideline` | `{"procedure": "CPT", "diagnosis": "ICD-10"}` | Look up clinical guidelines |
| `check_formulary` | `{"drug": "name"}` | Check drug formulary status |
| `get_patient_history` | `{}` | Retrieve patient treatment history |

### Denial Reason Codes

`CONTRAINDICATION_ACTIVE`, `CRITERIA_NOT_MET`, `MEDICAL_NECESSITY_NOT_ESTABLISHED`, `SAFETY_CONCERN`, `STEP_THERAPY_NOT_COMPLETED`

## Tasks

### Task 1: Knee MRI for ACL Injury (Easy)
- **Scenario**: 32yo male, acute ACL tear with positive Lachman test. All docs present.
- **Expected**: Look up guideline GL-ORTHO-001, approve with rationale citing criteria.
- **What makes it easy**: All criteria clearly met, no missing docs, no ambiguity.
- **Max reward**: 1.0

### Task 2: Humira for Crohn's Disease (Medium)
- **Scenario**: 28yo female with moderate-to-severe Crohn's, requesting Humira. Step therapy documentation is missing — clinical notes mention 2 failed therapies but formal records are absent.
- **Expected**: Look up guideline GL-GI-002, identify missing step therapy documentation, request it, then approve after receiving it.
- **What makes it hard**: Must identify *exactly* which docs are missing, request them, and only decide after receiving them. Ambiguity around whether methotrexate was formally trialed.
- **Max reward**: 1.0 (0.4 for correct pend + right fields; 1.0 for final correct decision)

### Task 3: Spinal Fusion — Complex Denial (Hard)
- **Scenario**: 56yo female with degenerative disc disease requesting spinal fusion. Most criteria met, but a contraindication (HbA1c 8.4% — uncontrolled diabetes) is buried mid-paragraph in a 400-word clinical note. Two applicable guidelines (GL-SPINE-003 vs GL-SPINE-004) give conflicting requirements.
- **Expected**: Find the buried contraindication, correctly select GL-SPINE-003 over GL-SPINE-004 based on plan type, issue denial with code `CONTRAINDICATION_ACTIVE` and detailed rationale.
- **What makes it genuinely hard**: Contraindication buried in text, conflicting guidelines, multiple plausible-but-wrong denial codes, and most other criteria ARE met.
- **Max reward**: 1.0 (0.3 for finding contraindication; 0.7 for correct denial; 1.0 for full rationale)

## Reward Function

| Component | Weight | Description |
|-----------|--------|-------------|
| Decision correctness | 0.5 | Right approve/deny/pend decision |
| Rationale quality | 0.2 | References correct guideline ID and key findings |
| Info gathering quality | 0.2 | Consulted guidelines, requested correct missing docs |
| Efficiency | 0.1 | Fewer steps = higher score |
| Hallucinated guideline | -0.3 | Penalty for citing fake guidelines |
| Repeated actions | -0.05/ea | Penalty for repeating identical actions |

## Setup & Usage

### Prerequisites
- Python 3.10+
- Docker (for containerized deployment)

### Install
```bash
pip install -e .
```

### Run locally
```bash
# Start the environment server
uvicorn medical_pa_env.server.app:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t medical-pa-env .
docker run -p 8000:8000 medical-pa-env
```

### Run inference
```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export IMAGE_NAME=medical-pa-env

python inference.py
```

### Client usage
```python
import asyncio
from medical_pa_env import MedicalPAAction, MedicalPAEnv

async def main():
    async with MedicalPAEnv(base_url="http://localhost:8000") as client:
        result = await client.reset(task_id="easy_knee_mri")
        print(result.observation.clinical_notes)

        # Look up guideline
        result = await client.step(MedicalPAAction(
            action_type="lookup_guideline",
            payload={"procedure": "73721", "diagnosis": "S83.511A"},
        ))
        print(result.observation.guideline_result)

        # Approve
        result = await client.step(MedicalPAAction(
            action_type="approve",
            payload={},
            rationale="Criteria GL-ORTHO-001 met: positive Lachman test, acute ACL injury.",
        ))
        print(f"Score: {result.reward}")

asyncio.run(main())
```

## Baseline Scores (Expected)

| Task | Expected Score | Notes |
|------|---------------|-------|
| easy_knee_mri | 0.75–0.90 | Most models get this right |
| medium_humira_crohns | 0.50–0.70 | Requires multi-step reasoning |
| hard_spinal_fusion | 0.30–0.55 | Frontier models struggle with buried contraindication |

## Architecture

```
medical_pa_env/
├── __init__.py              # Exports: MedicalPAAction, MedicalPAObservation, MedicalPAEnv
├── models.py                # Pydantic models for Action & Observation
├── client.py                # EnvClient implementation
├── tasks.py                 # Clinical guidelines DB + 3 task definitions
├── grader.py                # Deterministic graders (0.0–1.0)
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Package config
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI app via create_app()
    ├── medical_pa_environment.py  # Environment(step/reset/state)
    ├── Dockerfile
    └── requirements.txt
```

## License

MIT
