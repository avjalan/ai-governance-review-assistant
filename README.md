# ⚖️ AI Governance Review Assistant

An AI-powered governance review tool that helps legal and business teams perform preliminary assessments of proposed AI systems.

## Features

- Guided 11-question intake with plain-language help and animated transitions
- Dark employee-facing interface with a concise recommendation and prioritized fixes
- Detailed downloadable PDF with evidence, tests, reviewers, threats, and framework notes
- 🤖 AI-generated governance assessments
- 🔒 Privacy risk analysis
- 🛡️ Security risk analysis
- ⚖️ Intellectual property review
- 📋 Compliance considerations
- 👤 Human review checkpoints
- 📊 Overall governance recommendation
- 📥 Downloadable assessment report

## Tech Stack

- Python
- Streamlit
- Groq API
- Configurable Groq model (default: `openai/gpt-oss-120b`)
- JSON
- python-dotenv

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create a `.env` file:

```text
GROQ_API_KEY=your_api_key_here
# Optional: GROQ_MODEL=your_available_model_id
```

## Disclaimer

This project is a prototype for preliminary AI governance decision support. It does not constitute legal advice.

## Current boundaries

- Reviews are generated in memory and downloaded manually. Reviewer checkboxes do not record an approval or route a task.
- Interview answers are held only in the active Streamlit session; refreshing or restarting may clear them. Users can return to an answer or begin a new interview. The legacy technical intake and system diagram are no longer shown.
- Scores are model judgments, not calibrated measurements. Missing or invalid risk scores now stop the review instead of silently becoming zero.
- The app sends the entered use case to the configured model provider. Use fictional or public examples for demonstrations; do not enter confidential documents or personal data without an approved data processing arrangement.
- A gate is preliminary guidance, not authorization to deploy. A qualified human owner must verify evidence and approve the system.

## How the framework works

LaunchGate separates deterministic safety gates from AI-assisted analysis. The model scores six domains from 0-10, while explicit rules control blockers and evidence requirements. NIST AI RMF provides the Govern/Map/Measure/Manage structure, ISO/IEC 42001 informs ownership and lifecycle controls, and OWASP LLM guidance informs application-security scenarios. These are organizing references only; the app does not claim certification or legal compliance.

Elevated scores produce risk-reduction actions. A model or deployment alternative is suggested only when it addresses the actual driver—for example, an approved zero-retention endpoint, private hosting, or on-device inference for data exposure. Model switching is never presented as a substitute for human oversight, permissions, testing, or process controls.

## Product roadmap

1. **Workflow:** authenticated organizations and roles; durable review versions; actual owner assignments, evidence attachments, approvals, and an immutable event history. Separate submitted facts, model suggestions, and verified evidence.
2. **Policy:** versioned, organization-specific rules and explicit overrides with rationale. Test every gate against representative scenarios before release. Keep the model advisory, with deterministic controls and human sign-off.
3. **Data protection:** tenant isolation, encryption, retention/deletion controls, redaction, provider configurations, and a security review. Never log secrets or full use cases by default.
4. **Validation:** pilot with real governance teams using approved synthetic or properly authorized data; measure reviewer time, missing evidence found, false positives, and agreement with human decisions.
5. **Commercial readiness:** confirm ownership and rights to code and design before licensing; establish support, deployment, procurement, and security documentation. Do not claim compliance certification or autonomous approval based on this prototype.

For a local connection check, run `python test_groq.py`. Both scripts use `GROQ_MODEL` when set, so they check the same model.
