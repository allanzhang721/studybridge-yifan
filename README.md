> Current release: `app.py` now provides automatic AI image reading, original-image preservation, AI mock papers, a mistake board and a transparent giving demo. See [STREAMLIT_UPDATE.md](STREAMLIT_UPDATE.md) for features and remaining migration limitations. The earlier UI is retained as `legacy_app.py`; walkthrough notes below describe that version. Community Cloud local storage is not durable.
# Practilume

**Author: Yifan Yan**

A standalone Streamlit app for course-based maths preparation, real-exam calibration, and transparent education giving. It implements a focused first version of `../docs/PRODUCT_PLAN_ZH.md` in its own folder. It does not change or import the original Explain It! application.

## Run locally

Requires Python 3.11 or later. From this folder:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1
```

Or use `./run.ps1` after installing dependencies. Open **http://localhost:8502**. Run from this folder so Streamlit loads its theme and secrets configuration.

On macOS/Linux, use `.venv/bin/python` in place of `.venv/Scripts/python.exe`.

## First walkthrough

**My courses** groups features under **Learning report**, **Practice**, and **Materials**. The report has **Strengths / Weaknesses** subtabs with vertical bars on the same count scale. Each fictional worksheet contains five visible marked examples: fractions 2/5 correct, equations 3/5, graphs 4/5. These are authored sample results, not measured learning outcomes. When a course has saved attempts, its latest attempt supplies the chart instead. Reload the sample course to use the updated worksheet set; existing course history is preserved.

The three worksheet PNGs now form one fictional revision case: adding denominators, using the wrong inverse operation, and swapping slope/intercept. Each page includes successful work, visible incorrect reasoning and a follow-up question. The summary dashboard compares these error types and provides authored corrections with LaTeX. These annotations only appear for unchanged bundled transcripts paired with the matching image hash; they are not AI diagnoses of arbitrary uploads. Use **Try all 3 mistake examples** in Worksheet images to see the comparison immediately.

**Demo & examples** combines the complete walkthrough, interactive steps, and topic examples in one sidebar destination. The demo uses LaTeX for generated questions and worked solutions, with section shortcuts, worksheet downloads, and before/after topic counts. Switching views preserves your interactive demo progress.

For a **continuous end-to-end demonstration**, choose **Start full demo** on the home screen, or open `http://localhost:8502/?demo=1` in a new tab. The default **Complete worked example** shows all eight stages and their outputs on one scrollable page, with no steps to unlock. Select **Try it step by step** to operate the workflow yourself. Its **Start with sample images** button appears before the image previews and goes directly to transcript review; the real upload option is also available below. The eight stages cover image upload, transcript review, a generated mock, marking and explanations, targeted practice and retest, a post-exam update, giving simulation and journey summary. Example answers intentionally include three mistakes on the first attempt, one per topic (10/16). Their scores are labelled demonstrations, not learning evidence.

The walkthrough uses the same course, generation, grading, calibration and export functions as the rest of the app. Its records live in a separate, session-only workspace; they do not alter signed-in course history, paid entitlements or the live donation ledger. It makes no AI requests: prepared image transcripts are clearly identified. The demo's fictional post-exam source changes the next paper's topic balance without rewriting the original. It does not establish future predictive accuracy. **Restart this demo** clears only the walkthrough.

Open **Demo & examples → Topic examples** for three visual lessons on fractions, slope and probability. Each has an original Practilume diagram, a worked example, downloadable checked notes and a link to an online reference picture with its creator/licence. **Practise this topic** creates a focused course for the existing exam flow. These notes are prepared examples, not OCR output; no AI request is made when loading them. The online images remain on their source websites; their artwork is not bundled or copied into the previews.

1. Choose **Explore sample course**. The materials are explicitly fictional.
2. Open **Mock exams**, confirm the scope, and generate a free five-question paper.
3. Switch to **Take an exam**, answer the questions, and submit. Blank or invalid answers receive zero final-answer marks.
4. Open **Review & practice** for worked solutions. Generate a fresh practice set prioritising up to three weaker topics.
5. Under **After the real exam**, attach a completed real exam or the fictional download, enter its topic mark allocations, and save a review. It changes future topic balance, not the prior snapshot.
6. In **Plans & account**, try Plus without paying. Longer papers unlock and a sandbox order appears in your private Impact Ledger section. Simulating a refund adjusts that sandbox only.
7. Create a local account to retain the current workspace. Otherwise export your guest records before closing the browser session.

## Implemented learning features

- **Learning summary**: a single view of what the pages show, what to fix and what to practise next. Optional formulas, source evidence, text search and export sit inside **Check sources & formulas**. The former four-tab dashboard and study-board controls have been removed. Previously saved board records remain in course data and exports; they reset when source text or scope changes. Local summaries require no API; document analysis can use the existing opt-in AI path.

- **Worksheet images**: three original PNG lesson/worksheet pages with matching text files and a ZIP download. Try a bundled page directly, or upload 1–3 PNG/JPEG images (5 MB each, at most 12 MP and 6,000 pixels per side). Exact bundled images are recognised by SHA-256 and use prepared transcripts, explicitly labelled **no AI**. Other images support manual transcription or optional consented AI vision. Every transcript remains editable and requires explicit review and topic confirmation before saving a course. Raw image bytes stay in the Streamlit session; saved source records contain reviewed text, method and image hashes. Scanned PDF conversion is not included.
- PDF/TXT/Markdown import with bounded extraction, page-level sources, editable confirmed topic scope and optional AI-assisted organisation.
- Five bounded numerical skill families: fraction arithmetic, one-variable linear equations, slope/evaluation of linear functions, integer-root monic quadratics, and single-draw probability.
- Generated variations with independently recomputed answers; multiple-choice and numerical responses; exact equivalent fractions, decimals and percentages accepted. Arbitrary expressions are never evaluated.
- Source-linked blueprints, separate student PDFs and answer keys, first-attempt grading, personal mistakes, new practice questions, and aggregate practice accuracy.
- Frozen exam objects with fingerprints and input/source hashes. Later real-exam mark distributions are appended as separate records; they never alter prior papers.
- Forward-only calibration: a 50/50 blend of uniform scope weights and the last three recorded topic-share distributions, followed by an allocation that preserves at least one question per selected topic. This is a heuristic, not a probability forecast. Five-question exams covering all five topics necessarily remain evenly allocated.
- Comparison of covered/missed/extra supported topics and distribution error against a uniform baseline. Unsupported marks must not be reclassified to improve coverage. Do not interpret these metrics as verified exam prediction or learning impact.
- Local accounts using salted PBKDF2 password hashes, login lockout, account-scoped SQLite records, optimistic revision checks, export and deletion.

## Optional OpenAI integration

The app works without an API key. Local analysis is explicitly labelled a keyword scan; exam generation and grading use the checked mathematical engine, not an unconfigured AI fallback.

For AI-assisted source analysis and personalised explanations of mistakes, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and configure:

```toml
OPENAI_API_KEY = "your-server-key"
OPENAI_MODEL = "gpt-6-luna"
```

The same names can be set as environment variables. No key is collected from students. `gpt-6-luna` is a suggested starting model, based on [official OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-6-luna), which lists image input and structured outputs. It has not been benchmarked on this app's materials or live-tested here. Choose a model available to your account; image transcription additionally needs image input support. The runtime still requires both an explicit model setting and a key. The sidebar and the Topic examples view show the actual configuration status.

Image transcription follows the [Responses image-input guide](https://developers.openai.com/api/docs/guides/images-vision), using base64 images and structured per-image text/uncertainties. It preserves visible student errors rather than silently solving them. Incomplete output, mismatched page IDs and invalid schemas are rejected. Vision quality has not been live-tested without an API key; the sample/manual path works independently.

AI actions require explicit consent and are limited to 20 requests per saved workspace in this prototype. Source quotations must match the uploaded source text or are discarded. Provider errors are translated into safe messages without revealing keys or uploaded content. AI explanations are advice, not official grades.

Requests use `store=False`, a 45-second timeout, a bounded output size and one SDK retry. This does not guarantee zero provider retention. Per-workspace limits are not sufficient abuse protection for an unrestricted paid service; add production account/rate-limit controls before public rollout.

References: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [API tools](https://developers.openai.com/api/docs/guides/tools).

## Pricing and giving are prelaunch

The proposed **CNY 29 study pack / CNY 3 education allocation** is a product preview. There is **no checkout, charge, transfer, selected recipient, or claim of a completed donation**. Plus unlocks through a clearly labelled no-payment sandbox, and sandbox amounts are never counted in live totals. Final entitlements and pricing require cost and demand validation.

`data/public_ledger.json` starts empty. It is operator-maintained, not writable by learners. Live entries must include integer-cent amounts and evidence; the loader rejects unreconciled totals, transfers without receipts, and recipient confirmations without separate evidence. All evidence links must use HTTPS.

The Impact Ledger visualises the live allocation → transfer → receipt links → recipient responses. **Blockchain & proof** contains a separate fictional money trail and a working local SHA-256 chain demonstration: edit an allocation to break its fingerprint, or rebuild the chain to see its final hash diverge from the original reference. Demo downloads are labelled simulations and never update live totals. This is not a blockchain deployment: no wallet, RPC network, contract, transaction or independent anchor is configured. A future anchor could support detecting changed records, but would not verify the underlying payment, recipient or educational outcome by itself.

Example record schema (illustrative only, not present in the live ledger):

```json
{
  "id": "2026-11-001",
  "eligible_orders": 100,
  "pledge_per_order_cents": 300,
  "adjustment_cents": 0,
  "sent_cents": 0,
  "recipient_confirmed": false,
  "project_url": "https://example.org/project",
  "receipt_url": "",
  "confirmation_url": "",
  "report_url": ""
}
```

Before sales begin, choose a recipient, publish actual pricing/refund/settlement rules, replace manual order counts with reconciled payment records, and implement authenticated payment webhooks. Append explained corrections rather than silently overwriting historical financial records. Local checksums do not constitute independent audit or blockchain notarisation.

Public ledger questions require a local account and publication consent. Pending questions are visible only to their author and the operator. Run the following locally to inspect and respond:

```powershell
.venv/Scripts/python.exe manage.py pending
.venv/Scripts/python.exe manage.py reply 1 --message "Your factual response and evidence location."
.venv/Scripts/python.exe manage.py validate-ledger
```

Only the operator's command line can publish responses, marked **Platform team**. Verified charity accounts, recipient replies and external timestamp anchors are future work. References to DonorsChoose, GlobalGiving and Giveth are design references, not partnerships.

## Data and deployment

- Guest work stays in Streamlit session state; a browser reload or server restart can lose it. JSON export is available; import/recovery is not implemented.
- For signed-in users, extracted text and records are stored in `data/studybridge.sqlite`. Raw upload bytes are not written by the app. Set `STUDYBRIDGE_DB_PATH` to a persistent private path if needed.
- No shared cache holds private course material. Workspaces are loaded only after password authentication. Users can delete their accounts and related feedback. Password recovery is not implemented.
- Do not deploy the local SQLite prototype across multiple replicas or depend on ephemeral hosting disks. Public operation needs HTTPS, persistent storage, tested backups, account recovery, retention policies and stronger throttling.
- Streamlit Community Cloud can run the entrypoint `yifan_studybridge/app.py` with this folder's requirements, but local disk persistence is not guaranteed. The full private-account experience needs durable storage.
- No verified OCR accuracy, free-form hand-written grading, comprehensive syllabus coverage or guaranteed parallel-paper difficulty is claimed.

The original worksheet PNGs in `assets/worksheets/` can be regenerated with `scripts/build_worksheet_samples.py` using the development-only Playwright dependency and an installed Edge browser. Runtime use does not require a browser renderer.

## Tests

```powershell
.venv/Scripts/python.exe -m pip install pytest
.venv/Scripts/python.exe -m pytest -q
```

Tests cover computed answer consistency, numerical input safety, grading, source quotation validation, frozen snapshots, calibration, PDF separation, account isolation, lockout, feedback moderation, sandbox refunds and Streamlit user flows. Optional browser QA uses Playwright and the installed Edge browser; it is a development tool, not a runtime dependency.

## Attribution

Practilume author: **Yifan Yan**. The app develops the product direction discussed for Explain It!, whose original team includes Yifan Yan, Meiyu Shen and Jiachen Yu. This independent extension does not reassign ownership of the team's earlier work. Roadmap items are not represented as completed achievements.



