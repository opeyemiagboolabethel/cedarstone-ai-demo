from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_DB = Path(__file__).with_name("CedarStone_AI_Agent_Tools_Demo.db")
AS_OF = datetime(2026, 9, 30, 23, 59, 59)

READ_ROLES = {
    "executive": {"*"},
    "admin": {"*"},
    "sales": {"leads", "lead_activities", "properties", "units", "customers", "sales", "tasks", "communications"},
    "finance": {"customers", "sales", "payment_plans", "payments", "investors", "investments", "properties", "units", "tasks"},
    "investor_relations": {"investors", "investments", "properties", "units", "payments", "payment_plans", "communications", "tasks"},
    "facilities": {"properties", "units", "maintenance", "vendors", "tasks", "documents"},
    "construction": {"properties", "construction", "milestones", "project_expenses", "vendors", "tasks", "documents"},
    "shortlet": {"properties", "units", "bookings", "guests", "maintenance", "tasks", "communications"},
}

WRITE_CAPABILITIES = {
    "executive": {"update_lead", "create_task", "create_maintenance", "draft_communication"},
    "admin": {"create_task", "draft_communication"},
    "sales": {"update_lead", "create_task", "draft_communication"},
    "finance": {"create_task", "draft_communication"},
    "investor_relations": {"create_task", "draft_communication"},
    "facilities": {"create_task", "create_maintenance", "draft_communication"},
    "construction": {"create_task", "draft_communication"},
    "shortlet": {"create_task", "create_maintenance", "draft_communication"},
}

ROLE_DEPARTMENTS = {
    "executive": "DEPT-001",
    "sales": "DEPT-002",
    "shortlet": "DEPT-004",
    "facilities": "DEPT-005",
    "construction": "DEPT-006",
    "finance": "DEPT-007",
    "investor_relations": "DEPT-008",
    "admin": "DEPT-009",
}

COMMUNICATION_ENTITY_ACCESS = {
    "executive": {"Lead", "Customer", "Investor", "Guest"},
    "admin": {"Lead", "Customer", "Investor", "Guest"},
    "sales": {"Lead", "Customer"},
    "finance": {"Customer", "Investor"},
    "investor_relations": {"Investor"},
    "facilities": {"Customer", "Guest"},
    "construction": {"Investor"},
    "shortlet": {"Guest", "Customer"},
}

@dataclass
class ToolContext:
    employee_id: str = "EMP-001"
    role: str = "executive"

class CedarStoneTools:
    """Model-agnostic business tools for the CedarStone AI demo."""

    def __init__(self, db_path: str | Path = DEFAULT_DB, context: Optional[ToolContext] = None):
        self.db_path = str(db_path)
        self.context = context or ToolContext()
        self._validate_context()

    def _validate_context(self) -> None:
        if self.context.role not in READ_ROLES:
            raise PermissionError(f"Unknown CedarStone role: {self.context.role}")
        expected_dept = ROLE_DEPARTMENTS.get(self.context.role)
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT department_id,status FROM employees WHERE employee_id=?", (self.context.employee_id,)).fetchone()
        if not row:
            raise PermissionError(f"Unknown employee: {self.context.employee_id}")
        if row["status"] != "Active":
            raise PermissionError(f"Employee {self.context.employee_id} is not active.")
        if expected_dept and row["department_id"] != expected_dept:
            raise PermissionError(
                f"Employee {self.context.employee_id} does not belong to the department required for role '{self.context.role}'."
            )

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _allowed(self, table: str) -> bool:
        role_tables = READ_ROLES.get(self.context.role, set())
        return "*" in role_tables or table in role_tables

    def _require_read(self, *tables: str) -> None:
        denied = [t for t in tables if not self._allowed(t)]
        if denied:
            raise PermissionError(f"Role '{self.context.role}' cannot access: {', '.join(denied)}")

    def _require_write(self, capability: str) -> None:
        if capability not in WRITE_CAPABILITIES.get(self.context.role, set()):
            raise PermissionError(f"Role '{self.context.role}' cannot perform '{capability}'")

    def _employee_role(self, con: sqlite3.Connection) -> str:
        row = con.execute("SELECT role FROM employees WHERE employee_id=?", (self.context.employee_id,)).fetchone()
        return str(row["role"]) if row else ""

    def _sales_has_team_scope(self, con: sqlite3.Connection) -> bool:
        if self.context.role != "sales":
            return True
        role_name = self._employee_role(con).lower()
        return any(token in role_name for token in ("head", "manager", "crm officer"))

    @staticmethod
    def _rows(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
        return [dict(r) for r in rows]

    @staticmethod
    def _next_id(con: sqlite3.Connection, table: str, id_col: str, prefix: str, width: int = 4) -> str:
        rows = con.execute(f"SELECT {id_col} FROM {table} WHERE {id_col} LIKE ?", (f"{prefix}%",)).fetchall()
        nums = []
        for r in rows:
            try:
                nums.append(int(str(r[0]).split("-")[-1]))
            except Exception:
                continue
        return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"

    def _audit(self, con: sqlite3.Connection, request: str, action_type: str, records_affected: str, outcome: str = "Success") -> str:
        log_id = self._next_id(con, "ai_activity_log", "log_id", "AILOG-", 4)
        con.execute(
            "INSERT INTO ai_activity_log (log_id,user_employee_id,request,action_type,records_affected,outcome,timestamp) VALUES (?,?,?,?,?,?,?)",
            (log_id, self.context.employee_id, request, action_type, records_affected, outcome, datetime.now().isoformat(timespec="seconds")),
        )
        return log_id

    # 1. Generic, whitelist-based company search
    def search_company_data(self, query: str, domains: Optional[List[str]] = None, limit: int = 20) -> Dict[str, Any]:
        domains = domains or ["properties", "units", "leads", "customers", "investors", "bookings", "maintenance", "construction", "milestones"]
        limit = max(1, min(int(limit), 50))
        q = f"%{query.strip()}%"
        results: Dict[str, List[Dict[str, Any]]] = {}
        with self._conn() as con:
            for domain in domains:
                if not self._allowed(domain):
                    continue
                if domain == "properties":
                    sql = "SELECT * FROM properties WHERE property_name LIKE ? OR location LIKE ? OR property_type LIKE ? LIMIT ?"
                    rows = con.execute(sql, (q, q, q, limit)).fetchall()
                elif domain == "units":
                    sql = "SELECT * FROM units WHERE unit_id LIKE ? OR unit_number LIKE ? OR unit_type LIKE ? OR unit_status LIKE ? LIMIT ?"
                    rows = con.execute(sql, (q, q, q, q, limit)).fetchall()
                elif domain == "leads":
                    sql = "SELECT * FROM leads WHERE lead_id LIKE ? OR full_name LIKE ? OR lead_status LIKE ? OR lead_source LIKE ? LIMIT ?"
                    rows = con.execute(sql, (q, q, q, q, limit)).fetchall()
                elif domain == "customers":
                    rows = con.execute("SELECT * FROM customers WHERE customer_id LIKE ? OR full_name LIKE ? LIMIT ?", (q, q, limit)).fetchall()
                elif domain == "investors":
                    rows = con.execute("SELECT * FROM investors WHERE investor_id LIKE ? OR investor_name LIKE ? LIMIT ?", (q, q, limit)).fetchall()
                elif domain == "bookings":
                    rows = con.execute("SELECT * FROM bookings WHERE booking_id LIKE ? OR booking_status LIKE ? OR payment_status LIKE ? LIMIT ?", (q, q, q, limit)).fetchall()
                elif domain == "maintenance":
                    rows = con.execute("SELECT * FROM maintenance WHERE ticket_id LIKE ? OR issue_type LIKE ? OR status LIKE ? OR description LIKE ? LIMIT ?", (q, q, q, q, limit)).fetchall()
                elif domain == "construction":
                    rows = con.execute("SELECT * FROM construction WHERE project_id LIKE ? OR project_name LIKE ? OR status LIKE ? LIMIT ?", (q, q, q, limit)).fetchall()
                elif domain == "milestones":
                    rows = con.execute("SELECT * FROM milestones WHERE milestone_id LIKE ? OR milestone_name LIKE ? OR status LIKE ? OR notes LIKE ? LIMIT ?", (q, q, q, q, limit)).fetchall()
                else:
                    continue
                if rows:
                    results[domain] = self._rows(rows)
        return {"query": query, "results": results, "result_count": sum(len(v) for v in results.values())}

    # 2. Property/unit availability
    def get_property_availability(self, property_id: Optional[str] = None, unit_type: Optional[str] = None, max_price_ngn: Optional[float] = None) -> Dict[str, Any]:
        self._require_read("properties", "units")
        sql = """
        SELECT u.unit_id,u.unit_number,u.unit_type,u.bedrooms,u.selling_price_ngn,u.unit_status,
               u.shortlet_enabled,p.property_id,p.property_name,p.location
        FROM units u JOIN properties p ON p.property_id=u.property_id
        WHERE u.unit_status='Available'
        """
        params: List[Any] = []
        if property_id:
            sql += " AND u.property_id=?"; params.append(property_id)
        if unit_type:
            sql += " AND u.unit_type LIKE ?"; params.append(f"%{unit_type}%")
        if max_price_ngn is not None:
            sql += " AND u.selling_price_ngn<=?"; params.append(float(max_price_ngn))
        sql += " ORDER BY u.selling_price_ngn ASC"
        with self._conn() as con:
            rows = self._rows(con.execute(sql, params).fetchall())
        return {"available_count": len(rows), "units": rows}

    # 3. Lead search / stale lead detection
    def get_leads(self, status: Optional[str] = None, stale_days: Optional[int] = None, min_score: Optional[int] = None, min_budget_ngn: Optional[float] = None, assigned_employee_id: Optional[str] = None) -> Dict[str, Any]:
        self._require_read("leads")
        sql = "SELECT l.*, p.property_name, e.full_name AS sales_officer_name FROM leads l LEFT JOIN properties p ON p.property_id=l.interested_property_id LEFT JOIN employees e ON e.employee_id=l.assigned_sales_officer WHERE 1=1"
        params: List[Any] = []
        if status:
            sql += " AND l.lead_status=?"; params.append(status)
        if stale_days is not None:
            cutoff = (AS_OF.date()).isoformat()
            sql += " AND l.lead_status NOT IN ('Won','Lost') AND julianday(?) - julianday(date(l.last_contact_date)) > ?"
            params.extend([cutoff, int(stale_days)])
        if min_score is not None:
            sql += " AND l.lead_score>=?"; params.append(int(min_score))
        if min_budget_ngn is not None:
            sql += " AND l.budget_ngn>=?"; params.append(float(min_budget_ngn))
        with self._conn() as con:
            effective_assignee = assigned_employee_id
            if self.context.role == "sales" and not self._sales_has_team_scope(con):
                effective_assignee = self.context.employee_id
            if effective_assignee:
                sql += " AND l.assigned_sales_officer=?"; params.append(effective_assignee)
            sql += " ORDER BY l.lead_score DESC, l.budget_ngn DESC LIMIT 100"
            rows = self._rows(con.execute(sql, params).fetchall())
        return {"count": len(rows), "leads": rows}

    # 4. Safe lead status update
    def update_lead_status(self, lead_id: str, new_status: str, note: str = "Updated by CedarStone AI demo", commit: bool = True) -> Dict[str, Any]:
        self._require_write("update_lead")
        allowed = {"New", "Contacted", "Qualified", "Inspection Booked", "Negotiation", "Won", "Lost"}
        if new_status not in allowed:
            raise ValueError(f"Invalid lead status. Allowed: {sorted(allowed)}")
        with self._conn() as con:
            row = con.execute("SELECT lead_id,lead_status,assigned_sales_officer FROM leads WHERE lead_id=?", (lead_id,)).fetchone()
            if not row:
                raise KeyError(f"Lead not found: {lead_id}")
            before = row["lead_status"]
            if self.context.role == "sales" and not self._sales_has_team_scope(con):
                if row["assigned_sales_officer"] != self.context.employee_id:
                    raise PermissionError("This sales user can update only leads assigned to them.")
            if commit:
                con.execute("UPDATE leads SET lead_status=?, last_contact_date=? WHERE lead_id=?", (new_status, AS_OF.isoformat(sep=" "), lead_id))
                act_id = self._next_id(con, "lead_activities", "activity_id", "ACT-", 5)
                con.execute("INSERT INTO lead_activities (activity_id,lead_id,activity_date,channel,activity_type,outcome,employee_id) VALUES (?,?,?,?,?,?,?)",
                            (act_id, lead_id, AS_OF.isoformat(sep=" "), "AI Assisted", "Status update", note, self.context.employee_id))
                log_id = self._audit(con, f"Update {lead_id} from {before} to {new_status}", "Update lead", lead_id)
                con.commit()
            else:
                act_id = log_id = None
        return {"lead_id": lead_id, "old_status": before, "new_status": new_status, "committed": commit, "activity_id": act_id, "audit_log_id": log_id}

    # 5. Create internal task
    def create_task(self, department_id: str, assigned_employee_id: str, description: str, due_date: str, priority: str = "Medium", commit: bool = True) -> Dict[str, Any]:
        self._require_write("create_task")
        if priority not in {"Low", "Medium", "High"}:
            raise ValueError("priority must be Low, Medium, or High")
        with self._conn() as con:
            if not con.execute("SELECT 1 FROM departments WHERE department_id=?", (department_id,)).fetchone():
                raise KeyError(f"Department not found: {department_id}")
            emp = con.execute("SELECT department_id FROM employees WHERE employee_id=?", (assigned_employee_id,)).fetchone()
            if not emp:
                raise KeyError(f"Employee not found: {assigned_employee_id}")
            if emp["department_id"] != department_id:
                raise ValueError("assigned_employee_id must belong to department_id")
            allowed_dept = ROLE_DEPARTMENTS.get(self.context.role)
            if self.context.role not in {"executive", "admin"} and allowed_dept and department_id != allowed_dept:
                raise PermissionError(f"Role '{self.context.role}' can create tasks only within {allowed_dept}.")
            task_id = self._next_id(con, "tasks", "task_id", "TASK-", 4)
            if commit:
                con.execute("INSERT INTO tasks (task_id,department_id,assigned_employee_id,task_description,created_date,due_date,priority,status,source) VALUES (?,?,?,?,?,?,?,?,?)",
                            (task_id, department_id, assigned_employee_id, description, AS_OF.isoformat(sep=" "), due_date, priority, "Open", "AI"))
                log_id = self._audit(con, f"Create task: {description}", "Create task", task_id)
                con.commit()
            else:
                log_id = None
        return {"task_id": task_id, "department_id": department_id, "assigned_employee_id": assigned_employee_id, "description": description, "due_date": due_date, "priority": priority, "committed": commit, "audit_log_id": log_id}

    # 6. Create maintenance ticket
    def create_maintenance_ticket(self, property_id: str, unit_id: str, issue_type: str, description: str, priority: str = "Medium", assigned_vendor_id: Optional[str] = None, commit: bool = True) -> Dict[str, Any]:
        self._require_write("create_maintenance")
        if priority not in {"Low", "Medium", "High", "Critical"}:
            raise ValueError("Invalid maintenance priority")
        with self._conn() as con:
            unit = con.execute("SELECT property_id FROM units WHERE unit_id=?", (unit_id,)).fetchone()
            if not unit:
                raise KeyError(f"Unit not found: {unit_id}")
            if unit["property_id"] != property_id:
                raise ValueError("unit_id does not belong to property_id")
            if assigned_vendor_id and not con.execute("SELECT 1 FROM vendors WHERE vendor_id=?", (assigned_vendor_id,)).fetchone():
                raise KeyError(f"Vendor not found: {assigned_vendor_id}")
            ticket_id = self._next_id(con, "maintenance", "ticket_id", "MAIN-", 4)
            if commit:
                con.execute("INSERT INTO maintenance (ticket_id,property_id,unit_id,issue_type,description,priority,reported_date,assigned_vendor_id,assigned_employee_id,status,resolution_date,estimated_cost_ngn,actual_cost_ngn) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ticket_id, property_id, unit_id, issue_type, description, priority, AS_OF.isoformat(sep=" "), assigned_vendor_id, self.context.employee_id, "Open", None, None, None))
                log_id = self._audit(con, f"Create maintenance ticket: {issue_type}", "Create maintenance ticket", ticket_id)
                con.commit()
            else:
                log_id = None
        return {"ticket_id": ticket_id, "property_id": property_id, "unit_id": unit_id, "priority": priority, "status": "Open", "committed": commit, "audit_log_id": log_id}

    # 7. Shortlet booking search / occupancy
    def get_shortlet_bookings(self, start_date: str, end_date: str, property_id: Optional[str] = None) -> Dict[str, Any]:
        self._require_read("bookings", "units", "properties")
        sql_units = "SELECT COUNT(*) FROM units WHERE shortlet_enabled='Yes'"
        unit_params: List[Any] = []
        if property_id:
            sql_units += " AND property_id=?"; unit_params.append(property_id)
        sql_bookings = """
        SELECT b.*,u.unit_number,u.property_id,p.property_name,g.full_name AS guest_name
        FROM bookings b
        JOIN units u ON u.unit_id=b.unit_id
        JOIN properties p ON p.property_id=u.property_id
        LEFT JOIN guests g ON g.guest_id=b.guest_id
        WHERE u.shortlet_enabled='Yes'
          AND b.booking_status IN ('Confirmed','Completed')
          AND date(b.check_in) < date(?)
          AND date(b.check_out) > date(?)
        """
        params: List[Any] = [end_date, start_date]
        if property_id:
            sql_bookings += " AND u.property_id=?"; params.append(property_id)
        with self._conn() as con:
            total_units = con.execute(sql_units, unit_params).fetchone()[0]
            rows = self._rows(con.execute(sql_bookings, params).fetchall())
        booked_units = len(set(r["unit_id"] for r in rows))
        occupancy = round((booked_units / total_units * 100), 1) if total_units else 0
        revenue = sum(float(r.get("total_amount_ngn") or 0) for r in rows)
        return {"start_date": start_date, "end_date": end_date, "shortlet_units": total_units, "booked_units": booked_units, "occupancy_pct": occupancy, "booking_value_ngn": revenue, "bookings": rows}

    # 8. Investor summary
    def get_investor_summary(self, investor_id: str) -> Dict[str, Any]:
        self._require_read("investors", "investments", "units", "properties")
        with self._conn() as con:
            inv = con.execute("SELECT * FROM investors WHERE investor_id=?", (investor_id,)).fetchone()
            if not inv:
                raise KeyError(f"Investor not found: {investor_id}")
            assets = self._rows(con.execute("""
                SELECT i.investment_id,i.investment_value_ngn,i.investment_date,i.investment_model,i.status,
                       u.unit_id,u.unit_number,u.unit_type,u.shortlet_enabled,p.property_name,p.location
                FROM investments i
                LEFT JOIN units u ON u.unit_id=i.unit_id
                LEFT JOIN properties p ON p.property_id=i.property_id
                WHERE i.investor_id=? ORDER BY i.investment_date
            """, (investor_id,)).fetchall())
        return {"investor": dict(inv), "investment_count": len(assets), "total_investment_value_ngn": sum(float(a.get("investment_value_ngn") or 0) for a in assets), "investments": assets}

    # 9. Outstanding payment analysis
    def get_outstanding_payments(self, min_amount_ngn: float = 0, overdue_only: bool = True) -> Dict[str, Any]:
        self._require_read("customers", "sales", "payment_plans")
        sql = "SELECT * FROM vw_overdue_receivables WHERE outstanding_ngn>=?" if overdue_only else """
        SELECT pp.plan_id,s.sale_id,c.customer_id,c.full_name AS customer_name,p.property_name,
               COALESCE(u.unit_number,lp.plot_number) AS asset_number,
               pp.total_due_ngn,pp.paid_to_date_ngn,pp.outstanding_ngn,pp.final_due_date,
               CASE WHEN date(pp.final_due_date)<'2026-09-30' THEN CAST(julianday('2026-09-30')-julianday(pp.final_due_date) AS INTEGER) ELSE 0 END AS days_overdue
        FROM payment_plans pp JOIN sales s ON s.sale_id=pp.sale_id JOIN customers c ON c.customer_id=s.customer_id
        JOIN properties p ON p.property_id=s.property_id LEFT JOIN units u ON u.unit_id=s.unit_id LEFT JOIN land_plots lp ON lp.plot_id=s.plot_id
        WHERE pp.outstanding_ngn>=?
        """
        with self._conn() as con:
            rows = self._rows(con.execute(sql, (float(min_amount_ngn),)).fetchall())
        return {"count": len(rows), "total_outstanding_ngn": sum(float(r.get("outstanding_ngn") or 0) for r in rows), "records": rows}

    # 10. Construction/milestone analysis
    def get_construction_status(self, project_id: Optional[str] = None, delayed_only: bool = False) -> Dict[str, Any]:
        self._require_read("construction", "milestones")
        with self._conn() as con:
            if delayed_only:
                sql = "SELECT * FROM vw_delayed_milestones" + (" WHERE project_id=?" if project_id else "")
                rows = self._rows(con.execute(sql, (project_id,) if project_id else ()).fetchall())
                return {"delayed_count": len(rows), "milestones": rows}
            sql = "SELECT * FROM construction" + (" WHERE project_id=?" if project_id else "")
            projects = self._rows(con.execute(sql, (project_id,) if project_id else ()).fetchall())
            out=[]
            for p in projects:
                ms=self._rows(con.execute("SELECT * FROM milestones WHERE project_id=? ORDER BY planned_completion_date", (p["project_id"],)).fetchall())
                p["milestones"]=ms
                p["delayed_milestones"]=[m for m in ms if m["status"]=="Delayed"]
                out.append(p)
        return {"project_count": len(out), "projects": out}

    # 11. Executive briefing
    def generate_management_briefing(self) -> Dict[str, Any]:
        self._require_read("leads", "payment_plans", "maintenance", "construction", "milestones", "bookings", "units", "investors")
        with self._conn() as con:
            stale = con.execute("SELECT COUNT(*) FROM vw_stale_leads").fetchone()[0]
            high_stale = con.execute("SELECT COUNT(*) FROM vw_high_value_stale_leads").fetchone()[0]
            overdue = con.execute("SELECT COALESCE(SUM(outstanding_ngn),0) FROM vw_overdue_receivables").fetchone()[0]
            critical = self._rows(con.execute("SELECT * FROM vw_critical_open_maintenance WHERE hours_open>48 ORDER BY hours_open DESC").fetchall())
            delayed = self._rows(con.execute("SELECT * FROM vw_delayed_milestones ORDER BY planned_completion_date").fetchall())
            awaiting = con.execute("SELECT COUNT(*) FROM investors WHERE awaiting_update='Yes'").fetchone()[0]
        weekend = self.get_shortlet_bookings("2026-10-02", "2026-10-04")
        attention = []
        if high_stale:
            attention.append({"severity":"High","area":"Sales","issue":f"{high_stale} high-value/high-score stale leads require attention."})
        if overdue:
            attention.append({"severity":"High","area":"Finance","issue":f"NGN {float(overdue):,.0f} is outstanding on overdue property payment plans."})
        if weekend["occupancy_pct"] < 65:
            attention.append({"severity":"Medium","area":"Shortlet","issue":f"Upcoming weekend occupancy is {weekend['occupancy_pct']}%, below the 65% demo threshold."})
        if critical:
            attention.append({"severity":"Critical","area":"Facilities","issue":f"{len(critical)} critical maintenance issues have been open for more than 48 hours."})
        if delayed:
            attention.append({"severity":"High","area":"Construction","issue":f"{len(delayed)} delayed/late milestones require review."})
        if awaiting:
            attention.append({"severity":"Medium","area":"Investor Relations","issue":f"{awaiting} investors are awaiting scheduled updates."})
        return {
            "as_of": AS_OF.isoformat(sep=" "),
            "headline": "Management attention required across sales, receivables, shortlet operations, facilities, construction and investor relations.",
            "metrics": {
                "stale_open_leads": stale,
                "high_value_stale_leads": high_stale,
                "overdue_receivables_ngn": float(overdue or 0),
                "target_weekend_occupancy_pct": weekend["occupancy_pct"],
                "critical_maintenance_over_48h": len(critical),
                "delayed_or_late_milestones": len(delayed),
                "investors_awaiting_updates": awaiting,
            },
            "attention_items": attention,
        }

    # 12. Draft communication; stored as Draft only
    def draft_communication(self, entity_type: str, entity_id: str, channel: str, subject: str, message: str, commit: bool = True) -> Dict[str, Any]:
        self._require_write("draft_communication")
        if entity_type not in {"Lead","Customer","Investor","Guest"}:
            raise ValueError("entity_type must be Lead, Customer, Investor, or Guest")
        if entity_type not in COMMUNICATION_ENTITY_ACCESS.get(self.context.role, set()):
            raise PermissionError(f"Role '{self.context.role}' cannot draft communications to {entity_type} records.")
        if channel not in {"WhatsApp","Email","SMS","Phone"}:
            raise ValueError("Unsupported channel")
        if not subject.strip() or not message.strip():
            raise ValueError("subject and message are required")
        entity_table = {"Lead":("leads","lead_id"),"Customer":("customers","customer_id"),"Investor":("investors","investor_id"),"Guest":("guests","guest_id")}[entity_type]
        with self._conn() as con:
            table, id_col = entity_table
            if not con.execute(f"SELECT 1 FROM {table} WHERE {id_col}=?", (entity_id,)).fetchone():
                raise KeyError(f"{entity_type} not found: {entity_id}")
            cid = self._next_id(con, "communications", "communication_id", "COM-", 4)
            if commit:
                cols = [r["name"] for r in con.execute("PRAGMA table_info(communications)").fetchall()]
                if "message" in cols:
                    con.execute("INSERT INTO communications (communication_id,entity_type,entity_id,channel,subject,message,communication_date,status,employee_id) VALUES (?,?,?,?,?,?,?,?,?)",
                                (cid, entity_type, entity_id, channel, subject, message, AS_OF.isoformat(sep=" "), "Draft", self.context.employee_id))
                else:
                    con.execute("INSERT INTO communications (communication_id,entity_type,entity_id,channel,subject,communication_date,status,employee_id) VALUES (?,?,?,?,?,?,?,?)",
                                (cid, entity_type, entity_id, channel, subject, AS_OF.isoformat(sep=" "), "Draft", self.context.employee_id))
                log_id = self._audit(con, f"Draft {channel} communication to {entity_type} {entity_id}: {subject}", "Draft communication", cid)
                con.commit()
            else:
                log_id = None
        return {"communication_id": cid, "entity_type": entity_type, "entity_id": entity_id, "channel": channel, "subject": subject, "message": message, "status": "Draft", "committed": commit, "audit_log_id": log_id}
