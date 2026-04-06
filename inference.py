"""
Inference Script for Medical Prior Authorization Environment
=============================================================
Runs a baseline LLM agent against all 3 PA review tasks.

Environment Variables:
    API_BASE_URL      - LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME        - Model identifier (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN          - Hugging Face API key (NO default, optional)
    LOCAL_IMAGE_NAME  - Docker image name for the environment

STDOUT format:
    [START] task=<task_name> env=medical_pa_env model=<model_name>
    [RESET] task=<task_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import asyncio
import json
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from medical_pa_env import MedicalPAAction, MedicalPAEnv

LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
HF_TOKEN = os.getenv("HF_TOKEN")  # No default — optional
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
BENCHMARK = "medical_pa_env"
MAX_STEPS = 8
TEMPERATURE = 0.3
MAX_TOKENS = 1024

TASKS = [
    "easy_knee_mri",
    "medium_humira_crohns",
    "hard_spinal_fusion",
]

SYSTEM_PROMPT = textwrap.dedent("""\
You are an insurance prior authorization reviewer AI. You review medical procedure
requests against clinical guidelines and make coverage decisions.

For each case you receive:
- Patient demographics, diagnosis codes (ICD-10), procedure code (CPT)
- Clinical notes from the provider
- Prior treatment history
- Attached documentation

Available actions (respond with EXACTLY ONE JSON object per turn):
1. {"action_type": "lookup_guideline", "payload": {"procedure": "<CPT>", "diagnosis": "<ICD-10>"}, "rationale": null}
2. {"action_type": "get_patient_history", "payload": {}, "rationale": null}
3. {"action_type": "check_formulary", "payload": {"drug": "<drug_name>"}, "rationale": null}
4. {"action_type": "request_info", "payload": {"fields": ["field1", "field2"]}, "rationale": "reason for request"}
5. {"action_type": "approve", "payload": {}, "rationale": "detailed rationale citing guideline ID and criteria met"}
6. {"action_type": "deny", "payload": {"reason_code": "CODE"}, "rationale": "detailed rationale citing guideline ID and unmet criteria"}

Valid denial reason codes: CONTRAINDICATION_ACTIVE, CRITERIA_NOT_MET, MEDICAL_NECESSITY_NOT_ESTABLISHED, SAFETY_CONCERN, STEP_THERAPY_NOT_COMPLETED

Strategy:
1. First, lookup the applicable guideline for the procedure/diagnosis
2. Check if required documentation is present
3. If docs are missing, request them
4. Review all evidence against guideline criteria
5. Make your decision with a detailed rationale citing the guideline ID

IMPORTANT: Respond with ONLY a valid JSON object. No extra text, no markdown, no explanation outside the JSON.
""")


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_reset(task: str) -> None:
    print(f"[RESET] task={task}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(observation: Any, step: int, history: List[str]) -> str:
    """Build user prompt from the observation."""
    parts = [
        f"=== PA Review Case: {observation.request_id} (Step {step}/{observation.max_steps}) ===",
        f"Patient: {observation.patient_age}yo {observation.patient_gender}, Plan: {observation.plan_id}",
        f"Diagnosis (ICD-10): {', '.join(observation.diagnosis_codes)}",
        f"Procedure (CPT): {observation.procedure_code}",
        f"\nClinical Notes:\n{observation.clinical_notes}",
        f"\nPrior Treatments: {'; '.join(observation.prior_treatments) if observation.prior_treatments else 'None'}",
        f"Attached Documents: {', '.join(observation.attachments) if observation.attachments else 'None'}",
    ]

    if observation.guideline_result:
        parts.append(f"\n--- Guideline Lookup Result ---\n{observation.guideline_result}")
    if observation.formulary_result:
        parts.append(f"\n--- Formulary Check Result ---\n{observation.formulary_result}")
    if observation.patient_history_result:
        parts.append(f"\n--- Patient History ---\n{observation.patient_history_result}")
    if observation.info_request_result:
        parts.append(f"\n--- Requested Information ---\n{observation.info_request_result}")

    parts.append(f"\nStatus: {observation.message}")

    if history:
        parts.append(f"\nPrevious actions this episode:")
        for h in history[-5:]:
            parts.append(f"  {h}")

    parts.append("\nRespond with ONE JSON action object:")

    return "\n".join(parts)


def parse_action_from_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON action from model response."""
    # Try to find JSON in the response
    # First try: the whole response is JSON
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code blocks
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def get_model_action(
    client: OpenAI,
    observation: Any,
    step: int,
    history: List[str],
) -> Dict[str, Any]:
    """Get action from the LLM."""
    user_prompt = build_user_prompt(observation, step, history)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        action_dict = parse_action_from_response(text)
        if action_dict and "action_type" in action_dict:
            return action_dict
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)

    # Fallback: approve with generic rationale
    return {
        "action_type": "approve",
        "payload": {},
        "rationale": "Unable to parse model response. Defaulting to approval.",
    }


async def run_task(client: OpenAI, env: MedicalPAEnv, task_id: str) -> float:
    """Run a single task and return the score."""
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset(task_id=task_id)
        log_reset(task=task_id)
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action_dict = get_model_action(client, obs, step, history)

            # Build the typed action
            action = MedicalPAAction(
                action_type=action_dict.get("action_type", "approve"),
                payload=action_dict.get("payload", {}),
                rationale=action_dict.get("rationale"),
            )

            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step

            action_str = f"{action.action_type}({json.dumps(action.payload)})"
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {action.action_type} -> reward={reward:.2f}")

            if done:
                break

        # Score is the final reward (grader returns 0.0-1.0)
        score = rewards[-1] if rewards else 0.0
        score = max(0.0, min(1.0, score))
        success = score >= 0.3

    except Exception as exc:
        print(f"[DEBUG] Task {task_id} error: {exc}", flush=True)
        rewards.append(0.0)
        steps_taken = max(steps_taken, 1)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    # Try Docker image first; fall back to localhost if unavailable
    env = None
    if LOCAL_IMAGE_NAME:
        try:
            env = await MedicalPAEnv.from_docker_image(LOCAL_IMAGE_NAME)
        except Exception as exc:
            print(f"[DEBUG] from_docker_image failed ({exc}), falling back to localhost", flush=True)
    if env is None:
        env = MedicalPAEnv(base_url=os.getenv("ENV_BASE_URL", "http://localhost:8000"))
        await env.connect()

    try:
        scores = {}
        for task_id in TASKS:
            score = await run_task(client, env, task_id)
            scores[task_id] = score

        print("\n=== Baseline Results ===", flush=True)
        for task_id, score in scores.items():
            print(f"  {task_id}: {score:.2f}", flush=True)
        avg = sum(scores.values()) / len(scores) if scores else 0.0
        print(f"  Average: {avg:.2f}", flush=True)

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
