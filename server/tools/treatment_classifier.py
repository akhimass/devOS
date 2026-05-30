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

_DELAYED_ONSET_WARNING = (
    "I want to make sure you're okay — sometimes injuries like whiplash or internal trauma don't show symptoms right away. Even if you feel fine now, I'd strongly encourage you to see a doctor in the next 24 to 48 hours, both for your health and to document any injuries for your case."
)


def _tier_from_score(score: int) -> str:
    """Map a numeric severity score to a tier.

    Args:
        score: Internal 0-100 severity score.

    Returns:
        One of "minor", "moderate", "severe", or "catastrophic".

    Raises:
        None.
    """

    if score <= 19:
        return "minor"
    if score <= 44:
        return "moderate"
    if score <= 74:
        return "severe"
    return "catastrophic"


def _trajectory_from_tier(severity_tier: str) -> str:
    """Convert a severity tier to a treatment trajectory.

    Args:
        severity_tier: One of the accepted severity tiers.

    Returns:
        "short_term", "long_term", or "permanent".

    Raises:
        None.
    """

    if severity_tier == "minor":
        return "short_term"
    if severity_tier == "moderate":
        return "long_term"
    return "permanent"


def classify_treatment(
    injuries_described: str,
    er_visit: bool,
    hospitalized: bool,
    hospitalization_days: int,
    surgery_required: bool,
    loss_of_consciousness: bool,
    persistent_headaches: bool,
    spine_or_nerve_mentioned: bool,
    physical_therapy: bool,
    still_in_treatment: bool,
    returned_to_work: bool,
    psychological_symptoms: bool,
) -> dict:
    """Classify treatment severity and identify red flags for intake routing.

    Args:
        injuries_described: Free-text injury description.
        er_visit: Whether the caller visited the ER.
        hospitalized: Whether the caller was hospitalized.
        hospitalization_days: Number of days hospitalized, or 0 if none.
        surgery_required: Whether surgery was required.
        loss_of_consciousness: Whether there was any loss of consciousness.
        persistent_headaches: Whether headaches persisted beyond 48 hours.
        spine_or_nerve_mentioned: Whether spine or nerve injury was mentioned.
        physical_therapy: Whether physical therapy is involved.
        still_in_treatment: Whether the caller is still receiving treatment.
        returned_to_work: Whether the caller has returned to work.
        psychological_symptoms: Whether PTSD, anxiety, or depression symptoms are present.

    Returns:
        A structured dictionary containing the severity tier, score, red flags,
        delayed-onset risk and warning text, treatment trajectory, and notes.

    Raises:
        ValueError: If hospitalization_days is negative.
    """

    if hospitalization_days < 0:
        raise ValueError("hospitalization_days must be non-negative")

    score = 0
    red_flags: list[str] = []

    if er_visit:
        score += 10
    if hospitalized:
        score += 15
    if hospitalization_days >= 3:
        score += 10
    if hospitalization_days >= 7:
        score += 10
    if surgery_required:
        score += 20
    if loss_of_consciousness:
        score += 25
    if persistent_headaches:
        score += 15
    if spine_or_nerve_mentioned:
        score += 20
    if physical_therapy:
        score += 10
    if still_in_treatment:
        score += 10
    if not returned_to_work:
        score += 10
    if psychological_symptoms:
        score += 10

    score = max(0, min(score, 100))
    severity_tier = _tier_from_score(score)
    treatment_trajectory = _trajectory_from_tier(severity_tier)

    if loss_of_consciousness:
        red_flags.append("possible_TBI")
    if spine_or_nerve_mentioned:
        red_flags.append("spinal_injury")
    if surgery_required and hospitalization_days >= 7:
        red_flags.append("major_surgical_case")
    if psychological_symptoms:
        red_flags.append("psych_trauma")
    if score >= 75:
        red_flags.append("catastrophic_case_senior_partner_required")

    delayed_onset_risk = not er_visit and not hospitalized and not still_in_treatment
    delayed_onset_warning = _DELAYED_ONSET_WARNING if delayed_onset_risk else ""

    notes_parts = [
        f"Injury description: {injuries_described.strip() or 'n/a'}.",
        f"Severity tier: {severity_tier} ({score}/100).",
        f"Treatment trajectory: {treatment_trajectory}.",
    ]
    if red_flags:
        notes_parts.append(f"Red flags detected: {', '.join(red_flags)}.")
    if delayed_onset_risk:
        notes_parts.append(
            "Delayed-onset risk is present because the caller did not report an ER visit, hospitalization, or ongoing treatment."
        )

    return {
        "severity_tier": severity_tier,
        "severity_score": score,
        "red_flags": red_flags,
        "delayed_onset_risk": delayed_onset_risk,
        "delayed_onset_warning": delayed_onset_warning,
        "treatment_trajectory": treatment_trajectory,
        "notes": " ".join(notes_parts),
    }


async def classify_treatment_handler(params: FunctionCallParams) -> None:
    """Pipecat handler that wraps classify_treatment.

    Args:
        params: Pipecat FunctionCallParams containing function arguments and a
            result callback.

    Returns:
        None. The structured result is emitted with params.result_callback().

    Raises:
        None. Any exception should be handled by the surrounding runtime.
    """

    result = classify_treatment(**params.arguments)
    await params.result_callback(result)
