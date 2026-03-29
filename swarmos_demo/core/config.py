"""Centralized configuration for all A-line tunable constants.

Every magic number that was previously hardcoded in individual modules is
collected here.  Modules import what they need from this file.

Sections mirror the module they feed into:

  COST_*      → core/cost.py, core/router.py
  CONFLICT_*  → core/conflict.py
  REPUTATION_* → core/reputation.py
  LEARNED_*   → core/learned_router.py
  WORKFLOW_*  → core/workflow.py, serve.py
  PROVIDER_*  → providers/openai_compatible.py
  ROUTER_*    → core/router.py  (routing score tweaks)
"""
from __future__ import annotations

# ── Cost estimation ──────────────────────────────────────────────────
COST_PER_1K_PROMPT = 0.003
COST_PER_1K_COMPLETION = 0.006
COST_CHARS_PER_TOKEN = 3.5

# ── Conflict detection ───────────────────────────────────────────────
CONFLICT_CONFIDENCE_SPREAD = 0.25
CONFLICT_MIN_PROPOSALS = 2

# ── Reputation system ────────────────────────────────────────────────
REPUTATION_DEFAULT = 0.50
REPUTATION_LEARNING_RATE = 0.15
REPUTATION_WEIGHT = 0.10

# ── Learned routing ──────────────────────────────────────────────────
LEARNED_LEARNING_RATE = 0.20
LEARNED_BONUS_WEIGHT = 0.10
LEARNED_MAX_BONUS = 0.10
LEARNED_W_CONF = 0.50
LEARNED_W_REC = 0.30
LEARNED_W_RISK = 0.20

# ── Workflow / serve pipeline ────────────────────────────────────────
WORKFLOW_PROPOSE_TIMEOUT_S = 120

# ── OpenAI-compatible provider ───────────────────────────────────────
PROVIDER_MAX_RETRIES = 3
PROVIDER_BASE_BACKOFF_S = 1.0
PROVIDER_REQUEST_TIMEOUT_S = 60

# ── Router score bumps ───────────────────────────────────────────────
ROUTER_BASE_SCORE = 0.05
ROUTER_KEYWORD_BOOST = 0.14
ROUTER_PLANNER_BOOST = 0.18
ROUTER_DOMAIN_BOOST = {
    "systems_architect": 0.22,
    "coding_engineer": 0.20,
    "research_scientist": 0.20,
    "product_strategist": 0.14,
    "math_optimizer": 0.12,
    "legal_risk": 0.28,
    "medical_safety": 0.28,
}
