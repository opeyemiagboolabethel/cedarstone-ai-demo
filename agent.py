from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from cedarstone_tools import CedarStoneTools, ToolContext
from offline_agent import OfflineDemoAgent

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "CedarStone_AI_Agent_Demo.db"


class CedarStoneAgent:
    def __init__(
        self,
        role: str = "executive",
        employee_id: str = "EMP-001",
        db_path: str | Path = DEFAULT_DB,
        provider: str = "auto",
        gemini_api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.role = role
        self.employee_id = employee_id
        self.tools = CedarStoneTools(db_path, ToolContext(employee_id=employee_id, role=role))
        self.provider_name = provider

        has_key = bool(gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        if provider == "gemini" or (provider == "auto" and has_key):
            try:
                from gemini_provider import GeminiProvider
                kwargs = {"api_key": gemini_api_key}
                if model:
                    kwargs["model"] = model
                self.provider = GeminiProvider(self.tools, **kwargs)
                self.provider_name = "gemini"
            except Exception:
                if provider == "gemini":
                    raise
                self.provider = OfflineDemoAgent(self.tools)
                self.provider_name = "offline-demo"
        else:
            self.provider = OfflineDemoAgent(self.tools)
            self.provider_name = "offline-demo"

    def ask(self, message: str) -> Dict[str, Any]:
        if not message or not message.strip():
            return {"text": "Please enter a CedarStone business question.", "provider": self.provider_name}
        result = self.provider.ask(message.strip())
        result["role"] = self.role
        result["employee_id"] = self.employee_id
        return result
