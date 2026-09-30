from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
DB = HERE / "CedarStone_AI_Agent_Demo.db"
required = [
    "streamlit_app.py", "agent.py", "cedarstone_tools.py", "offline_agent.py",
    "gemini_provider.py", "prompts.py", "tool_schemas.json", "requirements.txt", DB.name,
]
missing = [name for name in required if not (HERE / name).exists()]
assert not missing, f"Missing deployment files: {missing}"

with sqlite3.connect(DB) as con:
    props = con.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    leads = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    critical = con.execute("SELECT COUNT(*) FROM vw_critical_open_maintenance WHERE hours_open > 48").fetchone()[0]
    investors = con.execute("SELECT COUNT(*) FROM investors WHERE awaiting_update='Yes'").fetchone()[0]

assert props == 5, props
assert leads == 350, leads
assert critical == 3, critical
assert investors == 4, investors
print("Deployment smoke test passed")
print({"properties": props, "leads": leads, "critical_maintenance": critical, "investor_updates": investors})
