# Practilume Streamlit update

This release updates the existing Streamlit deployment from its older review-driven prototype. Created by Yifan Yan.

## Available in this release

- The overview contains the full sample walkthrough; no separate demo navigation item.
- API connection precedes personal image reading and AI exam generation. Personal keys are held only in the server session, never in workspace exports.
- PNG/JPEG uploads are transcribed and organised into concept summaries and formulas. Students name or choose a course; manual transcription, topic confirmation and review checkboxes are not required.
- Original image bytes are retained unchanged in saved workspace records, with downloads alongside extracted text.
- A mistake board stores self-reported difficulties and AI reference solutions with review status.
- AI papers use course materials, a school/system/grade brief, past-paper image references, recent questions and review history. A second AI pass reviews each paper; structural checks reject incorrect question counts, total marks and exact repeated prompts.
- Students can save written working and review suggested solutions. These papers are not automatically graded and do not produce verified mastery scores.
- The impact page includes fictional CSV records, example receipts and acknowledgements, and a separate interactive explanation of cryptographic hash chaining.

## Remaining differences from the Sites application

- No ChatGPT sign-in or automatic migration of Sites accounts, courses or original images.
- Existing local accounts still use SQLite. Streamlit Community Cloud local files can disappear after redeployment or restart. Export records; this is not durable cloud account storage.
- Personal API keys must be entered again after the server session ends. They are not persisted insecurely to disk.
- This release does not search the web for curriculum references. Course materials and supplied exam references determine the requested level.
- Uploads in the new workflow accept PNG/JPEG; broader document formats and Sites-specific user flows are not yet migrated.
- Paid checkout, donations and blockchain anchoring remain unimplemented. Financial examples are fictional.

## Deployment

The existing Community Cloud app uses repository `allanzhang721/studybridge-yifan`, branch `main`, entrypoint `app.py`. Pushing this repository triggers its deployment workflow. Its observed custom subdomain was `smartstudybridge`; changing it to `practilume` is a separate dashboard action, subject to availability.

No Sites runtime secrets or private student data should be copied into this repository.
