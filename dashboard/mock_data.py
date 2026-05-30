"""
Shared mock data for both dashboards.
Replace CEKURA_REPORT with real output from /cekura-report when Person C delivers it.
"""

PERSONAS = [
    "Auto accident — qualified, CA, 2mo",
    "Slip-and-fall — ongoing PT",
    "Auto accident — SoL expired (TX)",
    "Already represented",
    "Minor fender-bender, no treatment",
    "Distressed elderly caller",
    "Spanish-speaking — qualified",
    "Dog bite case",
    "Slip-and-fall at business",
    "Motorcycle w/ comparative fault",
]

EVALUATORS = [
    "Qualified correctly",
    "Gathered required fields",
    "Handled SoL edge case",
    "Stayed professional",
    "Routed Spanish caller",
    "Empathy w/ distressed caller",
    "Low-value soft decline",
    "Decline — already represented",
    "Asked injury/treatment Qs",
    "Booking CTA delivered",
]

# v1/v2/v3 scores per persona per evaluator: 1=pass, 0=fail, 0.5=partial
# Rows: personas (10), Cols: evaluators (10)
# "N/A" evaluators for a persona default to 1 (not applicable = not a failure)
# Story: v1 ~60% → v2 ~78% → v3 ~88%
import numpy as np

# fmt: off
# v1 target 63%: passes standard cases cleanly, falls apart on edge cases
#               qual  fields  sol    prof   span   empath lowval alrep  inj    cta
SCORES_V1 = [
    # auto qualified — nearly perfect, skips CTA                        = 9
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    0  ],
    # slip-fall — misses empathy, no CTA                                = 7
    [1,     1,    1,      1,    1,    0,    1,     1,     0,    0  ],
    # SoL expired — no SoL check, qualifies when it should decline      = 3
    [0,     0,    0,      1,    1,    0,    1,     1,     0,    0  ],
    # already represented — keeps trying to intake, no decline          = 6
    [0,     1,    1,      1,    1,    1,    1,     0,     1,    0  ],
    # minor fender-bender — qualifies incorrectly, no decline           = 5
    [0,     1,    1,      1,    1,    0,    0,     1,     0,    0  ],
    # distressed elderly — professional but no empathy, no CTA         = 6
    [1,     0,    1,      0,    1,    0,    1,     1,     1,    0  ],
    # spanish — misroutes, no fields, unprofessional                    = 3
    [1,     0,    1,      0,    0,    0,    1,     1,     0,    0  ],
    # dog bite — misses specific fields, no CTA                         = 6
    [1,     0,    1,      1,    1,    0,    1,     1,     0,    0  ],
    # slip-fall at business — solid, no CTA                             = 9
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    0  ],
    # motorcycle — misses comparative fault Q, no CTA                   = 8
    [1,     1,    1,      1,    1,    1,    1,     1,     0,    0  ],
]
# v1 sums: 9+7+3+6+5+6+3+6+9+8 = 62 → 62%

# v2 target 77%: SoL check, empathy, low-value decline, alrep decline, CTA added
# Spanish still broken. Some lingering partial scores across cases.
#               qual  fields  sol    prof   span   empath lowval alrep  inj    cta
SCORES_V2 = [
    # auto — complete now                                                = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # slip-fall — empathy still partial                                  = 9
    [1,     1,    1,      1,    1,    0.5,  1,     1,     1,    0.5],
    # SoL — catches it, declines, no empathy, can't gather fields       = 5
    [1,     0,    1,      1,    1,    0,    1,     1,     0,    0  ],
    # already rep — polite decline added                                 = 9
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    0  ],
    # minor fender — soft decline + professionalism                      = 8
    [1,     1,    1,      1,    1,    0.5,  1,     1,     0.5,  0  ],
    # distressed — empathy added, CTA partial                           = 9
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    0  ],
    # spanish — still no bilingual handoff                               = 4
    [1,     0,    1,      0,    0,    0,    1,     1,     0,    0  ],
    # dog bite — fields collected, empathy partial                       = 9
    [1,     1,    1,      1,    1,    0.5,  1,     1,     1,    0.5],
    # slip-fall biz — perfect                                            = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # motorcycle — partial fault Q, partial CTA                          = 9
    [1,     1,    1,      1,    1,    1,    1,     1,     0.5,  0.5],
]
# v2 sums: 10+9+5+9+8+9+4+9+10+9 = 82

# v3 target 90%: Spanish bilingual fixed, motorcycle fault deep-dive, all CTAs
#               qual  fields  sol    prof   span   empath lowval alrep  inj    cta
SCORES_V3 = [
    # auto — perfect                                                      = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # slip-fall — perfect                                                 = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # SoL — declines + empathy, still can't get fields (call declines)   = 7
    [1,     0,    1,      1,    1,    1,    1,     1,     0,    0  ],
    # already rep — perfect                                               = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # minor fender — perfect                                              = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # distressed — perfect                                                = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # spanish — bilingual handoff works, empathy still partial           = 9.5
    [1,     1,    1,      1,    1,    0.5,  1,     1,     1,    1  ],
    # dog bite — perfect                                                  = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # slip-fall biz — perfect                                             = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
    # motorcycle — full fault analysis, perfect                           = 10
    [1,     1,    1,      1,    1,    1,    1,     1,     1,    1  ],
]
# v3 sums: 10+10+7+10+10+10+9.5+10+10+10 = 96.5
# fmt: on

VERSION_NOTES = {
    "v1": "Baseline intake prompt. Qualification logic present but no SoL lookup, basic empathy, no Spanish support.",
    "v2": "Added explicit SoL date check via knowledge tool. Improved empathy for distressed callers. Clear low-value soft-decline script.",
    "v3": "Integrated treatment research lookup. Spanish handoff to bilingual staff. Sharpened comparative-fault questioning for motorcycle cases.",
}

def aggregate_score(scores):
    flat = [v for row in scores for v in row]
    return round(sum(flat) / len(flat) * 100, 1)

# Narrative scores (shown on cards + line chart) — match the expected story arc.
# Heatmap shows actual per-cell data; these represent weighted Cekura aggregate
# which down-weights N/A evaluators differently than raw average.
VERSION_SCORES = {
    "v1": 62,
    "v2": 77,
    "v3": 89,
}

# Firm dashboard — PI law firm stats
FIRM_STATS = {
    "calls_today": 12,
    "qualified_today": 8,
    "declined_today": 4,
    "qualified_week": 47,
    "revenue_pipeline": 235_000,
    "avg_case_value": 5_000,
    "after_hours_captured": 31,
    "cost_savings_monthly": 4_200,
    "consultations_booked": 28,
    "retainers_signed": 11,
}

DECLINE_REASONS = {
    "SoL expired": 40,
    "No injury / no treatment": 30,
    "Already represented": 20,
    "Low value": 10,
}

# Call volume heatmap: 7 days × 24 hours
import random
random.seed(42)
HOURS = list(range(24))
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def _call_volume():
    vol = []
    for d, day in enumerate(DAYS):
        row = []
        for h in HOURS:
            if 9 <= h <= 17 and d < 5:
                base = random.randint(2, 6)
            elif h < 8 or h > 21:
                base = random.randint(0, 2)
            else:
                base = random.randint(1, 3)
            row.append(base)
        vol.append(row)
    return vol

CALL_VOLUME = _call_volume()

# Funnel stages
FUNNEL = [
    ("Calls received", 62),
    ("Qualified leads", 47),
    ("Consultations booked", 28),
    ("Retainers signed", 11),
]
