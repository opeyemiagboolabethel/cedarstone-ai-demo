from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from prompts import SYSTEM_PROMPT
from cedarstone_tools import CedarStoneTools

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _safe(fn: Callable[..., Any], **kwargs: Any) -> Dict[str, Any]:
    try:
        return {"ok": True, "data": fn(**kwargs)}
    except (PermissionError, ValueError, KeyError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"Tool execution failed: {type(exc).__name__}: {exc}"}


def build_tool_functions(tools: CedarStoneTools) -> List[Callable[..., Dict[str, Any]]]:
    # Simple, typed wrappers are intentionally used because the Google GenAI SDK
    # automatically converts Python callables into function declarations.
    def search_company_data(query: str, limit: int = 20) -> dict:
        """Search CedarStone business records for a term, name or record ID."""
        return _safe(tools.search_company_data, query=query, limit=limit)

    def get_property_availability(property_id: str = "", unit_type: str = "", max_price_ngn: float = 0) -> dict:
        """Find currently available property units using optional property, unit-type and maximum-price filters."""
        return _safe(
            tools.get_property_availability,
            property_id=property_id or None,
            unit_type=unit_type or None,
            max_price_ngn=max_price_ngn if max_price_ngn > 0 else None,
        )

    def get_leads(status: str = "", stale_days: int = 0, min_score: int = 0, min_budget_ngn: float = 0, assigned_employee_id: str = "") -> dict:
        """Search and analyse CedarStone sales leads, including stale, high-score and high-value leads."""
        return _safe(
            tools.get_leads,
            status=status or None,
            stale_days=stale_days if stale_days > 0 else None,
            min_score=min_score if min_score > 0 else None,
            min_budget_ngn=min_budget_ngn if min_budget_ngn > 0 else None,
            assigned_employee_id=assigned_employee_id or None,
        )

    def update_lead_status(lead_id: str, new_status: str, note: str = "Updated by CedarStone AI demo") -> dict:
        """Update a lead's status in the simulated CedarStone environment. Use only on explicit user instruction."""
        return _safe(tools.update_lead_status, lead_id=lead_id, new_status=new_status, note=note, commit=True)

    def create_task(department_id: str, assigned_employee_id: str, description: str, due_date: str, priority: str = "Medium") -> dict:
        """Create a simulated internal CedarStone task. Use only on explicit user instruction."""
        return _safe(tools.create_task, department_id=department_id, assigned_employee_id=assigned_employee_id, description=description, due_date=due_date, priority=priority, commit=True)

    def create_maintenance_ticket(property_id: str, unit_id: str, issue_type: str, description: str, priority: str = "Medium", assigned_vendor_id: str = "") -> dict:
        """Create a simulated facilities maintenance ticket. Use only on explicit user instruction."""
        return _safe(tools.create_maintenance_ticket, property_id=property_id, unit_id=unit_id, issue_type=issue_type, description=description, priority=priority, assigned_vendor_id=assigned_vendor_id or None, commit=True)

    def get_shortlet_bookings(start_date: str, end_date: str, property_id: str = "") -> dict:
        """Calculate shortlet occupancy and booking value for a date range."""
        return _safe(tools.get_shortlet_bookings, start_date=start_date, end_date=end_date, property_id=property_id or None)

    def get_investor_summary(investor_id: str) -> dict:
        """Return an investor profile and their connected CedarStone investments."""
        return _safe(tools.get_investor_summary, investor_id=investor_id)

    def get_outstanding_payments(min_amount_ngn: float = 0, overdue_only: bool = True) -> dict:
        """Analyse outstanding or overdue property-payment plans."""
        return _safe(tools.get_outstanding_payments, min_amount_ngn=min_amount_ngn, overdue_only=overdue_only)

    def get_construction_status(project_id: str = "", delayed_only: bool = False) -> dict:
        """Return construction project and milestone status, including delays."""
        return _safe(tools.get_construction_status, project_id=project_id or None, delayed_only=delayed_only)

    def generate_management_briefing() -> dict:
        """Generate a cross-department CedarStone management briefing using current demo records."""
        return _safe(tools.generate_management_briefing)

    def draft_communication(entity_type: str, entity_id: str, channel: str, subject: str, message: str) -> dict:
        """Create a draft-only communication in the demo. This never sends a real message."""
        return _safe(tools.draft_communication, entity_type=entity_type, entity_id=entity_id, channel=channel, subject=subject, message=message, commit=True)

    return [
        search_company_data,
        get_property_availability,
        get_leads,
        update_lead_status,
        create_task,
        create_maintenance_ticket,
        get_shortlet_bookings,
        get_investor_summary,
        get_outstanding_payments,
        get_construction_status,
        generate_management_briefing,
        draft_communication,
    ]


class GeminiProvider:
    def __init__(self, tools: CedarStoneTools, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed. Run: pip install -r requirements.txt") from exc

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("No Gemini API key found. Set GEMINI_API_KEY in your environment.")

        self._types = types
        self.client = genai.Client(api_key=key)
        self.model = model
        self.functions = build_tool_functions(tools)
        self.history: List[Dict[str, str]] = []

    def ask(self, message: str) -> Dict[str, Any]:
        # Keep a compact conversational trace in the prompt. Tool execution itself
        # is handled automatically by google-genai.
        history_text = ""
        if self.history:
            history_text = "\nRecent conversation:\n" + "\n".join(
                f"{h['role'].upper()}: {h['content']}" for h in self.history[-8:]
            ) + "\n"
        prompt = history_text + "\nCURRENT USER REQUEST:\n" + message
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=self.functions,
            ),
        )
        text = (response.text or "").strip()
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": text})
        return {"text": text, "provider": "gemini", "model": self.model}
