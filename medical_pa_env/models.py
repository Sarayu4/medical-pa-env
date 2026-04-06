"""
Data models for the Medical Prior Authorization Environment.

Defines the action and observation spaces for an AI agent performing
insurance prior authorization review of medical procedures.
"""

import json
from typing import Any, Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import Field, field_validator


class MedicalPAAction(Action):
    """Action the agent can take in the prior auth review process.

    action_type determines which tool/decision the agent is using:
      - approve: Approve the prior authorization request
      - deny: Deny the request with a reason code
      - request_info: Request additional documentation from the provider
      - lookup_guideline: Look up clinical guidelines for a procedure/diagnosis pair
      - check_formulary: Check drug formulary status
      - get_patient_history: Retrieve detailed patient treatment history
    """

    action_type: Literal[
        "approve",
        "deny",
        "request_info",
        "lookup_guideline",
        "check_formulary",
        "get_patient_history",
    ] = Field(..., description="Type of action to perform")

    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Action-specific payload. "
            "For deny: {reason_code: str}. "
            "For request_info: {fields: list[str]}. "
            "For lookup_guideline: {procedure: str, diagnosis: str}. "
            "For check_formulary: {drug: str}. "
            "For approve/get_patient_history: {} (empty)."
        ),
    )

    rationale: Optional[str] = Field(
        default=None,
        description="Agent's rationale for the action. Required for approve/deny.",
    )

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> Dict[str, Any]:
        """Accept payload as either a dict or a JSON string (web UI sends strings)."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            return {}
        return v if isinstance(v, dict) else {}


class MedicalPAObservation(Observation):
    """Observation returned to the agent after each step.

    Contains the current state of the PA review visible to the agent.
    """

    request_id: str = Field(default="", description="Unique ID for this PA request")
    patient_age: int = Field(default=0, description="Patient age in years")
    patient_gender: str = Field(default="", description="Patient gender")
    plan_id: str = Field(default="", description="Insurance plan identifier")
    diagnosis_codes: List[str] = Field(
        default_factory=list, description="ICD-10 diagnosis codes"
    )
    procedure_code: str = Field(default="", description="CPT procedure code")
    clinical_notes: str = Field(
        default="", description="Free-text clinical notes from provider"
    )
    prior_treatments: List[str] = Field(
        default_factory=list, description="Prior treatments the patient has received"
    )
    attachments: List[str] = Field(
        default_factory=list, description="Documents attached to the request"
    )

    # Dynamic fields populated by agent actions
    guideline_result: Optional[str] = Field(
        default=None, description="Result of the last guideline lookup"
    )
    formulary_result: Optional[str] = Field(
        default=None, description="Result of the last formulary check"
    )
    patient_history_result: Optional[str] = Field(
        default=None, description="Result of patient history retrieval"
    )
    info_request_result: Optional[str] = Field(
        default=None, description="Result of requesting additional information"
    )

    available_actions: List[str] = Field(
        default_factory=lambda: [
            "approve",
            "deny",
            "request_info",
            "lookup_guideline",
            "check_formulary",
            "get_patient_history",
        ],
        description="Actions available to the agent",
    )

    step_number: int = Field(default=0, description="Current step in the episode")
    max_steps: int = Field(default=8, description="Maximum steps per episode")
    message: str = Field(
        default="", description="Human-readable status message"
    )

    # Reward breakdown visible to agent after terminal action
    reward_breakdown: Optional[Dict[str, float]] = Field(
        default=None, description="Breakdown of reward components (terminal only)"
    )
