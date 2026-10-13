"""Whole-edition DeepSeek CNY budget with pessimistic, pre-request reservations.

A timeout or uncertain API outcome never gets blindly retried. Reservations
count at peak cache-miss prices even for the Beijing 01:00 off-peak run.
Actual provider billing can change if published prices change; fail closed.
"""
from __future__ import annotations

from decimal import Decimal
import logging

import requests
from ai_commentary import API_URL
from llm_budget import (
    DEFAULT_MODEL, conservative_input_tokens, estimate_peak_cost,
    actual_cost_ceiling,
)

LOG = logging.getLogger("newspaper.editorial.budget")
EDITION_CAP_RMB = Decimal("1.00")
SAFETY_MARGIN_RMB = Decimal("0.02")
COMMENTARY_RESERVE_RMB = Decimal("0.12")
MODEL = DEFAULT_MODEL  # official deepseek-flash / V4.1-Flash

class BudgetExhausted(RuntimeError):
    """Editorial quality work exceeds the remaining pre-authorized expense."""


class EditionBudget:
    def __init__(self, cap=EDITION_CAP_RMB):
        self.cap = Decimal(str(cap))
        if not (Decimal("0") < self.cap <= EDITION_CAP_RMB):
            raise ValueError("Cannot authorize more than 1.00 CNY per edition")
        self.spent_ceiling = Decimal("0")
        self.requests = 0
        self.breakdown = []

    def request(self, messages, max_tokens, key, *, purpose,
                transport=None, before_request=None):
        if purpose not in ("report", "commentary"):
            raise ValueError("Unrecognized billable task")
        if not isinstance(max_tokens, int) or not (0 < max_tokens <= 4200):
            raise ValueError("Invalid output cap")
        if not key or not key.strip():
            raise ValueError("Missing editorial model credential")
        worst_tokens = conservative_input_tokens(messages)
        reservation = estimate_peak_cost(MODEL, worst_tokens, max_tokens)
        protected = COMMENTARY_RESERVE_RMB if purpose == "report" else Decimal("0")
        if self.spent_ceiling + reservation + protected > self.cap - SAFETY_MARGIN_RMB:
            raise BudgetExhausted(
                "Whole-issue DeepSeek upper-bound budget insufficient; no request issued"
            )

        # Reserve before hitting the provider. Failure/timeout can have been billed.
        self.spent_ceiling += reservation
        self.requests += 1
        self.breakdown.append({
            "purpose": purpose, "reserved_rmb": str(reservation),
            "input_upper_bound": worst_tokens, "max_output": max_tokens,
            "status": "uncertain",
        })
        if before_request:
            before_request()
        response = (transport or requests.post)(
            API_URL,
            headers={"Authorization": "Bearer " + key.strip(),
                     "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "max_tokens": max_tokens,
                  "thinking": {"type": "disabled"},
                  "response_format": {"type": "json_object"}, "stream": False},
            timeout=(15, 90),
        )
        if response.status_code != 200:
            raise RuntimeError("Editorial API HTTP " + str(response.status_code))
        data = response.json()
        try:
            observed = actual_cost_ceiling(MODEL, data.get("usage"))
        except (TypeError, ValueError, KeyError):
            # Missing usage means leave conservative reservation in place.
            observed = reservation
        if observed > reservation:
            # Provider accounting exceeded prior conservative cap; do not
            # issue further API calls, and surface the violation.
            self.spent_ceiling += observed - reservation
            raise BudgetExhausted("Reported API usage exceeded preflight reservation")
        self.spent_ceiling += observed - reservation
        self.breakdown[-1]["status"] = "accounted"
        self.breakdown[-1]["conservative_cost_rmb"] = str(observed)
        LOG.info("Editorial API %s #%d conservative charge RMB=%s; issue total <= %s",
                 purpose, self.requests, observed, self.spent_ceiling)
        choice = (data.get("choices") or [{}])[0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("Incomplete editorial JSON completion")
        content = choice.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Blank editorial JSON completion")
        return content

    def snapshot(self):
        return {
            "request_count": self.requests,
            "estimated_peak_cost_rmb": str(self.spent_ceiling),
            "edition_ceiling_rmb": str(self.cap),
            "calls": list(self.breakdown),
        }
