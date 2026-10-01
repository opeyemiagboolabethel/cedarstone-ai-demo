from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from agent import CedarStoneAgent
from cedarstone_tools import CedarStoneTools, ToolContext

HERE = Path(__file__).resolve().parent
MASTER_DB = HERE / "CedarStone_AI_Agent_Demo.db"
AS_OF = "30 September 2026"
TARGET_START = "2026-10-02"
TARGET_END = "2026-10-04"

ROLE_LABELS = {
    "executive": "Executive Management",
    "sales": "Sales & CRM",
    "finance": "Finance & Accounts",
    "investor_relations": "Investor Relations",
    "facilities": "Facilities & Property Management",
    "construction": "Construction & Development",
    "shortlet": "Shortlet Operations",
    "admin": "Admin & HR",
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

st.set_page_config(
    page_title="CedarStone AI | Operations Agent",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #F7F8F6; }
    [data-testid="stSidebar"] { background: #102A2A; }
    [data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stCaption {
    color: #F7FAF8 !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #FFFFFF !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="select"] svg {
    color: #102A2A !important;
    fill: #102A2A !important;
}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E3E8E5;
        padding: 14px 16px;
        border-radius: 14px;
        box-shadow: 0 2px 12px rgba(16,42,42,0.04);
    }
    .hero {
        background: linear-gradient(120deg, #102A2A 0%, #174D49 68%, #1D625C 100%);
        color: white;
        border-radius: 20px;
        padding: 28px 30px;
        margin-bottom: 18px;
        box-shadow: 0 12px 34px rgba(16,42,42,0.16);
    }
    .hero h1 { margin: 0; font-size: 2.15rem; letter-spacing: -0.04em; }
    .hero p { margin: 8px 0 0 0; color: #D9ECE8; font-size: 1rem; }
    .eyebrow { font-size: .78rem; text-transform: uppercase; letter-spacing: .16em; color: #A7D6CE; font-weight: 700; }
    .status-chip {
        display:inline-block; padding:5px 10px; border-radius:999px;
        background:#E4F5EF; color:#0C655B; font-weight:700; font-size:.78rem;
        margin-right:6px;
    }
    .warning-chip {
        display:inline-block; padding:5px 10px; border-radius:999px;
        background:#FFF3D6; color:#7A4B00; font-weight:700; font-size:.78rem;
    }
    .section-card {
        background:white; border:1px solid #E3E8E5; border-radius:16px;
        padding:18px 20px; margin-bottom:12px;
    }
    .risk-card {
        background:#FFF9F1; border:1px solid #F0D7AE; border-radius:14px;
        padding:14px 16px; margin-bottom:10px;
    }
    .demo-note { color:#5F6C69; font-size:.88rem; }
    .small-label { color:#667572; font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
    div[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
    .block-container { padding-top: 1.4rem; padding-bottom: 2.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float | int | None) -> str:
    return f"₦{float(value or 0):,.0f}"


def get_secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


def ensure_session_db() -> Path:
    if "session_db" not in st.session_state:
        path = Path(tempfile.gettempdir()) / f"cedarstone_{uuid.uuid4().hex}.db"
        shutil.copy2(MASTER_DB, path)
        st.session_state.session_db = str(path)
    return Path(st.session_state.session_db)


def reset_session_db() -> None:
    old = st.session_state.get("session_db")
    if old:
        try:
            Path(old).unlink(missing_ok=True)
        except Exception:
            pass
    for key in ["session_db", "agent", "agent_key", "messages", "pending_prompt"]:
        st.session_state.pop(key, None)
    st.rerun()


def sql_df(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with sqlite3.connect(ensure_session_db()) as con:
        return pd.read_sql_query(sql, con, params=params)


def sql_scalar(sql: str, params: tuple[Any, ...] = ()) -> Any:
    with sqlite3.connect(ensure_session_db()) as con:
        row = con.execute(sql, params).fetchone()
        return row[0] if row else None


def employee_options(role: str) -> pd.DataFrame:
    dept = ROLE_DEPARTMENTS[role]
    return sql_df(
        "SELECT employee_id, full_name, role FROM employees WHERE department_id=? AND status='Active' ORDER BY employee_id",
        (dept,),
    )


def get_tools(role: str, employee_id: str) -> CedarStoneTools:
    return CedarStoneTools(ensure_session_db(), ToolContext(employee_id=employee_id, role=role))


def get_agent(role: str, employee_id: str, provider: str, api_key: str) -> CedarStoneAgent:
    key = (role, employee_id, provider, bool(api_key), str(ensure_session_db()))
    if st.session_state.get("agent_key") != key:
        st.session_state.agent = CedarStoneAgent(
            role=role,
            employee_id=employee_id,
            db_path=ensure_session_db(),
            provider=provider,
            gemini_api_key=api_key or None,
        )
        st.session_state.agent_key = key
    return st.session_state.agent


def render_dataframe(df: pd.DataFrame, height: int = 300) -> None:
    if df.empty:
        st.info("No records match this view.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def render_result_data(data: Any) -> None:
    if data is None:
        return
    with st.expander("View records used by the agent"):
        if isinstance(data, dict):
            # Prefer compact tabular rendering for common list payloads.
            for k in ["leads", "records", "units", "milestones", "bookings", "investments"]:
                if isinstance(data.get(k), list) and data[k]:
                    render_dataframe(pd.DataFrame(data[k]), height=260)
                    return
            st.json(data, expanded=False)
        elif isinstance(data, list):
            render_dataframe(pd.DataFrame(data), height=260)
        else:
            st.write(data)


DB = ensure_session_db()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## CEDARSTONE AI")
    st.caption("Agentic Real Estate Operations System")
    st.divider()

    role = st.selectbox(
        "Demo role",
        list(ROLE_LABELS.keys()),
        format_func=lambda x: ROLE_LABELS[x],
        index=0,
    )
    emps = employee_options(role)
    employee_lookup = {
        f"{r.employee_id} · {r.full_name} — {r.role}": r.employee_id
        for r in emps.itertuples(index=False)
    }
    employee_label = st.selectbox("Acting as", list(employee_lookup.keys()))
    employee_id = employee_lookup[employee_label]

    st.divider()
    api_key = get_secret("GEMINI_API_KEY") or get_secret("GOOGLE_API_KEY")
    provider_label = st.radio(
        "AI mode",
        ["Offline Demo", "Live Gemini"],
        index=0 if not api_key else 1,
        help="Offline Demo requires no API key. Live Gemini uses function calling against the same CedarStone tools.",
    )
    provider = "offline" if provider_label == "Offline Demo" else "gemini"
    if provider == "gemini" and not api_key:
        st.warning("Live Gemini is not configured. Add GEMINI_API_KEY in Streamlit secrets or your environment.")
    elif provider == "gemini":
        st.success("Live Gemini configured")
    else:
        st.info("Zero-cost offline demo mode")

    st.divider()
    st.caption("Demo controls")
    if st.button("Reset demo data", use_container_width=True):
        reset_session_db()
    st.caption("Every browser session uses a private copy of the fictional database.")

# ---------------- Hero ----------------
st.markdown(
    f"""
    <div class="hero">
      <div class="eyebrow">ONE Light Analytics · Demonstration Project 06</div>
      <h1>CedarStone AI Operations Agent</h1>
      <p>One intelligent operating layer across sales, shortlets, investors, facilities, construction, finance and management.</p>
      <div style="margin-top:16px">
        <span class="status-chip">Fictional company data</span>
        <span class="status-chip">Private demo sandbox</span>
        <span class="warning-chip">As of {AS_OF}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Global metrics are shown only where the selected role has business justification.
role_sections = {
    "executive": {"overview","sales","shortlet","facilities","construction","finance","actions","audit"},
    "admin": {"overview","actions","audit"},
    "sales": {"sales","actions"},
    "finance": {"finance","actions"},
    "investor_relations": {"finance","actions"},
    "facilities": {"facilities","actions"},
    "construction": {"construction","actions"},
    "shortlet": {"shortlet","facilities","actions"},
}
allowed = role_sections[role]

all_tabs = [("AI Agent","agent")]
for label, key in [
    ("Executive Overview","overview"),
    ("Sales","sales"),
    ("Shortlets","shortlet"),
    ("Facilities","facilities"),
    ("Construction","construction"),
    ("Investors & Finance","finance"),
    ("Action Lab","actions"),
    ("Audit Log","audit"),
]:
    if key in allowed:
        all_tabs.append((label,key))

ui_tabs = st.tabs([x[0] for x in all_tabs])
tab_by_key = {key: tab for (_, key), tab in zip(all_tabs, ui_tabs)}

# ---------------- AI Agent ----------------
with tab_by_key["agent"]:
    left, right = st.columns([1.65, 1])
    with left:
        st.subheader("Ask CedarStone AI")
        st.caption("The agent decides which approved business tool to use. Write actions require explicit instructions and are logged.")

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role":"assistant","content":"I’m CedarStone AI. Ask me about management priorities, leads, units, shortlet occupancy, investors, receivables, maintenance or construction."}
            ]

        for msg in st.session_state.messages[-12:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Ask a CedarStone business question...")
        if st.session_state.get("pending_prompt"):
            prompt = st.session_state.pop("pending_prompt")

        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    actual_provider = provider
                    if actual_provider == "gemini" and not api_key:
                        actual_provider = "offline"
                    agent = get_agent(role, employee_id, actual_provider, api_key)
                    result = agent.ask(prompt)
                    st.markdown(result.get("text", "No response returned."))
                    render_result_data(result.get("data"))
                    st.caption(f"Mode: {result.get('provider','unknown')} · Role: {ROLE_LABELS[role]}")
                    st.session_state.messages.append({"role":"assistant","content":result.get("text", "No response returned.")})
                except PermissionError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Agent request failed: {type(exc).__name__}: {exc}")

    with right:
        st.subheader("Demo scenarios")
        scenarios = sql_df("SELECT scenario_id, scenario_name, example_prompt FROM demo_scenarios ORDER BY scenario_id")
        for r in scenarios.itertuples(index=False):
            if st.button(r.scenario_name, key=f"scenario_{r.scenario_id}", use_container_width=True):
                st.session_state.pending_prompt = r.example_prompt
                st.rerun()
        st.markdown("<div class='demo-note'>The scenarios are backed by deliberate conditions in the database, so the agent can be tested against known answers.</div>", unsafe_allow_html=True)

# ---------------- Executive Overview ----------------
if "overview" in tab_by_key:
    with tab_by_key["overview"]:
        tools = get_tools("executive", employee_id if role=="executive" else "EMP-001")
        briefing = tools.generate_management_briefing()
        m = briefing["metrics"]
        st.subheader("Management Command Centre")

        row1 = st.columns(3)
        row1[0].metric("High-value stale leads", int(m["high_value_stale_leads"]))
        row1[1].metric("Overdue receivables", money(m["overdue_receivables_ngn"]))
        row1[2].metric("Weekend occupancy", f"{m['target_weekend_occupancy_pct']}%")
        
        row2 = st.columns(3)
        row2[0].metric("Critical maintenance >48h", int(m["critical_maintenance_over_48h"]))
        row2[1].metric("Delayed / late milestones", int(m["delayed_or_late_milestones"]))
        row2[2].metric("Investor updates due", int(m["investors_awaiting_updates"]))
        
        st.markdown("### What needs attention")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""<div class="risk-card"><b>Commercial</b><br>{m['high_value_stale_leads']} high-value leads require renewed follow-up; overdue receivables total {money(m['overdue_receivables_ngn'])}.</div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""<div class="risk-card"><b>Hospitality</b><br>Only {m['target_weekend_occupancy_pct']}% of shortlet-enabled units are booked for 2–4 October.</div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="risk-card"><b>Operations</b><br>{m['critical_maintenance_over_48h']} critical maintenance tickets are still open beyond 48 hours.</div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""<div class="risk-card"><b>Delivery & Investors</b><br>{m['delayed_or_late_milestones']} milestones are delayed/late and {m['investors_awaiting_updates']} investors are awaiting updates.</div>""",
                unsafe_allow_html=True,
            )

        st.markdown("### Portfolio snapshot")
        portfolio = sql_df("SELECT * FROM vw_property_unit_summary ORDER BY property_name")
        render_dataframe(portfolio, 240)

# ---------------- Sales ----------------
if "sales" in tab_by_key:
    with tab_by_key["sales"]:
        st.subheader("Sales & CRM Intelligence")
        pipeline = sql_df("SELECT * FROM vw_sales_pipeline ORDER BY pipeline_value_ngn DESC")
        if role == "sales":
            emp_role = str(sql_scalar("SELECT role FROM employees WHERE employee_id=?", (employee_id,)) or "").lower()
            team_scope = any(token in emp_role for token in ("head", "manager", "crm officer"))
            if team_scope:
                stale = sql_df("SELECT * FROM vw_high_value_stale_leads ORDER BY lead_score DESC, budget_ngn DESC")
            else:
                stale = sql_df("""
                    SELECT * FROM vw_high_value_stale_leads
                    WHERE lead_id IN (SELECT lead_id FROM leads WHERE assigned_sales_officer=?)
                    ORDER BY lead_score DESC, budget_ngn DESC
                """, (employee_id,))
        else:
            stale = sql_df("SELECT * FROM vw_high_value_stale_leads ORDER BY lead_score DESC, budget_ngn DESC")
        c1, c2, c3 = st.columns(3)
        c1.metric("Active pipeline leads", int(pipeline.loc[~pipeline.lead_status.isin(['Won','Lost']), 'lead_count'].sum()))
        c2.metric("High-value stale leads", len(stale))
        c3.metric("High-value stale budget", money(stale["budget_ngn"].sum() if not stale.empty else 0))
        st.markdown("#### Pipeline by stage")
        if not pipeline.empty:
            chart_df = pipeline.set_index("lead_status")[["lead_count"]]
            st.bar_chart(chart_df)
        st.markdown("#### High-value leads needing follow-up")
        render_dataframe(stale, 330)

# ---------------- Shortlets ----------------
if "shortlet" in tab_by_key:
    with tab_by_key["shortlet"]:
        st.subheader("Shortlet Operations")
        tools = get_tools(role, employee_id)
        occ = tools.get_shortlet_bookings(TARGET_START, TARGET_END)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Shortlet units", occ["shortlet_units"])
        c2.metric("Booked units", occ["booked_units"])
        c3.metric("2–4 Oct occupancy", f"{occ['occupancy_pct']}%")
        c4.metric("Booking value", money(occ["booking_value_ngn"]))
        st.markdown("#### Monthly booking revenue")
        rev = sql_df("SELECT revenue_month, SUM(booking_revenue_ngn) AS revenue_ngn FROM vw_shortlet_revenue GROUP BY revenue_month ORDER BY revenue_month")
        if not rev.empty:
            st.line_chart(rev.set_index("revenue_month"))
        st.markdown("#### Upcoming confirmed bookings")
        upcoming = sql_df("""
            SELECT b.booking_id,u.unit_number,p.property_name,g.full_name AS guest,b.check_in,b.check_out,
                   b.total_amount_ngn,b.payment_status
            FROM bookings b JOIN units u ON u.unit_id=b.unit_id
            JOIN properties p ON p.property_id=u.property_id JOIN guests g ON g.guest_id=b.guest_id
            WHERE date(b.check_in)>=date('2026-10-01') AND b.booking_status='Confirmed'
            ORDER BY b.check_in LIMIT 30
        """)
        render_dataframe(upcoming, 320)

# ---------------- Facilities ----------------
if "facilities" in tab_by_key:
    with tab_by_key["facilities"]:
        st.subheader("Facilities & Maintenance")
        critical = sql_df("SELECT * FROM vw_critical_open_maintenance WHERE hours_open>48 ORDER BY hours_open DESC")
        open_count = int(sql_scalar("SELECT COUNT(*) FROM maintenance WHERE status NOT IN ('Resolved','Closed')") or 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Open maintenance tickets", open_count)
        c2.metric("Critical >48 hours", len(critical))
        c3.metric("Estimated critical cost", money(sql_scalar("SELECT COALESCE(SUM(estimated_cost_ngn),0) FROM maintenance WHERE priority='Critical' AND status NOT IN ('Resolved','Closed')")))
        st.markdown("#### Escalation queue")
        render_dataframe(critical, 300)

# ---------------- Construction ----------------
if "construction" in tab_by_key:
    with tab_by_key["construction"]:
        st.subheader("Construction & Development")
        projects = sql_df("SELECT project_id,project_name,budget_ngn,spent_to_date_ngn,percent_complete,status,planned_completion_date FROM construction ORDER BY project_id")
        render_dataframe(projects, 190)
        st.markdown("#### Delayed / late milestones")
        delayed = sql_df("SELECT * FROM vw_delayed_milestones ORDER BY planned_completion_date")
        render_dataframe(delayed, 330)
        if not projects.empty:
            st.markdown("#### Project completion")
            progress = projects.set_index("project_name")[["percent_complete"]]
            st.bar_chart(progress)

# ---------------- Investors & Finance ----------------
if "finance" in tab_by_key:
    with tab_by_key["finance"]:
        st.subheader("Investors & Finance")
        awaiting = sql_df("SELECT investor_id,investor_name,country,reporting_frequency,investment_count,total_investment_value_ngn FROM vw_investor_summary WHERE awaiting_update='Yes' ORDER BY total_investment_value_ngn DESC")
        if role in {"executive", "finance"}:
            overdue = sql_df("SELECT * FROM vw_overdue_receivables ORDER BY outstanding_ngn DESC")
            c1, c2, c3 = st.columns(3)
            c1.metric("Overdue plans", len(overdue))
            c2.metric("Outstanding receivables", money(overdue["outstanding_ngn"].sum() if not overdue.empty else 0))
            c3.metric("Investor updates due", len(awaiting))
            st.markdown("#### Largest overdue balances")
            render_dataframe(overdue.head(20), 320)
        else:
            c1, c2 = st.columns(2)
            c1.metric("Investor updates due", len(awaiting))
            c2.metric("Affected investment value", money(awaiting["total_investment_value_ngn"].sum() if not awaiting.empty else 0))
        st.markdown("#### Investors awaiting updates")
        render_dataframe(awaiting, 260)

# ---------------- Action Lab ----------------
if "actions" in tab_by_key:
    with tab_by_key["actions"]:
        st.subheader("Action Lab")
        st.caption("These forms execute against your private demo database and create audit records. Nothing is sent outside the demo.")
        tools = get_tools(role, employee_id)
        caps = WRITE_CAPABILITIES.get(role, set())

        action_tabs = []
        if "update_lead" in caps: action_tabs.append(("Update lead", "lead"))
        if "create_task" in caps: action_tabs.append(("Create task", "task"))
        if "create_maintenance" in caps: action_tabs.append(("Maintenance ticket", "maintenance"))
        if "draft_communication" in caps: action_tabs.append(("Draft communication", "communication"))
        rendered = st.tabs([x[0] for x in action_tabs]) if action_tabs else []

        for (_, key), t in zip(action_tabs, rendered):
            with t:
                if key == "lead":
                    if role == "sales":
                        emp_role = str(sql_scalar("SELECT role FROM employees WHERE employee_id=?", (employee_id,)) or "").lower()
                        team_scope = any(token in emp_role for token in ("head", "manager", "crm officer"))
                    else:
                        team_scope = True
                    if role == "sales" and not team_scope:
                        lead_ids = sql_df("SELECT lead_id,full_name,lead_status FROM leads WHERE lead_status NOT IN ('Won','Lost') AND assigned_sales_officer=? ORDER BY lead_score DESC LIMIT 80", (employee_id,))
                    else:
                        lead_ids = sql_df("SELECT lead_id,full_name,lead_status FROM leads WHERE lead_status NOT IN ('Won','Lost') ORDER BY lead_score DESC LIMIT 80")
                    options = {f"{r.lead_id} · {r.full_name} · {r.lead_status}": r.lead_id for r in lead_ids.itertuples(index=False)}
                    with st.form("lead_update_form"):
                        pick = st.selectbox("Lead", list(options.keys()))
                        new_status = st.selectbox("New status", ["New","Contacted","Qualified","Inspection Booked","Negotiation","Won","Lost"])
                        note = st.text_input("Note", "Updated during CedarStone AI demonstration")
                        submit = st.form_submit_button("Update lead")
                    if submit:
                        try:
                            result = tools.update_lead_status(options[pick], new_status, note)
                            st.success(f"{result['lead_id']} updated: {result['old_status']} → {result['new_status']}")
                        except Exception as exc:
                            st.error(str(exc))

                elif key == "task":
                    if role in {"executive", "admin"}:
                        depts = sql_df("SELECT department_id,department_name FROM departments ORDER BY department_id")
                    else:
                        depts = sql_df("SELECT department_id,department_name FROM departments WHERE department_id=?", (ROLE_DEPARTMENTS[role],))
                    dept_map = {f"{r.department_id} · {r.department_name}": r.department_id for r in depts.itertuples(index=False)}
                    with st.form("task_form"):
                        dlabel = st.selectbox("Department", list(dept_map.keys()))
                        selected_dept = dept_map[dlabel]
                        staff = sql_df("SELECT employee_id,full_name,role FROM employees WHERE department_id=? ORDER BY employee_id", (selected_dept,))
                        staff_map = {f"{r.employee_id} · {r.full_name} — {r.role}": r.employee_id for r in staff.itertuples(index=False)}
                        slabel = st.selectbox("Assign to", list(staff_map.keys()))
                        desc = st.text_area("Task", "Follow up on the operational issue identified during the management review.")
                        due = st.date_input("Due date")
                        priority = st.selectbox("Priority", ["Low","Medium","High"], index=1)
                        submit = st.form_submit_button("Create simulated task")
                    if submit:
                        try:
                            result = tools.create_task(selected_dept, staff_map[slabel], desc, str(due), priority)
                            st.success(f"Created {result['task_id']} and logged the AI action.")
                        except Exception as exc:
                            st.error(str(exc))

                elif key == "maintenance":
                    props = sql_df("SELECT property_id,property_name FROM properties WHERE property_id IN ('PROP-001','PROP-003') ORDER BY property_id")
                    prop_map = {f"{r.property_id} · {r.property_name}": r.property_id for r in props.itertuples(index=False)}
                    with st.form("maintenance_form"):
                        plabel = st.selectbox("Property", list(prop_map.keys()))
                        selected_prop = prop_map[plabel]
                        units = sql_df("SELECT unit_id,unit_number FROM units WHERE property_id=? ORDER BY unit_number", (selected_prop,))
                        unit_map = {f"{r.unit_number} · {r.unit_id}": r.unit_id for r in units.itertuples(index=False)}
                        ulabel = st.selectbox("Unit", list(unit_map.keys()))
                        issue = st.selectbox("Issue type", ["Air Conditioning","Plumbing","Electrical","Water Supply","Door/Lock","Internet","Other"])
                        desc = st.text_area("Description", "Issue reported during the CedarStone AI demonstration.")
                        priority = st.selectbox("Priority", ["Low","Medium","High","Critical"], index=1)
                        submit = st.form_submit_button("Create simulated ticket")
                    if submit:
                        try:
                            result = tools.create_maintenance_ticket(selected_prop, unit_map[ulabel], issue, desc, priority)
                            st.success(f"Created maintenance ticket {result['ticket_id']} and logged the action.")
                        except Exception as exc:
                            st.error(str(exc))

                elif key == "communication":
                    with st.form("communication_form"):
                        entity_types = {
                            "sales": ["Lead", "Customer"],
                            "investor_relations": ["Investor"],
                            "shortlet": ["Guest", "Customer"],
                            "finance": ["Customer", "Investor"],
                            "facilities": ["Customer", "Guest"],
                            "construction": ["Investor"],
                        }.get(role, ["Lead", "Customer", "Investor", "Guest"])
                        entity_type = st.selectbox("Recipient type", entity_types)
                        default_id = {"Investor":"INV-003", "Lead":"LEAD-0012", "Customer":"CUS-001", "Guest":"GST-0001"}[entity_type]
                        entity_id = st.text_input("Record ID", default_id)
                        channel = st.selectbox("Channel", ["WhatsApp","Email","SMS"])
                        subject = st.text_input("Subject", "CedarStone update")
                        message = st.text_area("Draft message", "Thank you for your continued relationship with CedarStone. This is a simulated communication prepared by the AI demonstration system.")
                        submit = st.form_submit_button("Save draft")
                    if submit:
                        try:
                            result = tools.draft_communication(entity_type, entity_id, channel, subject, message)
                            st.success(f"Saved draft {result['communication_id']}. No message was sent.")
                        except Exception as exc:
                            st.error(str(exc))

# ---------------- Audit ----------------
if "audit" in tab_by_key:
    with tab_by_key["audit"]:
        st.subheader("AI Governance & Activity Log")
        st.caption("Every simulated write performed through the CedarStone tool layer is auditable.")
        audit = sql_df("""
            SELECT a.log_id,a.timestamp,a.user_employee_id,e.full_name,a.request,a.action_type,a.records_affected,a.outcome
            FROM ai_activity_log a LEFT JOIN employees e ON e.employee_id=a.user_employee_id
            ORDER BY a.timestamp DESC LIMIT 100
        """)
        render_dataframe(audit, 430)

st.markdown("---")
st.caption("CedarStone Properties & Living Ltd. is fictional. This application is a ONE Light Analytics demonstration of agentic business operations, not a production client system.")
