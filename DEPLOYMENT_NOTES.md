# Deployment notes

CedarStone Properties & Living Ltd. is fictional. All names, contact details, transactions, properties, investors, bookings, and operational records in this demo are synthetic.

The public demo is intentionally designed around a local bundled SQLite master database. On each Streamlit browser session, the app copies that master database into a temporary session-specific file. Demo actions therefore behave like real writes without changing the bundled master dataset.

For a real client deployment, replace the local SQLite layer with a production database such as PostgreSQL/Supabase or the client's existing ERP/CRM/database and implement real authentication, row-level permissions, backups, monitoring, and approval workflows.
