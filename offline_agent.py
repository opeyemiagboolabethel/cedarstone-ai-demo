from __future__ import annotations

import re
from typing import Any, Dict

from cedarstone_tools import CedarStoneTools


def money(x: float) -> str:
    return f"₦{float(x):,.0f}"


class OfflineDemoAgent:
    """Zero-API-key fallback for predictable demonstrations and development."""

    def __init__(self, tools: CedarStoneTools):
        self.tools = tools

    def ask(self, message: str) -> Dict[str, Any]:
        q = message.lower().strip()

        if any(k in q for k in ["management briefing", "requires my attention", "attention today", "morning briefing"]):
            d = self.tools.generate_management_briefing()
            m = d["metrics"]
            text = (
                f"Management attention is required across six areas. "
                f"There are {m['high_value_stale_leads']} high-value stale leads, "
                f"{money(m['overdue_receivables_ngn'])} in overdue receivables, "
                f"target-weekend shortlet occupancy is {m['target_weekend_occupancy_pct']}%, "
                f"{m['critical_maintenance_over_48h']} critical maintenance cases have been open over 48 hours, "
                f"{m['delayed_or_late_milestones']} construction milestones are delayed/late, and "
                f"{m['investors_awaiting_updates']} investors are awaiting updates."
            )
            return {"text": text, "provider": "offline-demo", "tool": "generate_management_briefing", "data": d}

        if "lead" in q and any(k in q for k in ["stale", "not been contacted", "follow-up", "follow up"]):
            high = any(k in q for k in ["high-value", "high value", "valuable", "high score"])
            d = self.tools.get_leads(stale_days=5, min_score=80 if high else None, min_budget_ngn=150_000_000 if high else None)
            ids = ", ".join(x["lead_id"] for x in d["leads"][:8])
            text = f"I found {d['count']} matching stale leads. Highest-priority records include {ids}."
            return {"text": text, "provider": "offline-demo", "tool": "get_leads", "data": d}

        if "occupancy" in q or ("shortlet" in q and any(k in q for k in ["booking", "weekend", "vacant"])):
            d = self.tools.get_shortlet_bookings("2026-10-02", "2026-10-04")
            text = f"For 2–4 October 2026, {d['booked_units']} of {d['shortlet_units']} shortlet units are booked, giving {d['occupancy_pct']}% occupancy and {money(d['booking_value_ngn'])} in booking value."
            return {"text": text, "provider": "offline-demo", "tool": "get_shortlet_bookings", "data": d}

        if "maintenance" in q and any(k in q for k in ["critical", "48", "unresolved", "open"]):
            d = self.tools.search_company_data("Open", domains=["maintenance"], limit=50)
            rows = [r for r in d.get("results", {}).get("maintenance", []) if r.get("priority") == "Critical" and r.get("status") not in ("Resolved", "Closed")]
            ids = ", ".join(r["ticket_id"] for r in rows)
            text = f"There are {len(rows)} unresolved critical maintenance cases: {ids}."
            return {"text": text, "provider": "offline-demo", "tool": "search_company_data", "data": rows}

        if any(k in q for k in ["construction", "behind schedule", "delayed milestone", "delay"]):
            project_id = "PROJ-001" if any(k in q for k in ["cedarstone park", "park", "proj-001"]) else None
            d = self.tools.get_construction_status(project_id=project_id, delayed_only=True)
            ids = ", ".join(x["milestone_id"] for x in d["milestones"])
            note = d["milestones"][0].get("notes", "") if d["milestones"] else ""
            text = f"I found {d['delayed_count']} delayed/late milestones ({ids}). {note}".strip()
            return {"text": text, "provider": "offline-demo", "tool": "get_construction_status", "data": d}

        if any(k in q for k in ["overdue", "outstanding", "receivable"]):
            d = self.tools.get_outstanding_payments()
            text = f"There are {d['count']} overdue payment plans with {money(d['total_outstanding_ngn'])} outstanding."
            return {"text": text, "provider": "offline-demo", "tool": "get_outstanding_payments", "data": d}

        inv_match = re.search(r"inv-\d{3}", q, re.I)
        if inv_match:
            inv_id = inv_match.group(0).upper()
            d = self.tools.get_investor_summary(inv_id)
            text = f"{d['investor']['investor_name']} ({inv_id}) has {d['investment_count']} recorded investment(s) with total recorded investment value of {money(d['total_investment_value_ngn'])}."
            return {"text": text, "provider": "offline-demo", "tool": "get_investor_summary", "data": d}

        if any(k in q for k in ["available unit", "availability", "units available"]):
            d = self.tools.get_property_availability()
            text = f"There are {d['available_count']} units currently marked Available across CedarStone's unit portfolio."
            return {"text": text, "provider": "offline-demo", "tool": "get_property_availability", "data": d}

        update = re.search(r"(lead-\d{4}).*?(new|contacted|qualified|inspection booked|negotiation|won|lost)", q, re.I)
        if update and any(k in q for k in ["update", "change", "set"]):
            lead_id, status = update.group(1).upper(), update.group(2).title()
            if status.lower() == "inspection booked":
                status = "Inspection Booked"
            d = self.tools.update_lead_status(lead_id, status, "Explicit offline-demo user instruction")
            return {"text": f"{lead_id} was updated from {d['old_status']} to {d['new_status']} in the simulated demo database.", "provider": "offline-demo", "tool": "update_lead_status", "data": d}

        d = self.tools.search_company_data(message, limit=10)
        if d["result_count"]:
            domains = ", ".join(d["results"].keys())
            text = f"I found {d['result_count']} matching record(s) across: {domains}."
        else:
            text = "I could not find a matching CedarStone record. Try a property name, record ID, investor ID, lead question, shortlet question, maintenance issue, construction question, or management briefing."
        return {"text": text, "provider": "offline-demo", "tool": "search_company_data", "data": d}
