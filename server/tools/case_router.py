from __future__ import annotations

try:
    from pipecat.services.llm_service import FunctionCallParams
except Exception:  # pragma: no cover - fallback for environments without pipecat installed

    class FunctionCallParams:  # type: ignore[no-redef]
        """Minimal fallback matching the attributes used by the tool handlers."""

        def __init__(self, arguments: dict | None = None, result_callback=None):
            self.arguments = arguments or {}
            self.result_callback = result_callback or self._noop_result_callback

        async def _noop_result_callback(self, *_args, **_kwargs):
            return None

_ALLOWED_CASE_TYPES = {
    "mva",
    "slip_fall",
    "dog_bite",
    "trucking",
    "medmal",
    "product_liability",
    "workers_comp",
    "wrongful_death",
    "other",
}
_ALLOWED_SEVERITIES = {"minor", "moderate", "severe", "catastrophic"}
_ALLOWED_VALUES = {"low", "medium", "high"}


def _urgency_from_severity(severity_tier: str, case_type: str) -> str:
    """Derive urgency from the severity tier and case type.

    Args:
        severity_tier: Injury severity tier.
        case_type: Case category.

    Returns:
        "immediate", "standard", or "low".

    Raises:
        None.
    """

    if severity_tier == "catastrophic" or case_type == "wrongful_death":
        return "immediate"
    if severity_tier in {"moderate", "severe"}:
        return "standard"
    return "low"


def route_case(
    case_type: str,
    severity_tier: str,
    state: str,
    sol_viable: bool,
    has_prior_representation: bool,
    defendant_type: str,
    estimated_case_value: str,
) -> dict:
    """Route a personal injury intake to the appropriate attorney tier.

    Args:
        case_type: One of the supported case categories.
        severity_tier: "minor", "moderate", "severe", or "catastrophic".
        state: Two-letter state code.
        sol_viable: Whether the SoL is still open.
        has_prior_representation: Whether the caller already has counsel.
        defendant_type: "private" or "government".
        estimated_case_value: "low", "medium", or "high".

    Returns:
        A routing decision dictionary containing decision, attorney tier, reason,
        decline_reason when applicable, referral note when applicable, urgency,
        and human-readable notes.

    Raises:
        ValueError: If severity_tier or estimated_case_value is invalid.
    """

    normalized_case_type = case_type.strip().lower()
    normalized_severity = severity_tier.strip().lower()
    normalized_state = state.strip().upper()
    normalized_defendant_type = defendant_type.strip().lower()
    normalized_value = estimated_case_value.strip().lower()

    if normalized_severity not in _ALLOWED_SEVERITIES:
        raise ValueError(f"Unknown severity_tier: {severity_tier!r}")
    if normalized_value not in _ALLOWED_VALUES:
        raise ValueError(f"Unknown estimated_case_value: {estimated_case_value!r}")
    if normalized_case_type not in _ALLOWED_CASE_TYPES:
        normalized_case_type = "other"

    urgency = _urgency_from_severity(normalized_severity, normalized_case_type)
    government_note = (
        " Government defendant — confirm notice of claim deadline immediately with assigned attorney."
        if normalized_defendant_type == "government"
        else ""
    )

    if not sol_viable:
        return {
            "decision": "declined",
            "attorney_tier": None,
            "reason": "sol_expired",
            "decline_reason": "sol_expired",
            "referral_note": None,
            "urgency": urgency,
            "notes": f"Statute of limitations appears expired in {normalized_state}, so the case should be declined.{government_note}",
        }

    if has_prior_representation:
        return {
            "decision": "declined",
            "attorney_tier": None,
            "reason": "prior_representation",
            "decline_reason": "prior_representation",
            "referral_note": None,
            "urgency": urgency,
            "notes": f"Caller already has prior representation in {normalized_state}, so the case should be declined.{government_note}",
        }

    if normalized_case_type == "workers_comp":
        referral_note = (
            "This sounds like a workers compensation claim. We recommend contacting a workers comp specialist — we'd be happy to provide a referral."
        )
        return {
            "decision": "declined",
            "attorney_tier": "referral_out",
            "reason": "workers_comp_refer",
            "decline_reason": "workers_comp_refer",
            "referral_note": referral_note,
            "urgency": urgency,
            "notes": f"{referral_note}{government_note}",
        }

    attorney_tier: str
    referral_note: str | None = None
    reason: str

    if normalized_case_type == "wrongful_death":
        attorney_tier = "senior_partner"
        reason = "wrongful_death_case"
    elif normalized_severity == "catastrophic":
        attorney_tier = "senior_partner"
        reason = "catastrophic_injury_case"
    elif normalized_value == "high":
        attorney_tier = "senior_partner"
        reason = "high_value_case"
    elif normalized_case_type == "trucking":
        attorney_tier = "senior_partner"
        reason = "trucking_case"
    elif normalized_case_type == "medmal":
        attorney_tier = "referral_out"
        reason = "medmal_specialty_referral"
        referral_note = "Medical malpractice requires specialized expertise. We can provide a referral to a trusted medmal attorney."
    elif normalized_case_type == "product_liability" and normalized_severity in {"severe", "catastrophic"}:
        attorney_tier = "senior_partner"
        reason = "serious_product_liability_case"
    elif normalized_case_type == "mva" and normalized_severity == "moderate":
        attorney_tier = "mid_associate"
        reason = "moderate_mva_case"
    elif normalized_case_type == "slip_fall" and normalized_severity in {"moderate", "severe"}:
        attorney_tier = "mid_associate"
        reason = "slip_fall_mid_level_case"
    elif normalized_case_type == "product_liability" and normalized_severity == "moderate":
        attorney_tier = "mid_associate"
        reason = "moderate_product_liability_case"
    elif normalized_case_type == "mva" and normalized_severity == "minor":
        attorney_tier = "junior"
        reason = "minor_mva_case"
    elif normalized_case_type == "dog_bite":
        attorney_tier = "junior"
        reason = "dog_bite_case"
    elif normalized_case_type == "slip_fall" and normalized_severity == "minor":
        attorney_tier = "junior"
        reason = "minor_slip_fall_case"
    else:
        attorney_tier = "mid_associate"
        reason = "standard_intake_assignment"

    notes = f"Case routed as {attorney_tier} assignment for a {normalized_severity} {normalized_case_type} matter in {normalized_state}.{government_note}"
    if referral_note:
        notes = f"{notes} {referral_note}"

    return {
        "decision": "qualified",
        "attorney_tier": attorney_tier,
        "reason": reason,
        "decline_reason": None,
        "referral_note": referral_note,
        "urgency": urgency,
        "notes": notes,
    }


async def route_case_handler(params: FunctionCallParams) -> None:
    """Pipecat handler that wraps route_case.

    Args:
        params: Pipecat FunctionCallParams containing function arguments and a
            result callback.

    Returns:
        None. The structured result is emitted with params.result_callback().

    Raises:
        None. Any exception should be handled by the surrounding runtime.
    """

    result = route_case(**params.arguments)
    await params.result_callback(result)
