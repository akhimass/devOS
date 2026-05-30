from __future__ import annotations

import tools.case_router as cr


def test_route_case_declines_for_expired_sol():
    result = cr.route_case(
        case_type="mva",
        severity_tier="moderate",
        state="CA",
        sol_viable=False,
        has_prior_representation=False,
        defendant_type="private",
        estimated_case_value="medium",
    )

    assert result["decision"] == "declined"
    assert result["decline_reason"] == "sol_expired"
    assert result["attorney_tier"] is None
    assert result["urgency"] == "standard"
    assert "expired" in result["notes"].lower()


def test_route_case_refers_workers_comp_cases_out():
    result = cr.route_case(
        case_type="workers_comp",
        severity_tier="minor",
        state="TX",
        sol_viable=True,
        has_prior_representation=False,
        defendant_type="private",
        estimated_case_value="low",
    )

    assert result["decision"] == "declined"
    assert result["attorney_tier"] == "referral_out"
    assert result["decline_reason"] == "workers_comp_refer"
    assert result["referral_note"] is not None
    assert "workers compensation" in result["referral_note"].lower()


def test_route_case_qualifies_mva_moderate_and_mentions_government_defendant():
    result = cr.route_case(
        case_type="mva",
        severity_tier="moderate",
        state="NY",
        sol_viable=True,
        has_prior_representation=False,
        defendant_type="government",
        estimated_case_value="medium",
    )

    assert result["decision"] == "qualified"
    assert result["attorney_tier"] == "mid_associate"
    assert result["urgency"] == "standard"
    assert result["decline_reason"] is None
    assert "Government defendant" in result["notes"]


def test_route_case_handles_wrongful_death_as_immediate_senior_partner():
    result = cr.route_case(
        case_type="wrongful_death",
        severity_tier="catastrophic",
        state="GA",
        sol_viable=True,
        has_prior_representation=False,
        defendant_type="private",
        estimated_case_value="high",
    )

    assert result["decision"] == "qualified"
    assert result["attorney_tier"] == "senior_partner"
    assert result["urgency"] == "immediate"
    assert result["reason"] == "wrongful_death_case"
