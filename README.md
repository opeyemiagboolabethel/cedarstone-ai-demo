# CedarStone AI — Phase 8 Web Application

A polished Streamlit demonstration of an agentic operating system for a fictional full-service real-estate company.

## What the app includes

- Executive command-centre dashboard
- Conversational AI operations agent
- Sales/CRM intelligence
- Shortlet occupancy and revenue views
- Facilities and maintenance escalation view
- Construction project and milestone view
- Investor and receivables view
- Role switching for eight operating roles
- Safe simulated write actions: lead updates, tasks, maintenance tickets and communication drafts
- AI activity/audit log
- Private per-browser-session sandbox database
- Offline zero-cost demo mode
- Optional Gemini 3.8 Flash tool-calling mode

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

No API key is required for Offline Demo mode.

## Enable live Gemini

For local development, create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` and add:

```toml
GEMINI_API_KEY = "your-key"
```

Do not commit the real secret to Git.

## Streamlit Community Cloud

1. Put this folder in a GitHub repository.
2. Create a Streamlit Community Cloud app and select `streamlit_app.py` as the entry point.
3. Add `GEMINI_API_KEY` in the app's secrets if live Gemini is required.
4. The app works without a key in Offline Demo mode.

## Safety design

- Data is entirely fictional.
- Each browser session receives a private copy of the master demo database.
- No real payments, contracts or external communications are executed.
- Simulated writes are role-limited and recorded in `ai_activity_log`.
- Sensitive production actions should require stronger authentication, RLS and human approval.

## Recommended demo flow

1. Start as Executive Management.
2. Open Executive Overview and show cross-department KPIs.
3. Ask: `What requires management attention today?`
4. Ask: `Which high-value leads have not been contacted in more than five days?`
5. Ask: `Why is CedarStone Park behind schedule?`
6. Show Facilities and Shortlets tabs.
7. Open Action Lab and create a simulated task or update a lead.
8. Open Audit Log to show governance and traceability.
9. Switch to Sales or Facilities role to demonstrate role-based access.

## Project status

Phase 8 completes the user-facing application layer. The next phase is structured QA, agent evaluation and demonstration testing before public deployment.

## Phase 9 QA status

This build has completed structured Phase 9 QA. The included `test_phase9_qa.py` suite validates 40 known-answer, access-control, action-safety and auditability conditions.

Key Phase 9 hardening includes persistent draft-message bodies, employee/role identity validation, department-scoped task creation, individual sales ownership controls, role-specific communication recipient rules and a tighter Investor Relations view.

See `PHASE9_QA_REPORT.md` for the full QA summary.

## Phase 10 deployment
This build is packaged for Streamlit Community Cloud. See `DEPLOYMENT_CHECKLIST.md` for the exact deployment flow. Offline Demo mode requires no API key. Live Gemini mode uses Streamlit Secrets and `gemini-3.8-flash`.
