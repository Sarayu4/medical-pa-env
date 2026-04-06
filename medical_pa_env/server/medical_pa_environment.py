"""
Medical Prior Authorization Environment Implementation.

A realistic environment simulating insurance prior authorization review.
The agent must review clinical documentation, look up guidelines, identify
missing information, and make approve/deny decisions on medical procedure requests.
"""

import copy
from typing import Any, Dict, List, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import MedicalPAAction, MedicalPAObservation
    from ..tasks import GUIDELINES, FORMULARY, get_task, ALL_TASKS
    from ..grader import grade_task
except ImportError:
    from models import MedicalPAAction, MedicalPAObservation
    from tasks import GUIDELINES, FORMULARY, get_task, ALL_TASKS
    from grader import grade_task


MAX_STEPS = 8


class MedicalPAEnvironment(Environment):
    """
    A medical prior authorization review environment.

    The agent acts as an insurance PA reviewer, examining clinical documentation,
    consulting guidelines, and making coverage decisions (approve/deny/request info).

    Each episode loads a PA request (task). The agent interacts via typed actions
    and receives structured observations with partial reward signals.

    Supports 3 tasks:
      - easy_knee_mri: straightforward approval
      - medium_humira_crohns: requires identifying missing docs
      - hard_spinal_fusion: complex denial with buried contraindication
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task_id: str = "easy_knee_mri"):
        """Initialize the environment with a specific task.

        Args:
            task_id: One of 'easy_knee_mri', 'medium_humira_crohns', 'hard_spinal_fusion'
        """
        super().__init__()
        self._task_id = task_id
        self._task: Optional[Dict[str, Any]] = None
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._actions_taken: List[Dict[str, Any]] = []
        self._done = False
        self._cumulative_reward = 0.0
        self._info_received = False
        self._last_action_result: Optional[str] = None
        self._guideline_result: Optional[str] = None
        self._formulary_result: Optional[str] = None
        self._patient_history_result: Optional[str] = None
        self._info_request_result: Optional[str] = None

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> MedicalPAObservation:
        """Reset the environment and load the PA request.

        Args:
            seed: unused
            episode_id: optional custom episode ID
            **kwargs: may contain 'task_id' to override the task

        Returns:
            Initial observation with PA request details
        """
        task_id = kwargs.get("task_id", self._task_id)
        if task_id and task_id in ALL_TASKS:
            self._task_id = task_id

        self._task = get_task(self._task_id)
        self._state = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )
        self._actions_taken = []
        self._done = False
        self._cumulative_reward = 0.0
        self._info_received = False
        self._last_action_result = None
        self._guideline_result = None
        self._formulary_result = None
        self._patient_history_result = None
        self._info_request_result = None

        req = self._task["request"]
        return MedicalPAObservation(
            request_id=req["request_id"],
            patient_age=req["patient_age"],
            patient_gender=req["patient_gender"],
            plan_id=req["plan_id"],
            diagnosis_codes=req["diagnosis_codes"],
            procedure_code=req["procedure_code"],
            clinical_notes=req["clinical_notes"],
            prior_treatments=req["prior_treatments"],
            attachments=req["attachments"],
            step_number=0,
            max_steps=MAX_STEPS,
            message=f"PA request {req['request_id']} loaded. Review the case and make a decision.",
            done=False,
            reward=0.0,
        )

    def step(
        self,
        action: MedicalPAAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> MedicalPAObservation:
        """Execute a step in the PA review process.

        Args:
            action: The agent's action (approve, deny, request_info, lookup_guideline, etc.)
            timeout_s: unused
            **kwargs: unused

        Returns:
            Observation with updated state and reward
        """
        if self._task is None:
            return MedicalPAObservation(
                message="Error: Environment not reset. Call reset() first.",
                done=True,
                reward=0.0,
            )

        if self._done:
            return MedicalPAObservation(
                message="Episode already finished. Call reset() to start a new episode.",
                done=True,
                reward=0.0,
            )

        self._state.step_count += 1
        step_num = self._state.step_count

        # Record action
        action_record = {
            "action_type": action.action_type,
            "payload": action.payload,
            "rationale": action.rationale,
            "step": step_num,
        }
        self._actions_taken.append(action_record)

        req = self._task["request"]

        # Handle each action type
        if action.action_type == "lookup_guideline":
            return self._handle_lookup_guideline(action, req, step_num)
        elif action.action_type == "check_formulary":
            return self._handle_check_formulary(action, req, step_num)
        elif action.action_type == "get_patient_history":
            return self._handle_get_patient_history(action, req, step_num)
        elif action.action_type == "request_info":
            return self._handle_request_info(action, req, step_num)
        elif action.action_type in ("approve", "deny"):
            return self._handle_decision(action, req, step_num)
        else:
            return self._make_observation(
                req, step_num,
                message=f"Unknown action type: {action.action_type}",
                reward=0.0,
            )

    def _handle_lookup_guideline(
        self, action: MedicalPAAction, req: Dict, step_num: int
    ) -> MedicalPAObservation:
        """Look up clinical guidelines for a procedure/diagnosis pair."""
        payload = action.payload
        proc = payload.get("procedure", req["procedure_code"])
        diag = payload.get("diagnosis", req["diagnosis_codes"][0] if req["diagnosis_codes"] else "")

        # Find matching guidelines
        matching = []
        for gl_id, gl in GUIDELINES.items():
            proc_match = proc in gl["procedure_codes"]
            diag_match = any(d in gl["diagnosis_codes"] for d in req["diagnosis_codes"])
            if proc_match or diag_match:
                matching.append(gl)

        if matching:
            result_parts = []
            for gl in matching:
                criteria_text = "\n".join(f"  - {c}" for c in gl["criteria"])
                docs_text = ", ".join(gl["required_documents"])
                result_parts.append(
                    f"Guideline {gl['id']}: {gl['title']}\n"
                    f"Criteria:\n{criteria_text}\n"
                    f"Required documents: {docs_text}\n"
                    f"Step therapy required: {gl['step_therapy_required']}\n"
                    f"Notes: {gl['notes']}"
                )
            self._guideline_result = "\n\n".join(result_parts)
        else:
            self._guideline_result = f"No guidelines found for procedure {proc} with diagnosis {diag}."

        # Check if max steps reached
        if step_num >= MAX_STEPS:
            return self._force_end(req, step_num, "Step limit reached without a decision.")

        return self._make_observation(
            req, step_num,
            message="Guideline lookup complete.",
            reward=0.0,
        )

    def _handle_check_formulary(
        self, action: MedicalPAAction, req: Dict, step_num: int
    ) -> MedicalPAObservation:
        """Check drug formulary status."""
        drug = action.payload.get("drug", "").lower()

        if drug in FORMULARY:
            info = FORMULARY[drug]
            self._formulary_result = (
                f"Drug: {info['brand_name']} ({info['generic_name']})\n"
                f"Formulary tier: {info['tier']}\n"
                f"Requires PA: {info['requires_pa']}\n"
                f"Step therapy requirements: {', '.join(info['step_therapy']) if info['step_therapy'] else 'None'}\n"
                f"Status: {info['status']}"
            )
        else:
            self._formulary_result = f"Drug '{drug}' not found in formulary database."

        if step_num >= MAX_STEPS:
            return self._force_end(req, step_num, "Step limit reached without a decision.")

        return self._make_observation(
            req, step_num,
            message="Formulary check complete.",
            reward=0.0,
        )

    def _handle_get_patient_history(
        self, action: MedicalPAAction, req: Dict, step_num: int
    ) -> MedicalPAObservation:
        """Retrieve patient treatment history."""
        history_data = self._task.get("patient_history", {})
        history_text = history_data.get("history", "No additional history available.")
        prior_auths = history_data.get("prior_auths", [])
        auths_text = "\n".join(f"  - {pa}" for pa in prior_auths) if prior_auths else "  None"

        self._patient_history_result = (
            f"Patient History:\n{history_text}\n\nPrior Authorizations:\n{auths_text}"
        )

        if step_num >= MAX_STEPS:
            return self._force_end(req, step_num, "Step limit reached without a decision.")

        return self._make_observation(
            req, step_num,
            message="Patient history retrieved.",
            reward=0.0,
        )

    def _handle_request_info(
        self, action: MedicalPAAction, req: Dict, step_num: int
    ) -> MedicalPAObservation:
        """Request additional documentation from the provider."""
        fields = action.payload.get("fields", [])
        if not fields:
            return self._make_observation(
                req, step_num,
                message="Error: request_info requires 'fields' in payload.",
                reward=0.0,
            )

        supplemental = self._task.get("supplemental_info", {})
        results = []
        for field in fields:
            if field in supplemental:
                results.append(f"[{field}]: {supplemental[field]}")
                self._info_received = True
            else:
                results.append(f"[{field}]: Document not available or not applicable to this case.")

        self._info_request_result = "\n\n".join(results)

        if step_num >= MAX_STEPS:
            return self._force_end(req, step_num, "Step limit reached without a decision.")

        return self._make_observation(
            req, step_num,
            message="Information request processed. Review the documents and make your decision.",
            reward=0.0,
        )

    def _handle_decision(
        self, action: MedicalPAAction, req: Dict, step_num: int
    ) -> MedicalPAObservation:
        """Handle approve or deny decision — terminal action."""
        self._done = True

        # Grade the episode
        ground_truth = self._task["ground_truth"]
        result = grade_task(self._task_id, self._actions_taken, ground_truth, MAX_STEPS)

        score = result["score"]
        breakdown = result["breakdown"]
        feedback = result["feedback"]

        return MedicalPAObservation(
            request_id=req["request_id"],
            patient_age=req["patient_age"],
            patient_gender=req["patient_gender"],
            plan_id=req["plan_id"],
            diagnosis_codes=req["diagnosis_codes"],
            procedure_code=req["procedure_code"],
            clinical_notes=req["clinical_notes"],
            prior_treatments=req["prior_treatments"],
            attachments=req["attachments"],
            guideline_result=self._guideline_result,
            formulary_result=self._formulary_result,
            patient_history_result=self._patient_history_result,
            info_request_result=self._info_request_result,
            step_number=step_num,
            max_steps=MAX_STEPS,
            message=f"Decision: {action.action_type}. {feedback}",
            reward_breakdown=breakdown,
            done=True,
            reward=score,
        )

    def _force_end(self, req: Dict, step_num: int, message: str) -> MedicalPAObservation:
        """Force episode end when step limit reached."""
        self._done = True

        ground_truth = self._task["ground_truth"]
        result = grade_task(self._task_id, self._actions_taken, ground_truth, MAX_STEPS)
        score = result["score"]
        breakdown = result["breakdown"]

        return MedicalPAObservation(
            request_id=req["request_id"],
            patient_age=req["patient_age"],
            patient_gender=req["patient_gender"],
            plan_id=req["plan_id"],
            diagnosis_codes=req["diagnosis_codes"],
            procedure_code=req["procedure_code"],
            clinical_notes=req["clinical_notes"],
            prior_treatments=req["prior_treatments"],
            attachments=req["attachments"],
            guideline_result=self._guideline_result,
            formulary_result=self._formulary_result,
            patient_history_result=self._patient_history_result,
            info_request_result=self._info_request_result,
            step_number=step_num,
            max_steps=MAX_STEPS,
            message=message,
            reward_breakdown=breakdown,
            done=True,
            reward=score,
        )

    def _make_observation(
        self, req: Dict, step_num: int, message: str, reward: float
    ) -> MedicalPAObservation:
        """Build a non-terminal observation."""
        return MedicalPAObservation(
            request_id=req["request_id"],
            patient_age=req["patient_age"],
            patient_gender=req["patient_gender"],
            plan_id=req["plan_id"],
            diagnosis_codes=req["diagnosis_codes"],
            procedure_code=req["procedure_code"],
            clinical_notes=req["clinical_notes"],
            prior_treatments=req["prior_treatments"],
            attachments=req["attachments"],
            guideline_result=self._guideline_result,
            formulary_result=self._formulary_result,
            patient_history_result=self._patient_history_result,
            info_request_result=self._info_request_result,
            step_number=step_num,
            max_steps=MAX_STEPS,
            message=message,
            done=False,
            reward=reward,
        )

    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state
