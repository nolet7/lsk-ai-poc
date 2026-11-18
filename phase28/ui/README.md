# P28-08 — Browser UI tasks

- [ ] TASK: build a small accessible interface to select domain (Sales, Marketing, Finance), enter a question and display mode/answer/authorized citations.
- [ ] TASK: design safe login/session handling. **Current POC demo API keys and X-Actor header are not enterprise authentication.** Never embed a shared gateway key in public JavaScript, HTML, browser localStorage or URL.
- [ ] TASK: prefer same-origin backend route/session proxy; no direct credentials sent to business app services from browser.
- [ ] TASK: add loading, timeout, empty-evidence, permission-denied, cost-disabled and error states.
- [ ] TASK: clearly label mock/retrieval-only vs live Bedrock inference. No fake AI output.
- [ ] TASK: show that answers never change transactions; approvals are separate and not implemented.
- [ ] TASK: add UI tests and screenshots to your PR.

Do not expose the POC on the public internet. Build locally first.
