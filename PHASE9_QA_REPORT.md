# CedarStone AI — Phase 9 QA & Agent Evaluation

**Status:** Deployment-ready prototype after code-level QA  
**Demo as-of date:** 30 September 2026  
**QA date:** 1 October 2026

## Result

**40 / 40 automated business-logic, agent, permission and write-action tests passed.**

## Validated known-answer scenarios

- Target shortlet occupancy for 2–4 October 2026: **54.8%**
- Critical maintenance tickets open beyond 48 hours: **3**
- Investors awaiting scheduled updates: **4**
- Synthetic overdue receivables: **NGN 1,929,562,159**
- CedarStone Park delayed milestones surface correctly
- Investor `INV-003` resolves to a connected investment portfolio
- High-value stale leads are detected from the database

## Security and governance tests

- Invalid role names are rejected.
- Employee/role mismatches are rejected.
- Sales users cannot access finance receivables.
- Facilities users cannot access investor portfolios.
- Construction users cannot access shortlet booking data.
- Shortlet users cannot access receivables.
- Individual sales executives are scoped to their assigned leads.
- Sales users cannot create cross-department tasks.
- Department/assignee mismatches are rejected.
- Sales users cannot create maintenance tickets.
- Invalid property/unit and vendor combinations are rejected.
- Communication recipient type is role-restricted.
- Invalid recipient IDs and blank drafts are rejected.
- Every simulated write action creates an audit record.

## Phase 9 fixes applied

1. **Draft-message persistence:** communication draft bodies are now stored in the demo database instead of existing only in the immediate response.
2. **Department task enforcement:** direct tool calls can no longer bypass departmental task boundaries.
3. **Employee/role validation:** the tool layer verifies that the acting employee actually belongs to the department represented by the selected role.
4. **Sales ownership scope:** ordinary sales executives see and update only assigned leads, while sales management/CRM roles retain team scope.
5. **Recipient validation:** communication tools validate the recipient ID and role-appropriate recipient type.
6. **Finance/investor UI separation:** Investor Relations no longer receives the same customer-receivables view as Finance.

## Model integration verification

The configured Gemini model ID and automatic Python function-calling pattern were checked against the current Google Gemini API documentation during QA.

## Runtime note

The current execution sandbox does not have Streamlit installed and cannot reach PyPI, so a live Streamlit process could not be launched here. The application Python modules compile successfully, all underlying application/business logic tests pass, and the included `requirements.txt` is ready for installation on Streamlit Community Cloud or a normal Python environment.

## Recommended next phase

Phase 10 should deploy this build to a public demo URL, configure secrets if Live Gemini is desired, perform browser-level visual smoke testing, and create the final client demonstration script.
