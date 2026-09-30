
from pathlib import Path
import shutil, tempfile, sqlite3, sys

from agent import CedarStoneAgent
from cedarstone_tools import CedarStoneTools, ToolContext, READ_ROLES

HERE = Path(__file__).resolve().parent
MASTER = HERE / "CedarStone_AI_Agent_Demo.db"
DB = Path(tempfile.gettempdir()) / "cedarstone_phase9_qa.db"
shutil.copy2(MASTER, DB)

passed = 0
failed = 0
results=[]

def check(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        results.append((name, "PASS", ""))
    except Exception as exc:
        failed += 1
        results.append((name, "FAIL", f"{type(exc).__name__}: {exc}"))

def expect_error(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__}")

exec_tools = CedarStoneTools(DB, ToolContext(employee_id="EMP-001", role="executive"))

# Dataset and known-answer tests
check("Executive briefing occupancy", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.generate_management_briefing()["metrics"]["target_weekend_occupancy_pct"] != 54.8 else None)
check("Exactly 3 critical maintenance >48h", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.generate_management_briefing()["metrics"]["critical_maintenance_over_48h"] != 3 else None)
check("Exactly 4 investor updates due", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.generate_management_briefing()["metrics"]["investors_awaiting_updates"] != 4 else None)
check("Overdue receivables total", lambda: (_ for _ in ()).throw(AssertionError()) if round(exec_tools.get_outstanding_payments()["total_outstanding_ngn"]) != 1929562159 else None)
check("CedarStone Park delay surfaced", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.get_construction_status("PROJ-001", True)["delayed_count"] < 2 else None)
check("Investor INV-003 exists", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.get_investor_summary("INV-003")["investment_count"] < 1 else None)
check("Available units returned", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.get_property_availability()["available_count"] <= 0 else None)
check("High-value stale leads returned", lambda: (_ for _ in ()).throw(AssertionError()) if exec_tools.get_leads(stale_days=5,min_score=80,min_budget_ngn=150_000_000)["count"] < 4 else None)

# Offline agent known scenarios
agent = CedarStoneAgent(role="executive", employee_id="EMP-001", db_path=DB, provider="offline")
check("Offline CEO briefing", lambda: (_ for _ in ()).throw(AssertionError()) if "1,929,562,159" not in agent.ask("What requires management attention today?")["text"] else None)
check("Offline occupancy", lambda: (_ for _ in ()).throw(AssertionError()) if "54.8%" not in agent.ask("What is occupancy for 2-4 October 2026?")["text"] else None)
check("Offline maintenance IDs", lambda: (_ for _ in ()).throw(AssertionError()) if "MAIN-0003" not in agent.ask("Show critical maintenance issues open for more than 48 hours")["text"] else None)
check("Offline construction", lambda: (_ for _ in ()).throw(AssertionError()) if "MILE-" not in agent.ask("Why is CedarStone Park behind schedule?")["text"] else None)
check("Offline investor", lambda: (_ for _ in ()).throw(AssertionError()) if "INV-003" not in agent.ask("Summarise INV-003")["text"] else None)

# Context identity/role validation
check("Role/employee mismatch rejected", lambda: expect_error(PermissionError, lambda: CedarStoneTools(DB, ToolContext(employee_id="EMP-006", role="finance"))))
check("Unknown role rejected", lambda: expect_error(PermissionError, lambda: CedarStoneTools(DB, ToolContext(employee_id="EMP-006", role="superuser"))))

# Role read restrictions
sales_head = CedarStoneTools(DB, ToolContext(employee_id="EMP-006", role="sales"))
finance = CedarStoneTools(DB, ToolContext(employee_id="EMP-068", role="finance"))
facilities = CedarStoneTools(DB, ToolContext(employee_id="EMP-044", role="facilities"))
construction = CedarStoneTools(DB, ToolContext(employee_id="EMP-056", role="construction"))
shortlet = CedarStoneTools(DB, ToolContext(employee_id="EMP-034", role="shortlet"))
investor_rel = CedarStoneTools(DB, ToolContext(employee_id="EMP-076", role="investor_relations"))
admin = CedarStoneTools(DB, ToolContext(employee_id="EMP-081", role="admin"))

check("Sales denied finance receivables", lambda: expect_error(PermissionError, lambda: sales_head.get_outstanding_payments()))
check("Facilities denied investor summary", lambda: expect_error(PermissionError, lambda: facilities.get_investor_summary("INV-003")))
check("Construction denied shortlet bookings", lambda: expect_error(PermissionError, lambda: construction.get_shortlet_bookings("2026-10-02","2026-10-04")))
check("Shortlet denied receivables", lambda: expect_error(PermissionError, lambda: shortlet.get_outstanding_payments()))
check("Investor relations allowed investor summary", lambda: investor_rel.get_investor_summary("INV-003"))
check("Finance allowed receivables", lambda: finance.get_outstanding_payments())
check("Admin executive-style read access", lambda: admin.generate_management_briefing())

# Individual sales scope
con=sqlite3.connect(DB)
assigned = con.execute("SELECT lead_id FROM leads WHERE assigned_sales_officer='EMP-008' LIMIT 1").fetchone()
unassigned = con.execute("SELECT lead_id FROM leads WHERE assigned_sales_officer<>'EMP-008' AND lead_status NOT IN ('Won','Lost') LIMIT 1").fetchone()
con.close()
assert assigned and unassigned
sales_exec = CedarStoneTools(DB, ToolContext(employee_id="EMP-008", role="sales"))
check("Sales executive get_leads scoped to own leads", lambda: (_ for _ in ()).throw(AssertionError()) if any(x["assigned_sales_officer"]!="EMP-008" for x in sales_exec.get_leads()["leads"]) else None)
check("Sales executive can update own lead", lambda: sales_exec.update_lead_status(assigned[0], "Qualified", "QA own lead"))
check("Sales executive cannot update another rep's lead", lambda: expect_error(PermissionError, lambda: sales_exec.update_lead_status(unassigned[0], "Qualified", "QA forbidden")))

# Task controls
check("Sales can create task in own department", lambda: sales_head.create_task("DEPT-002","EMP-006","QA sales task","2026-10-02","Medium"))
check("Sales cannot create cross-department task", lambda: expect_error(PermissionError, lambda: sales_head.create_task("DEPT-005","EMP-044","Cross dept attempt","2026-10-02","High")))
check("Mismatched department and assignee rejected", lambda: expect_error(ValueError, lambda: exec_tools.create_task("DEPT-002","EMP-044","Mismatch","2026-10-02","Low")))
check("Executive can create valid cross-department task", lambda: exec_tools.create_task("DEPT-005","EMP-044","Executive facilities task","2026-10-02","High"))

# Maintenance controls
check("Facilities can create maintenance ticket", lambda: facilities.create_maintenance_ticket("PROP-001","UNIT-LH-001","Plumbing","QA plumbing issue","High"))
check("Sales cannot create maintenance ticket", lambda: expect_error(PermissionError, lambda: sales_head.create_maintenance_ticket("PROP-001","UNIT-LH-001","Plumbing","Forbidden","Low")))
check("Wrong property/unit pairing rejected", lambda: expect_error(ValueError, lambda: exec_tools.create_maintenance_ticket("PROP-003","UNIT-LH-001","Electrical","Wrong pair","Medium")))
check("Bad vendor rejected", lambda: expect_error(KeyError, lambda: exec_tools.create_maintenance_ticket("PROP-001","UNIT-LH-001","Electrical","Bad vendor","Medium","VEN-999")))

# Communications
msg = "This exact draft body must persist for Phase 9 QA."
def draft_and_verify():
    r = investor_rel.draft_communication("Investor","INV-003","Email","Phase 9 QA",msg)
    con=sqlite3.connect(DB)
    row=con.execute("SELECT message,status FROM communications WHERE communication_id=?",(r["communication_id"],)).fetchone()
    con.close()
    assert row == (msg,"Draft")
check("Draft message body persists", draft_and_verify)
check("Sales cannot draft to investor", lambda: expect_error(PermissionError, lambda: sales_head.draft_communication("Investor","INV-003","Email","No","Not allowed")))
check("Invalid recipient ID rejected", lambda: expect_error(KeyError, lambda: investor_rel.draft_communication("Investor","INV-999","Email","Bad","Bad")))
check("Blank draft rejected", lambda: expect_error(ValueError, lambda: investor_rel.draft_communication("Investor","INV-003","Email","","")))

# Audit logging
def audit_check():
    con=sqlite3.connect(DB)
    n=con.execute("SELECT COUNT(*) FROM ai_activity_log").fetchone()[0]
    con.close()
    assert n >= 5
check("Write actions generate audit records", audit_check)

# Search permissions
def search_sales():
    d=sales_head.search_company_data("INV-003",domains=["investors","leads"])
    assert "investors" not in d["results"]
check("Generic search skips unauthorized domain", search_sales)

# Data integrity / row counts
def integrity():
    con=sqlite3.connect(DB)
    counts={
        "employees":85,"properties":5,"units":230,"leads":350
    }
    for table,expected in counts.items():
        got=con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert got==expected,(table,got,expected)
    con.close()
check("Core master row counts stable", integrity)

print(f"PASS={passed} FAIL={failed} TOTAL={passed+failed}")
for name,status,detail in results:
    print(f"{status}\t{name}" + (f"\t{detail}" if detail else ""))

DB.unlink(missing_ok=True)
if failed:
    sys.exit(1)
