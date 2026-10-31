# Publish Practilume

Public name: **Practilume — Learn Forward, Give Back**  
Author: **Yifan Yan**  
Current production site: **https://practilume.allanzhang721.chatgpt.site** (Sites).

The instructions below cover the earlier Streamlit prototype. Suggested Streamlit address: **practilume-yifan.streamlit.app** (availability must be checked during deployment).

## Streamlit Community Cloud

Deploy the standalone repository, with this folder's contents at its root:

- Repository: `allanzhang721/studybridge-yifan` (existing repository identifier retained)
- Branch: `main`
- Main file: `app.py`
- Python: `3.12` in Advanced settings
- Custom subdomain: `practilume-yifan` (if available)
- Sharing: public / anyone with the link

The sample walkthrough, worksheet review, mock exams, charts and giving simulation work without secrets. Leave secrets empty for the initial public demo. The complete walkthrough is available at `/?demo=1` on the deployed site.

The root `requirements.txt` installs runtime dependencies, and `.streamlit/config.toml` supplies the theme. Sample assets and the empty public ledger are included. Local databases, credentials, temporary files and development environments must never be uploaded.

## Public demo scope

Payments, donations and blockchain anchoring are simulations. AI is optional and remains off without credentials. Before enabling a paid AI key publicly, add service-wide rate limits and spending controls; session limits alone do not prevent abuse.

Accounts currently use SQLite on the app server. Community Cloud local storage is not durable: users should export their work, and persistent accounts require an external database before a production launch.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
