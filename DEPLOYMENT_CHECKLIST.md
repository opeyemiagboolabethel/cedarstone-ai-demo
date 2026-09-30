# CedarStone AI — Streamlit Community Cloud Deployment

## What is already ready
- Entry point: `streamlit_app.py`
- Master fictional SQLite database bundled in the repository
- Each visitor receives a private temporary database copy
- Offline Demo mode works without an API key
- Live Gemini mode reads the API key from Streamlit secrets
- Streamlit and Google GenAI versions are pinned for reproducibility

## One-time GitHub step
Create an empty GitHub repository, recommended name:

`cedarstone-ai-demo`

Do not add a README, .gitignore, or license when creating it if ChatGPT will upload the prepared files afterward.

## Streamlit deployment
1. Sign in to Streamlit Community Cloud with GitHub.
2. Choose **Create app**.
3. Select the CedarStone repository and the `main` branch.
4. Entrypoint: `streamlit_app.py`.
5. Choose Python 3.12 in Advanced settings.
6. The app can deploy immediately in Offline Demo mode.

## Optional live AI mode
In Streamlit Advanced settings > Secrets, add:

```toml
GEMINI_API_KEY = "your-real-key"
GEMINI_MODEL = "gemini-3.8-flash"
```

Never commit the key to GitHub. The `.gitignore` already excludes local secret files.

## Recommended public-demo settings
- Keep the repository private if you do not want the implementation source publicly visible.
- The application itself can still be shared according to Streamlit app access settings.
- Use only the fictional CedarStone data with Gemini free-tier testing.
- Reset demo data before a live presentation if needed.

## Suggested app URL
If available, use a memorable Streamlit subdomain such as:

`cedarstone-ai-demo.streamlit.app`

## Demonstration sequence
1. Executive role → “What requires management attention today?”
2. Sales role → identify stale high-value leads.
3. Facilities role → show critical maintenance issues open >48 hours.
4. Construction role → explain CedarStone Park delays.
5. Shortlet role → calculate occupancy for 2–4 October 2026.
6. Investor Relations role → inspect INV-003.
7. Action Lab → create a task or draft communication.
8. Audit view → show that the AI action was logged.
