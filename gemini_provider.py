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
    def search_company_data(query: str, limit: int = 20) -> dict:
        return _safe(tools.search_company_data, query=query, limit=limit)

    def get_property_availability(property_id: str = "", unit_type: str = "", max_price_ngn: float = 0) -> dict:
        return _safe(
            tools.get_property_availability,
            property_id=property_id or None,
            unit_type=unit_type or None,
            max_price_ngn=max_price_ngn if max_price_ngn > 0 else None,
        )

    def get_leads(status: str = "", stale_days: int = 0, min_score: int = 0, min_budget_ngn: float = 0, assigned_employee_id: str = "") -> dict:
        return _safe(
            tools.get_leads,
            status=status or None,
            stale_days=stale_days if stale_days > 0 else None,
            min_score=min_score if min_score > 0 else None,
            min_budget_ngn=min_budget_ngn if min_budget_ngn > 0 else None,
            assigned_employee_id=assigned_employee_id or None,
        )

    def update_lead_status(lead_id: str, new_status: str, note: str = "Updated by CedarStone AI demo") -> dict:
        return _safe(tools.update_lead_status, lead_id=lead_id, new_status=new_status, note=note, commit=True)

    def create_task(department_id: str, assigned_employee_id: str, description: str, due_date: str, priority: str = "Medium") -> dict:
        return _safe(
            tools.create_task,
            department_id=department_id,
            assigned_employee_id=assigned_employee_id,
            description=description,
            due_date=due_date,
            priority=priority,
            commit=True,
        )

    def create_maintenance_ticket(property_id: str, unit_id: str, issue_type: str, description: str, priority: str = "Medium", assigned_vendor_id: str = "") -> dict:
        return _safe(
            tools.create_maintenance_ticket,
            property_id=property_id,
            unit_id=unit_id,
            issue_type=issue_type,
            description=description,
            priority=priority,
            assigned_vendor_id=assigned_vendor_id or None,
            commit=True,
        )

    def get_shortlet_bookings(start_date: str, end_date: str, property_id: str = "") -> dict:
        return _safe(tools.get_shortlet_bookings, start_date=start_date, end_date=end_date, property_id=property_id or None)

    def get_investor_summary(investor_id: str) -> dict:
        return _safe(tools.get_investor_summary, investor_id=investor_id)

    def get_outstanding_payments(min_amount_ngn: float = 0, overdue_only: bool = True) -> dict:
        return _safe(tools.get_outstanding_payments, min_amount_ngn=min_amount_ngn, overdue_only=overdue_only)

    def get_construction_status(project_id: str = "", delayed_only: bool = False) -> dict:
        return _safe(tools.get_construction_status, project_id=project_id or None, delayed_only=delayed_only)

    def generate_management_briefing() -> dict:
        return _safe(tools.generate_management_briefing)

    def draft_communication(entity_type: str, entity_id: str, channel: str, subject: str, message: str) -> dict:
        return _safe(
            tools.draft_communication,
            entity_type=entity_type,
            entity_id=entity_id,
            channel=channel,
            subject=subject,
            message=message,
            commit=True,
        )

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


def build_tool_declarations(types):
    def fn(name: str, description: str, properties: dict, required: Optional[List[str]] = None):
        schema = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return types.FunctionDeclaration(
            name=name,
            description=description,
            parameters_json_schema=schema,
        )

    declarations = [
        fn(
            "search_company_data",
            "Search CedarStone business records for a term, name or record ID.",
            {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            ["query"],
        ),
        fn(
            "get_property_availability",
            "Find currently available property units using optional property, unit-type and maximum-price filters.",
            {
                "property_id": {"type": "string"},
                "unit_type": {"type": "string"},
                "max_price_ngn": {"type": "number"},
            },
        ),
        fn(
            "get_leads",
            "Search and analyse CedarStone sales leads, including stale, high-score and high-value leads.",
            {
                "status": {"type": "string"},
                "stale_days": {"type": "integer"},
                "min_score": {"type": "integer"},
                "min_budget_ngn": {"type": "number"},
                "assigned_employee_id": {"type": "string"},
            },
        ),
        fn(
            "update_lead_status",
            "Update a lead's status in the simulated CedarStone environment. Use only on explicit user instruction.",
            {
                "lead_id": {"type": "string"},
                "new_status": {"type": "string"},
                "note": {"type": "string"},
            },
            ["lead_id", "new_status"],
        ),
        fn(
            "create_task",
            "Create a simulated internal CedarStone task. Use only on explicit user instruction. The assigned employee must belong to the selected department.",
            {
                "department_id": {"type": "string"},
                "assigned_employee_id": {"type": "string"},
                "description": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "priority": {"type": "string", "enum": ["Low", "Medium", "High"]},
            },
            ["department_id", "assigned_employee_id", "description", "due_date"],
        ),
        fn(
            "create_maintenance_ticket",
            "Create a simulated facilities maintenance ticket. Use only on explicit user instruction.",
            {
                "property_id": {"type": "string"},
                "unit_id": {"type": "string"},
                "issue_type": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                "assigned_vendor_id": {"type": "string"},
            },
            ["property_id", "unit_id", "issue_type", "description"],
        ),
        fn(
            "get_shortlet_bookings",
            "Calculate shortlet occupancy and booking value for a date range.",
            {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "property_id": {"type": "string"},
            },
            ["start_date", "end_date"],
        ),
        fn(
            "get_investor_summary",
            "Return an investor profile and their connected CedarStone investments.",
            {"investor_id": {"type": "string"}},
            ["investor_id"],
        ),
        fn(
            "get_outstanding_payments",
            "Analyse outstanding or overdue property-payment plans.",
            {
                "min_amount_ngn": {"type": "number"},
                "overdue_only": {"type": "boolean"},
            },
        ),
        fn(
            "get_construction_status",
            "Return construction project and milestone status, including delays.",
            {
                "project_id": {"type": "string"},
                "delayed_only": {"type": "boolean"},
            },
        ),
        fn(
            "generate_management_briefing",
            "Generate a cross-department CedarStone management briefing using current demo records.",
            {},
        ),
        fn(
            "draft_communication",
            "Create a draft-only communication in the demo. This never sends a real message.",
            {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "string"},
                "channel": {"type": "string"},
                "subject": {"type": "string"},
                "message": {"type": "string"},
            },
            ["entity_type", "entity_id", "channel", "subject", "message"],
        ),
    ]
    return types.Tool(function_declarations=declarations)


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
        self.function_map = {fn.__name__: fn for fn in self.functions}
        self.tool = build_tool_declarations(types)
        self.history: List[Dict[str, str]] = []

    def _config(self):
        return self._types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.tool],
        )

    def ask(self, message: str) -> Dict[str, Any]:
        history_text = ""
        if self.history:
            history_text = "\nRecent conversation:\n" + "\n".join(
                f"{h['role'].upper()}: {h['content']}" for h in self.history[-8:]
            ) + "\n"

        prompt = history_text + "\nCURRENT USER REQUEST:\n" + message
        contents = [
            self._types.Content(
                role="user",
                parts=[self._types.Part.from_text(text=prompt)],
            )
        ]

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self._config(),
        )

        for _ in range(8):
            calls = list(response.function_calls or [])
            if not calls:
                break

            if response.candidates and response.candidates[0].content is not None:
                contents.append(response.candidates[0].content)

            tool_parts = []
            for call in calls:
                name = call.name or ""
                args = dict(call.args or {})
                fn = self.function_map.get(name)

                if fn is None:
                    function_response = {"error": f"Unknown CedarStone tool: {name}"}
                else:
                    try:
                        result = fn(**args)
                        function_response = {"result": result}
                    except Exception as exc:
                        function_response = {
                            "error": f"Tool execution failed: {type(exc).__name__}: {exc}"
                        }

                tool_parts.append(
                    self._types.Part.from_function_response(
                        name=name,
                        response=function_response,
                    )
                )

            contents.append(self._types.Content(role="tool", parts=tool_parts))
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=self._config(),
            )

        text = (response.text or "").strip()
        if not text:
            text = "The request was processed, but Gemini returned no final text response."

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": text})
        return {"text": text, "provider": "gemini", "model": self.model}
