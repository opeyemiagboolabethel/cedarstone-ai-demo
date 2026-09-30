from pathlib import Path
import shutil
import tempfile

from agent import CedarStoneAgent
from cedarstone_tools import CedarStoneTools, ToolContext

HERE = Path(__file__).resolve().parent
MASTER = HERE / "CedarStone_AI_Agent_Demo.db"
DB = Path(tempfile.gettempdir()) / "cedarstone_phase8_test.db"
shutil.copy2(MASTER, DB)

exec_tools = CedarStoneTools(DB, ToolContext(employee_id="EMP-001", role="executive"))
brief = exec_tools.generate_management_briefing()
assert brief["metrics"]["target_weekend_occupancy_pct"] == 54.8
assert brief["metrics"]["critical_maintenance_over_48h"] == 3
assert brief["metrics"]["investors_awaiting_updates"] == 4

agent = CedarStoneAgent(role="executive", employee_id="EMP-001", db_path=DB, provider="offline")
assert "54.8" in agent.ask("What is shortlet occupancy for 2-4 October 2026?")["text"]
assert "MAIN-0003" in agent.ask("Show critical maintenance issues open for more than 48 hours")["text"]

sales = CedarStoneTools(DB, ToolContext(employee_id="EMP-006", role="sales"))
lead = sales.get_leads(stale_days=5, min_score=80, min_budget_ngn=150_000_000)
assert lead["count"] >= 4

result = sales.update_lead_status("LEAD-0012", "Negotiation", "Phase 8 QA simulated update")
assert result["new_status"] == "Negotiation"

try:
    sales.get_outstanding_payments()
    raise AssertionError("Sales role should not have finance access")
except PermissionError:
    pass

DB.unlink(missing_ok=True)
print("Phase 8 logic QA passed.")
