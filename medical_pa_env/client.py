"""Medical Prior Authorization Environment Client."""

from typing import Any, Dict, List

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import MedicalPAAction, MedicalPAObservation


class MedicalPAEnv(EnvClient[MedicalPAAction, MedicalPAObservation, State]):
    """
    Client for the Medical Prior Authorization Environment.

    Connects via WebSocket to the environment server and provides
    typed step/reset/state operations.

    Example:
        >>> async with MedicalPAEnv(base_url="http://localhost:8000") as client:
        ...     result = await client.reset()
        ...     print(result.observation.request_id)
        ...
        ...     action = MedicalPAAction(
        ...         action_type="lookup_guideline",
        ...         payload={"procedure": "73721", "diagnosis": "S83.511A"},
        ...     )
        ...     result = await client.step(action)
        ...     print(result.observation.guideline_result)

    Example with Docker:
        >>> client = await MedicalPAEnv.from_docker_image("medical-pa-env:latest")
        >>> result = await client.reset()
        >>> await client.close()
    """

    def _step_payload(self, action: MedicalPAAction) -> Dict:
        """Convert action to JSON payload for the step message."""
        return {
            "action_type": action.action_type,
            "payload": action.payload,
            "rationale": action.rationale,
        }

    def _parse_result(self, payload: Dict) -> StepResult[MedicalPAObservation]:
        """Parse server response into StepResult[MedicalPAObservation]."""
        obs_data = payload.get("observation", {})
        observation = MedicalPAObservation(
            request_id=obs_data.get("request_id", ""),
            patient_age=obs_data.get("patient_age", 0),
            patient_gender=obs_data.get("patient_gender", ""),
            plan_id=obs_data.get("plan_id", ""),
            diagnosis_codes=obs_data.get("diagnosis_codes", []),
            procedure_code=obs_data.get("procedure_code", ""),
            clinical_notes=obs_data.get("clinical_notes", ""),
            prior_treatments=obs_data.get("prior_treatments", []),
            attachments=obs_data.get("attachments", []),
            guideline_result=obs_data.get("guideline_result"),
            formulary_result=obs_data.get("formulary_result"),
            patient_history_result=obs_data.get("patient_history_result"),
            info_request_result=obs_data.get("info_request_result"),
            available_actions=obs_data.get("available_actions", []),
            step_number=obs_data.get("step_number", 0),
            max_steps=obs_data.get("max_steps", 8),
            message=obs_data.get("message", ""),
            reward_breakdown=obs_data.get("reward_breakdown"),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State object."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
