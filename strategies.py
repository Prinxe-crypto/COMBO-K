"""
strategies.py
-------------
Defines all 12 strategies (P1-P8 standard permutations, S1-S4 synthetic
covered structures). Each strategy says:
  - which single-leg side it bets on (BTC or ETH, up or down)
  - which combo outcome it pairs with (both up, or both down)

You should not need to edit this file unless you want to add/remove
a strategy from the matrix.
"""

# Each strategy is a dict describing its two legs.
# single_asset: "BTC" or "ETH"
# single_side: "up" or "down"
# combo_outcome: "both_up" or "both_down"  (the combo leg always bets on
#                co-directional movement; which one depends on the strategy)

STRATEGIES = {
    # ── Standard Permutations (P1-P8) ──────────────────────────────────
    # Single leg direction matches the combo's co-directional bet.
    "P1": {"single_asset": "BTC", "single_side": "up",   "combo_outcome": "both_up"},
    "P2": {"single_asset": "BTC", "single_side": "up",   "combo_outcome": "both_up"},
    "P3": {"single_asset": "BTC", "single_side": "down", "combo_outcome": "both_down"},
    "P4": {"single_asset": "BTC", "single_side": "down", "combo_outcome": "both_down"},
    "P5": {"single_asset": "ETH", "single_side": "up",   "combo_outcome": "both_up"},
    "P6": {"single_asset": "ETH", "single_side": "up",   "combo_outcome": "both_up"},
    "P7": {"single_asset": "ETH", "single_side": "down", "combo_outcome": "both_down"},
    "P8": {"single_asset": "ETH", "single_side": "down", "combo_outcome": "both_down"},

    # ── Synthetic Covered Structures (S1-S4) ────────────────────────────
    # Single leg direction is CROSS to the combo's co-directional bet —
    # these hedge against correlation breakdown.
    "S1": {"single_asset": "ETH", "single_side": "down", "combo_outcome": "both_up"},
    "S2": {"single_asset": "BTC", "single_side": "up",   "combo_outcome": "both_down"},
    "S3": {"single_asset": "ETH", "single_side": "up",   "combo_outcome": "both_down"},
    "S4": {"single_asset": "BTC", "single_side": "down", "combo_outcome": "both_up"},
}


def all_strategy_names():
    return list(STRATEGIES.keys())


def get_strategy(name: str) -> dict:
    return STRATEGIES[name]
