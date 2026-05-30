from __future__ import annotations

import tools.treatment_classifier as tc


def test_classify_treatment_high_severity_has_expected_red_flags():
    result = tc.classify_treatment(
        injuries_described="Back and neck pain, headaches, and anxiety",
        er_visit=True,
        hospitalized=True,
        hospitalization_days=7,
        surgery_required=True,
        loss_of_consciousness=True,
        persistent_headaches=True,
        spine_or_nerve_mentioned=True,
        physical_therapy=True,
        still_in_treatment=True,
        returned_to_work=False,
        psychological_symptoms=True,
    )

    assert result["severity_tier"] == "catastrophic"
    assert result["severity_score"] == 100
    assert result["treatment_trajectory"] == "permanent"
    assert result["delayed_onset_risk"] is False
    assert "possible_TBI" in result["red_flags"]
    assert "spinal_injury" in result["red_flags"]
    assert "major_surgical_case" in result["red_flags"]
    assert "psych_trauma" in result["red_flags"]
    assert "catastrophic_case_senior_partner_required" in result["red_flags"]
    assert "Severity tier: catastrophic" in result["notes"]


def test_classify_treatment_minimal_case_flags_delayed_onset():
    result = tc.classify_treatment(
        injuries_described="Feeling fine",
        er_visit=False,
        hospitalized=False,
        hospitalization_days=0,
        surgery_required=False,
        loss_of_consciousness=False,
        persistent_headaches=False,
        spine_or_nerve_mentioned=False,
        physical_therapy=False,
        still_in_treatment=False,
        returned_to_work=True,
        psychological_symptoms=False,
    )

    assert result["severity_tier"] == "minor"
    assert result["severity_score"] == 0
    assert result["treatment_trajectory"] == "short_term"
    assert result["delayed_onset_risk"] is True
    assert result["delayed_onset_warning"].startswith("I want to make sure you're okay")
    assert result["red_flags"] == []
