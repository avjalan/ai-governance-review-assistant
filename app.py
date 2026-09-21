import os
import json
import hashlib
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from review_validation import validate_assessment
from interview import QUESTIONS, HELP, to_form_values
try:
    from pdf_report import build_pdf_report
except ImportError:
    build_pdf_report = None


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="LaunchGate",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error(
        "GROQ_API_KEY was not found. "
        "Add it to your .env file or deployment secrets."
    )
    st.stop()

client = Groq(api_key=api_key)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1040px;
            padding-top: 3.5rem;
            padding-bottom: 4rem;
        }

        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 90% 0%, #27214d 0, transparent 35%),
                        linear-gradient(145deg, #090a12 0%, #111321 55%, #171329 100%);
            color: #f4f2ff;
        }

        [data-testid="stForm"] {
            background: rgba(24, 25, 42, .88);
            border: 1px solid rgba(171, 151, 255, .22);
            border-radius: 22px;
            padding: 1.4rem;
            box-shadow: 0 24px 70px rgba(0, 0, 0, .28);
            animation: questionIn .42s cubic-bezier(.2,.8,.2,1);
        }

        @keyframes questionIn {
            from { opacity: 0; transform: translateY(16px) scale(.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        h1, h2, h3, p, label, [data-testid="stCaptionContainer"] { color: #f4f2ff !important; }
        [data-testid="stCaptionContainer"], .subtitle { color: #aaa8bc !important; }
        [data-baseweb="select"] > div, textarea, input {
            background: #121420 !important;
            color: #f4f2ff !important;
            border-color: #35364b !important;
        }

        h1 {
            letter-spacing: -0.04em;
            font-weight: 700;
        }

        h2, h3 {
            letter-spacing: -0.02em;
        }

        .subtitle {
            font-size: 1.08rem;
            color: #aaa8bc;
            max-width: 850px;
            margin-bottom: 1rem;
        }

        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.73rem;
            font-weight: 700;
            color: #b7a2ff;
            margin: .5rem 0 1rem;
            line-height: 1.6;
        }

        .trust-map {
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 16px;
            padding: 18px 20px;
            margin-top: 8px;
            margin-bottom: 16px;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18);
            padding: 14px;
            border-radius: 15px;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 12px;
            min-height: 2.8rem;
            transition: transform .16s ease, box-shadow .16s ease;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(58, 35, 120, .12);
        }

        button[kind="primary"] {
            background: linear-gradient(90deg, #7657ff, #9e6cff);
            border-color: #8a68ff;
        }

        [data-testid="stMetric"] { background: rgba(23, 24, 39, .75); }
        [data-testid="stTabs"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def make_review_id(use_case_text: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = f"{use_case_text}-{timestamp}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"LG-{digest}"


def normalize_score(value):
    try:
        score = float(value)
        return max(0.0, min(10.0, score))
    except (TypeError, ValueError):
        return 0.0


def score_label(score):
    score = normalize_score(score)

    if score <= 2:
        return "Low"
    if score <= 5:
        return "Moderate"
    if score <= 8:
        return "High"

    return "Critical"


def safe_list(value):
    return value if isinstance(value, list) else []


def build_risk_reduction_options(intake, domains):
    """Translate elevated risks into concrete controls and architecture choices."""
    options = []
    scores = {name: normalize_score(value.get("score", 0)) for name, value in domains.items() if isinstance(value, dict)}
    if scores.get("privacy", 0) >= 6:
        options.append({"title": "Reduce data exposure", "action": "Remove unnecessary personal data, redact inputs, shorten retention, and use an approved zero-retention enterprise endpoint. If the use case permits it, evaluate a company-hosted or on-device model."})
    if scores.get("ai_security", 0) >= 6 or scores.get("security", 0) >= 6:
        options.append({"title": "Limit what the AI can reach", "action": "Give it the minimum permissions, isolate untrusted content, require approval before tool actions, and test prompt-injection and data-exfiltration scenarios."})
    if scores.get("reliability", 0) >= 6:
        options.append({"title": "Narrow and verify the task", "action": "Ground answers in approved sources, show citations, test representative cases, and require a person to check consequential output. Compare models on your own evaluation set before switching."})
    if scores.get("compliance", 0) >= 6:
        options.append({"title": "Add accountable review", "action": "Document the purpose, owner, affected people, appeal path, and approval record. Route the use case to the appropriate legal, privacy, HR, or compliance reviewer."})
    if scores.get("intellectual_property", 0) >= 6:
        options.append({"title": "Control source and output rights", "action": "Use approved or licensed source material, record provenance, restrict reuse of protected content, and review outputs before publication."})
    if intake.get("model_source") == "Third-party cloud model" and (intake.get("provider_retention") == "Unknown" or intake.get("training_use") == "Unknown"):
        options.append({"title": "Verify the provider before choosing a model", "action": "Confirm retention, training use, regional processing, access controls, and deletion terms. Prefer an approved enterprise configuration; consider private hosting or on-device inference when the data sensitivity justifies it."})
    if not options:
        options.append({"title": "Keep the review valid", "action": "Document the owner, test the intended workflow, monitor changes, and run a new review whenever the data, model, audience, or permissions change."})
    return options[:4]


def is_unknown(value):
    return value in {
        "Unknown",
        "Not decided",
        "Not sure",
        "Not provided",
        "Partially",
    }


def render_domain(name, domain):

    score = normalize_score(
        domain.get("score", 0)
    )

    left, right = st.columns(
        [1, 4]
    )

    with left:
        st.metric(
            name,
            f"{score:.1f}/10"
        )

        st.caption(
            score_label(score)
        )

    with right:

        st.write(
            domain.get(
                "rationale",
                "No rationale provided."
            )
        )

        triggers = safe_list(
            domain.get("triggers")
        )

        if triggers:

            st.markdown(
                "**Why this was flagged**"
            )

            for trigger in triggers:
                st.write(
                    f"• {trigger}"
                )

        with st.expander(
            "Risks and safeguards"
        ):

            risks = safe_list(
                domain.get("risks")
            )

            safeguards = safe_list(
                domain.get("safeguards")
            )

            st.markdown(
                "**Risks**"
            )

            if risks:

                for item in risks:
                    st.write(
                        f"• {item}"
                    )

            else:

                st.caption(
                    "None identified."
                )

            st.markdown(
                "**Suggested safeguards**"
            )

            if safeguards:

                for item in safeguards:
                    st.write(
                        f"• {item}"
                    )

            else:

                st.caption(
                    "None identified."
                )


# ============================================================
# DETERMINISTIC EVIDENCE RULES
# ============================================================

def build_deterministic_evidence_requirements(
    intake
):

    requirements = []

    def add(
        question,
        why_it_matters,
        owner,
        evidence_type,
    ):

        requirements.append(
            {
                "question": question,
                "why_it_matters": why_it_matters,
                "owner": owner,
                "evidence_type": evidence_type,
            }
        )

    if (
        intake["model_source"]
        == "Third-party cloud model"
    ):

        if is_unknown(
            intake["provider_retention"]
        ):

            add(
                "Verify the provider's input-retention behavior.",
                (
                    "Retention changes the privacy, "
                    "confidentiality, and IP exposure of "
                    "data sent to the model."
                ),
                "Privacy / Vendor Management",
                "Vendor documentation",
            )

        if is_unknown(
            intake["training_use"]
        ):

            add(
                (
                    "Verify whether submitted data "
                    "can be used for provider model training."
                ),
                (
                    "Training use changes the risk of "
                    "secondary use of confidential or "
                    "personal information."
                ),
                "Legal / Privacy",
                "Vendor documentation",
            )

    if (
        intake["untrusted_content"]
        != "No"
    ):

        add(
            (
                "Document and test how untrusted content "
                "is isolated from trusted model instructions."
            ),
            (
                "Untrusted content can introduce "
                "prompt-injection and instruction-confusion risks."
            ),
            "AI Engineering / Security",
            "Architecture evidence + test result",
        )

    if intake["logging"] in {
        "Partially",
        "No",
        "Not decided",
    }:

        add(
            (
                "Define the audit and investigation "
                "logging posture."
            ),
            (
                "Weak or undefined logging can reduce "
                "incident investigation and "
                "change-tracking capability."
            ),
            "Security / Operations",
            "Architecture evidence",
        )

    if (
        intake["decision_impact"]
        in {
            "Provides recommendations",
            "Materially influences decisions",
            "Makes automated decisions",
            "Not sure",
        }
        and intake["human_review"]
        in {
            "Sometimes",
            "No",
            "Not decided",
        }
    ):

        add(
            (
                "Define a human-review and escalation "
                "policy for consequential outputs."
            ),
            (
                "The impact of incorrect model output "
                "increases when human oversight is "
                "inconsistent or absent."
            ),
            "Business Owner / Legal",
            "Policy",
        )

    if intake["agentic_capability"] in {
        "Can modify data",
        "Can call tools / APIs",
        "Can trigger real-world actions",
        "Not decided",
    }:

        add(
            (
                "Document the system's authorization "
                "and tool-permission boundaries."
            ),
            (
                "Action-taking systems require explicit "
                "limits on what the model can read, "
                "change, or invoke."
            ),
            "Engineering / Security",
            "Architecture evidence",
        )

    return requirements


# ============================================================
# ASSUMPTION REGISTRY
# ============================================================

def build_assumption_registry(
    intake
):

    assumptions = []

    def add(
        assumption_id,
        assumption,
        value,
        status,
        owner,
    ):

        assumptions.append(
            {
                "id": assumption_id,
                "assumption": assumption,
                "value": value,
                "status": status,
                "owner": owner,
                "material_if_changed": True,
            }
        )

    add(
        "A1",
        (
            "Human oversight remains "
            "configured as declared."
        ),
        intake["human_review"],
        "Declared in intake",
        "Business Owner / Legal",
    )

    add(
        "A2",
        (
            "The model's action-taking capability "
            "remains within the declared boundary."
        ),
        intake["agentic_capability"],
        "Declared in intake",
        "Engineering / Security",
    )

    add(
        "A3",
        (
            "Third-party retention behavior "
            "remains as declared."
        ),
        intake["provider_retention"],
        (
            "Evidence required"
            if is_unknown(
                intake["provider_retention"]
            )
            else "Declared in intake"
        ),
        "Privacy / Vendor Management",
    )

    add(
        "A4",
        (
            "Provider training use "
            "remains as declared."
        ),
        intake["training_use"],
        (
            "Evidence required"
            if is_unknown(
                intake["training_use"]
            )
            else "Declared in intake"
        ),
        "Legal / Privacy",
    )

    add(
        "A5",
        (
            "Output exposure remains "
            "within the declared audience."
        ),
        intake["external_visibility"],
        "Declared in intake",
        "Product / Legal",
    )

    add(
        "A6",
        (
            "The system continues to process "
            "the same data classes."
        ),
        ", ".join(
            intake["data_types"]
        ),
        "Declared in intake",
        "Privacy / Security",
    )

    add(
        "A7",
        (
            "The system continues to handle "
            "untrusted content as declared."
        ),
        intake["untrusted_content"],
        (
            "Evidence required"
            if is_unknown(
                intake["untrusted_content"]
            )
            else "Declared in intake"
        ),
        "Security Engineering",
    )

    add(
        "A8",
        (
            "Audit and investigation logging "
            "remains as declared."
        ),
        intake["logging"],
        (
            "Evidence required"
            if is_unknown(
                intake["logging"]
            )
            else "Declared in intake"
        ),
        "Security / Operations",
    )

    add(
        "A9",
        (
            "The system's role in decisions "
            "about people remains as declared."
        ),
        intake["decision_impact"],
        (
            "Evidence required"
            if is_unknown(
                intake["decision_impact"]
            )
            else "Declared in intake"
        ),
        "Legal / Business Owner",
    )

    return assumptions


# ============================================================
# DETERMINISTIC DEPLOYMENT GATE
# ============================================================

def deterministic_gate(
    intake,
    scores,
    evidence_requirements,
):

    reasons = []

    sensitive_data = (
        (
            "Sensitive personal information"
            in intake["data_types"]
        )
        or (
            "Potentially regulated data"
            in intake["data_types"]
        )
    )

    weak_human_review = (
        intake["human_review"]
        in {
            "No",
            "Sometimes",
            "Not decided",
        }
    )

    powerful_actions = (
        intake["agentic_capability"]
        in {
            "Can modify data",
            "Can call tools / APIs",
            "Can trigger real-world actions",
            "Not decided",
        }
    )

    automated_people_decision = (
        intake["decision_impact"]
        == "Makes automated decisions"
    )

    untrusted_inputs = (
        intake["untrusted_content"]
        != "No"
    )

    if (
        automated_people_decision
        and weak_human_review
    ):

        reasons.append(
            (
                "Automated decisions about people "
                "do not have a defined mandatory "
                "human-review step."
            )
        )

    if (
        powerful_actions
        and untrusted_inputs
        and weak_human_review
    ):

        reasons.append(
            (
                "The system can take consequential "
                "actions while processing untrusted "
                "content without a strong "
                "human-review boundary."
            )
        )

    if (
        sensitive_data
        and intake["model_source"]
        == "Third-party cloud model"
        and is_unknown(
            intake["provider_retention"]
        )
        and is_unknown(
            intake["training_use"]
        )
    ):

        reasons.append(
            (
                "Sensitive data crosses a third-party "
                "boundary while both retention and "
                "training-use behavior remain unresolved."
            )
        )

    if reasons:

        return (
            "BLOCKED",
            reasons,
        )

    if evidence_requirements:

        return (
            "EVIDENCE REQUIRED",
            [
                (
                    f"{len(evidence_requirements)} "
                    "material evidence item(s) must "
                    "be resolved before the review "
                    "is complete."
                )
            ],
        )

    high_count = sum(
        normalize_score(score) >= 6
        for score in scores
    )

    if high_count >= 1:

        return (
            "CONDITIONAL",
            [
                (
                    "Material risk requires mitigation "
                    "and specialist review before launch."
                )
            ],
        )

    return (
        "READY FOR REVIEW",
        [
            (
                "No deterministic blocker or unresolved "
                "evidence requirement was detected."
            )
        ],
    )


# ============================================================
# CHANGE IMPACT
# ============================================================

def compare_intakes(
    previous,
    current,
):

    if not previous:
        return []

    fields = {
        "model_source": "Model architecture",
        "external_visibility": "Output exposure",
        "human_review": "Human review",
        "decision_impact": "Decision impact",
        "agentic_capability": "Action capability",
        "provider_retention": "Provider retention",
        "training_use": "Provider training use",
        "untrusted_content": "Untrusted content",
        "logging": "Logging",
        "data_types": "Data classification",
    }

    changes = []

    for field, label in fields.items():

        before = previous.get(
            field
        )

        after = current.get(
            field
        )

        if before != after:

            impact = "Medium"

            explanation = (
                "A material deployment assumption changed."
            )

            if field in {
                "human_review",
                "decision_impact",
                "agentic_capability",
                "provider_retention",
                "training_use",
                "untrusted_content",
                "data_types",
            }:

                impact = "High"

            changes.append(
                {
                    "label": label,
                    "before": before,
                    "after": after,
                    "impact": impact,
                    "explanation": explanation,
                }
            )

    return changes


# ============================================================
# SESSION STATE / DEMO
# ============================================================

if "last_intake" not in st.session_state:
    st.session_state.last_intake = None

if "demo_values" not in st.session_state:
    st.session_state.demo_values = {}


def load_demo():

    st.session_state.demo_values = {

        "use_case": (
            "Internal assistant that summarizes commercial agreements, "
            "identifies unusual clauses, and recommends sections "
            "requiring attorney review."
        ),

        "users": (
            "Legal operations and corporate attorneys"
        ),

        "business_owner": "Legal",

        "data_description": (
            "Confidential commercial contracts, supplier information, "
            "employee contact information, and internal legal guidance."
        ),

        "deployment_environment": (
            "Internal tool"
        ),

        "lifecycle_stage": (
            "Prototype"
        ),

        "personal": True,

        "sensitive_personal": False,

        "confidential": True,

        "customer": False,

        "financial": False,

        "regulated": False,

        "model_source": (
            "Third-party cloud model"
        ),

        "model_provider": "Groq",

        "external_visibility": (
            "Internal users only"
        ),

        "human_review": (
            "Always"
        ),

        "decision_impact": (
            "Provides recommendations"
        ),

        "agentic_capability": (
            "No — output only"
        ),

        "provider_retention": (
            "Unknown"
        ),

        "training_use": (
            "No"
        ),

        "untrusted_content": (
            "Yes — documents"
        ),

        "logging": (
            "Yes"
        ),

        "additional_context": "",
    }


# ============================================================
# HEADER
# ============================================================

st.title(
    "LaunchGate"
)

st.markdown(
    """
    <div class="subtitle">
    Tell us how your team plans to use AI. We’ll ask a few questions,
    then show what needs attention before it goes live.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    (
        "AI use case review · About 5 minutes · A person makes the final decision"
    )
)

with st.expander("How LaunchGate reaches a recommendation"):
    st.markdown("""
    **1. Hard safety gates:** explicit rules block or pause uses with missing human oversight, powerful actions, sensitive data, or unresolved provider terms.

    **2. Six risk areas:** the AI analyzes privacy, security, AI security, reliability, intellectual property, and compliance on a 0-10 scale. Unknown facts become evidence requests rather than automatically becoming low risk.

    **3. Framework organization:** NIST AI RMF informs Govern, Map, Measure, and Manage activities; ISO/IEC 42001 informs ownership and lifecycle controls; OWASP guidance informs prompt injection, data disclosure, excessive agency, and other LLM-specific scenarios.

    **4. Human decision:** the score explains where to focus. It never grants launch approval or claims certification.
    """)

if "interview_answers" not in st.session_state:
    st.session_state.interview_answers = {}
if "interview_step" not in st.session_state:
    st.session_state.interview_step = 0
if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False

if not st.session_state.interview_complete:
    step = st.session_state.interview_step
    field, question, kind, options, required = QUESTIONS[step]
    saved = st.session_state.interview_answers.get(field)
    st.progress(step / len(QUESTIONS), text=f"Question {step + 1} of {len(QUESTIONS)}")
    st.subheader(question)
    if field in HELP:
        st.write(HELP[field])
    st.caption("For this demo, use fictional or public details. Avoid confidential documents.")
    with st.form(f"interview_question_{step}"):
        if kind == "text":
            answer = st.text_area("Your answer", value=saved or "", height=130)
        elif kind == "short":
            answer = st.text_input("Your answer", value=saved or "")
        elif kind == "multiple":
            answer = st.multiselect("Select all that apply", options, default=saved or [])
        elif kind == "profile":
            prior = saved or {}
            retention = st.selectbox("Can the AI provider keep submitted data?", ["Unknown", "Provider does not retain inputs", "Provider may retain inputs", "No third-party processing"], index=["Unknown", "Provider does not retain inputs", "Provider may retain inputs", "No third-party processing"].index(prior.get("provider_retention", "Unknown")))
            training = st.selectbox("Can submitted data be used to train models?", ["Unknown", "No", "Yes", "Not applicable"], index=["Unknown", "No", "Yes", "Not applicable"].index(prior.get("training_use", "Unknown")))
            logging = st.selectbox("Are interactions recorded for investigation?", ["Not decided", "Yes", "Partially", "No"], index=["Not decided", "Yes", "Partially", "No"].index(prior.get("logging", "Not decided")))
            untrusted_options = ["Unknown", "No", "Yes — documents", "Yes — websites", "Yes — email/messages", "Yes — user-generated content", "Multiple sources"]
            untrusted = st.selectbox("Will it read outside files, websites, messages, or user content?", untrusted_options, index=untrusted_options.index(prior.get("untrusted_content", "Unknown")))
            answer = {"provider_retention": retention, "training_use": training, "logging": logging, "untrusted_content": untrusted}
        else:
            answer = st.selectbox("Choose an answer", options, index=options.index(saved) if saved in options else 0)
        submitted = st.form_submit_button(
            "Generate review" if step == len(QUESTIONS) - 1 else "Next question",
            type="primary",
        )
    if step:
        if st.button("Previous question"):
            st.session_state.interview_step -= 1
            st.rerun()
    if submitted:
        if required and not answer.strip():
            st.warning("Please answer this question to continue.")
        else:
            st.session_state.interview_answers[field] = answer
            if step == len(QUESTIONS) - 1:
                st.session_state.demo_values = to_form_values(st.session_state.interview_answers)
                st.session_state.interview_complete = True
                st.session_state.interview_run = True
            else:
                st.session_state.interview_step += 1
            st.rerun()
    st.stop()

if st.button("Start a new interview"):
    st.session_state.interview_answers = {}
    st.session_state.interview_step = 0
    st.session_state.interview_complete = False
    st.session_state.demo_values = {}
    st.rerun()

st.caption("Your preliminary review is ready below. A person must verify evidence before any launch decision.")

d = st.session_state.demo_values


# The guided interview is the only employee-facing intake.
# Keep these values compatible with the existing review engine.
use_case = d.get("use_case", "")
users = d.get("users", "")
business_owner = d.get("business_owner", "Other")
data_description = d.get("data_description", "")
deployment_environment = d.get("deployment_environment", "Internal tool")
lifecycle_stage = d.get("lifecycle_stage", "Concept")
personal = d.get("personal", False)
sensitive_personal = d.get("sensitive_personal", False)
confidential = d.get("confidential", False)
customer = d.get("customer", False)
financial = d.get("financial", False)
regulated = d.get("regulated", False)
model_source = d.get("model_source", "Not decided")
model_provider = d.get("model_provider", "")
external_visibility = d.get("external_visibility", "Not decided")
human_review = d.get("human_review", "Not decided")
decision_impact = d.get("decision_impact", "Not sure")
agentic_capability = d.get("agentic_capability", "Not decided")
provider_retention = d.get("provider_retention", "Unknown")
training_use = d.get("training_use", "Unknown")
untrusted_content = d.get("untrusted_content", "Unknown")
logging = d.get("logging", "Not decided")
additional_context = d.get("additional_context", "")

with st.expander("Check your answers", expanded=False):
    st.write(f"**What it does:** {use_case}")
    st.write(f"**Who uses it:** {users or 'Not specified'}")
    st.write(f"**Information used:** {data_description}")
    st.write(f"**Human review:** {human_review}")
    st.write(f"**Model setup:** {model_source}")
    if st.button("Change an answer"):
        st.session_state.interview_step = 0
        st.session_state.interview_complete = False
        st.rerun()

# ============================================================
# RUN REVIEW
# ============================================================

st.divider()

generate = st.button(
    "Run review again",
    type="primary",
    use_container_width=True,
) or st.session_state.pop("interview_run", False)


if generate:

    if not use_case.strip():

        st.warning(
            (
                "Describe the system purpose "
                "before running the review."
            )
        )

        st.stop()

    if not data_description.strip():

        st.warning(
            (
                "Describe the data processed "
                "before running the review."
            )
        )

        st.stop()

    selected_data_types = []

    if personal:
        selected_data_types.append(
            "Personal information"
        )

    if sensitive_personal:
        selected_data_types.append(
            "Sensitive personal information"
        )

    if confidential:
        selected_data_types.append(
            "Confidential company data"
        )

    if customer:
        selected_data_types.append(
            "Customer data"
        )

    if financial:
        selected_data_types.append(
            "Financial data"
        )

    if regulated:
        selected_data_types.append(
            "Potentially regulated data"
        )

    if not selected_data_types:
        selected_data_types.append(
            "None explicitly selected"
        )

    intake = {

        "use_case": (
            use_case.strip()
        ),

        "users": (
            users.strip()
            or "Not provided"
        ),

        "business_owner": (
            business_owner
        ),

        "deployment_environment": (
            deployment_environment
        ),

        "lifecycle_stage": (
            lifecycle_stage
        ),

        "data_description": (
            data_description.strip()
        ),

        "data_types": (
            selected_data_types
        ),

        "model_source": (
            model_source
        ),

        "model_provider": (
            model_provider.strip()
            or "Not provided"
        ),

        "external_visibility": (
            external_visibility
        ),

        "human_review": (
            human_review
        ),

        "decision_impact": (
            decision_impact
        ),

        "agentic_capability": (
            agentic_capability
        ),

        "provider_retention": (
            provider_retention
        ),

        "training_use": (
            training_use
        ),

        "untrusted_content": (
            untrusted_content
        ),

        "logging": (
            logging
        ),

        "additional_context": (
            additional_context.strip()
            or "Not provided"
        ),
    }

    review_id = make_review_id(
        use_case
    )

    deterministic_evidence = (
        build_deterministic_evidence_requirements(
            intake
        )
    )

    assumptions = (
        build_assumption_registry(
            intake
        )
    )

    changes = compare_intakes(
        st.session_state.last_intake,
        intake,
    )


    # ========================================================
    # MODEL PROMPT
    # ========================================================

    system_prompt = """
You are an AI security and launch-readiness analyst.

You are NOT the policy engine.
You do NOT approve or block launch.
You do NOT create mandatory organizational requirements.

The application already applies deterministic governance rules.

Your job is to add probabilistic analysis that is useful to engineers:
- system-specific failure scenarios
- AI-security threats
- reliability risks
- evidence gaps
- evaluation ideas
- proportional safeguards
- human review needs
- continuous conditions worth monitoring

RULES

1. Separate facts from unknowns.

2. Never claim an unknown vendor behavior is true or false.

3. Never accuse a vendor of retaining, training on,
   leaking, or misusing data without evidence.

4. Never invent numeric thresholds, frequencies,
   retention periods, encryption versions, SLAs,
   or benchmark requirements.

5. If a threshold is needed but not supplied, write:
   "Threshold must be defined by the system owner."

6. Never claim a system prompt is impossible to override.

7. For prompt injection, recommend separating
   trusted instructions from untrusted content,
   minimizing privileges, testing adversarial inputs,
   and monitoring behavior.

8. Do not state that a specific law conclusively applies.

9. Keep recommendations technically credible
   and proportional to the declared architecture.

10. Prefer verifiable statements and tests
    over generic compliance language.

RISK SCALE

0-2 = Low
3-5 = Moderate
6-8 = High
9-10 = Critical

Unknown information belongs in missing_evidence.

Do not inflate scores merely because
information is unknown.

Return ONLY valid JSON.
"""


    user_prompt = f"""
Analyze this system:

{json.dumps(intake, indent=2)}

Return JSON with EXACTLY this structure:

{{
  "executive_summary": "2-4 sentence summary",

  "risk_domains": {{

    "privacy": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }},

    "security": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }},

    "intellectual_property": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }},

    "compliance": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }},

    "reliability": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }},

    "ai_security": {{
      "score": 0,
      "rationale": "",
      "triggers": [],
      "risks": [],
      "safeguards": []
    }}
  }},

  "missing_evidence": [
    {{
      "question": "",
      "why_it_matters": "",
      "owner": "",
      "evidence_type": ""
    }}
  ],

  "threat_scenarios": [
    {{
      "scenario": "",
      "impact": "",
      "mitigation": "",
      "test": ""
    }}
  ],

  "evaluation_plan": [
    {{
      "test": "",
      "success_criterion": "",
      "failure_action": ""
    }}
  ],

  "required_reviews": [
    {{
      "reviewer": "",
      "reason": "",
      "required_before_launch": true
    }}
  ],

  "human_checkpoints": [
    {{
      "checkpoint": "",
      "owner": "",
      "trigger": ""
    }}
  ],

  "continuous_controls": [
    {{
      "condition": "",
      "why_it_matters": "",
      "monitor": ""
    }}
  ],

  "recommended_actions": [
    {{
      "priority": "P0 / P1 / P2",
      "action": "",
      "owner": ""
    }}
  ]
}}

THREAT MODEL REQUIREMENTS

Threat scenarios must be specific
to this exact architecture.

For systems processing untrusted documents,
consider indirect prompt injection,
instruction confusion,
malicious formatting,
retrieval contamination,
and data disclosure.

For systems with tool access,
consider excessive agency,
privilege boundaries,
unauthorized actions,
and data exfiltration.

Do not invent vendor misconduct.

Frame vendor uncertainty as an
assumption or verification need.

EVALUATION REQUIREMENTS

Turn important risks into tests
where practical.

Do not invent percentages.

Do not invent arbitrary numerical
acceptance criteria.

If an acceptance threshold is not supplied, use:

"Threshold must be defined by the system owner."

Be concise and technically specific.
"""


    # ========================================================
    # CALL MODEL
    # ========================================================

    try:

        with st.spinner(
            (
                "Analyzing system risks "
                "and launch readiness..."
            )
        ):

            response = (
                client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    temperature=0.1,
                    response_format={
                        "type": "json_object"
                    },
                )
            )

        result = validate_assessment(json.loads(
            response
            .choices[0]
            .message
            .content
        ))

    except json.JSONDecodeError:

        st.error(
            (
                "The model returned an invalid "
                "structured response. "
                "Run the review again."
            )
        )

        st.stop()

    except ValueError as error:
        st.error(f"The model returned an incomplete assessment: {error} Please run the review again.")
        st.stop()

    except Exception:

        st.error(
            (
                "Unable to generate "
                "the review. Check the API key, selected model, and provider availability, then retry."
            )
        )

        st.stop()


    # ========================================================
    # RESULTS DATA
    # ========================================================

    domains = result.get(
        "risk_domains",
        {},
    )

    privacy_score = normalize_score(
        domains
        .get("privacy", {})
        .get("score", 0)
    )

    security_score = normalize_score(
        domains
        .get("security", {})
        .get("score", 0)
    )

    ip_score = normalize_score(
        domains
        .get("intellectual_property", {})
        .get("score", 0)
    )

    compliance_score = normalize_score(
        domains
        .get("compliance", {})
        .get("score", 0)
    )

    reliability_score = normalize_score(
        domains
        .get("reliability", {})
        .get("score", 0)
    )

    ai_security_score = normalize_score(
        domains
        .get("ai_security", {})
        .get("score", 0)
    )

    scores = [
        privacy_score,
        security_score,
        ip_score,
        compliance_score,
        reliability_score,
        ai_security_score,
    ]


    model_evidence = safe_list(
        result.get(
            "missing_evidence"
        )
    )

    combined_evidence = (
        deterministic_evidence[:]
    )

    existing_questions = {
        item.get(
            "question",
            "",
        ).strip().lower()

        for item
        in combined_evidence
    }

    for item in model_evidence:

        question = (
            item.get(
                "question",
                "",
            ).strip()
        )

        if (
            question
            and question.lower()
            not in existing_questions
        ):

            combined_evidence.append(
                item
            )

            existing_questions.add(
                question.lower()
            )


    gate, gate_reasons = (
        deterministic_gate(
            intake,
            scores,
            deterministic_evidence,
        )
    )

    reduction_options = build_risk_reduction_options(intake, domains)


    # ========================================================
    # LAUNCH DECISION
    # ========================================================

    st.divider()

    st.markdown(
        (
            f'<div class="eyebrow">'
            f'Review {review_id}'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )

    st.header("Your review")


    if gate == "BLOCKED":

        st.error("Do not launch yet · A critical safeguard is missing")

    elif gate == "EVIDENCE REQUIRED":

        st.warning("More information needed before review")

    elif gate == "CONDITIONAL":

        st.warning("Specialist review and safeguards needed")

    else:

        st.success("Ready for a person's review")


    st.caption(
        (
            "This is a preliminary recommendation based on your answers. "
            "It does not grant permission to launch."
        )
    )

    for reason in gate_reasons:

        st.write(
            f"• {reason}"
        )


    st.write(
        result.get(
            "executive_summary",
            "",
        )
    )

    st.subheader("What to do next")
    for index, option in enumerate(reduction_options, start=1):
        st.markdown(f"**{index}. {option['title']}**")
        st.write(option["action"])

    st.caption("A different model can reduce some privacy, security, cost, or performance risks, but it cannot fix an unsafe workflow by itself. Compare candidate models using your own data, tests, and vendor terms.")


    # ========================================================
    # CHANGE IMPACT
    # ========================================================

    if changes:

        st.warning(
            (
                "Material changes detected since "
                "the previous review in this "
                "browser session."
            )
        )

        with st.expander(
            "View change-impact analysis"
        ):

            for item in changes:

                st.markdown(
                    (
                        f"**{item['impact']} impact · "
                        f"{item['label']}**"
                    )
                )

                st.write(
                    f"Before: {item['before']}"
                )

                st.write(
                    f"After: {item['after']}"
                )

                st.caption(
                    item["explanation"]
                )

                st.divider()


    # ========================================================
    # RISK SURFACE
    # ========================================================

    st.subheader("Areas to check")

    a, b, c = st.columns(
        3
    )

    with a:

        st.metric(
            "Privacy",
            f"{privacy_score:.1f}/10",
            score_label(
                privacy_score
            ),
        )

        st.metric(
            "Security",
            f"{security_score:.1f}/10",
            score_label(
                security_score
            ),
        )

    with b:

        st.metric(
            "AI Security",
            f"{ai_security_score:.1f}/10",
            score_label(
                ai_security_score
            ),
        )

        st.metric(
            "Reliability",
            f"{reliability_score:.1f}/10",
            score_label(
                reliability_score
            ),
        )

    with c:

        st.metric(
            "IP",
            f"{ip_score:.1f}/10",
            score_label(
                ip_score
            ),
        )

        st.metric(
            "Compliance",
            f"{compliance_score:.1f}/10",
            score_label(
                compliance_score
            ),
        )


    (
        risk_tab,
        assumptions_tab,
        evidence_tab,
        threat_tab,
        eval_tab,
        workflow_tab,
        controls_tab,
    ) = st.tabs(
        [
            "Potential risks",
            "What we assumed",
            "Information needed",
            "What could go wrong",
            "Tests to run",
            "People to involve",
            "After launch",
        ]
    )


    # ========================================================
    # RISK ANALYSIS
    # ========================================================

    with risk_tab:

        render_domain(
            "Privacy",
            domains.get(
                "privacy",
                {},
            ),
        )

        st.divider()

        render_domain(
            "Security",
            domains.get(
                "security",
                {},
            ),
        )

        st.divider()

        render_domain(
            "AI Security",
            domains.get(
                "ai_security",
                {},
            ),
        )

        st.divider()

        render_domain(
            "Reliability",
            domains.get(
                "reliability",
                {},
            ),
        )

        st.divider()

        render_domain(
            "Intellectual Property",
            domains.get(
                "intellectual_property",
                {},
            ),
        )

        st.divider()

        render_domain(
            "Compliance",
            domains.get(
                "compliance",
                {},
            ),
        )


    # ========================================================
    # ASSUMPTIONS
    # ========================================================

    with assumptions_tab:

        st.subheader(
            "Assumption registry"
        )

        st.caption(
            (
                "The review remains valid only while "
                "these system conditions remain true."
            )
        )

        for item in assumptions:

            st.markdown(
                (
                    f"**{item['id']} · "
                    f"{item['assumption']}**"
                )
            )

            st.write(
                (
                    "Current value: "
                    f"{item['value']}"
                )
            )

            st.caption(
                (
                    f"Status: {item['status']} · "
                    f"Owner: {item['owner']}"
                )
            )

            st.divider()


    # ========================================================
    # EVIDENCE
    # ========================================================

    with evidence_tab:

        st.subheader(
            "Evidence required"
        )

        if not combined_evidence:

            st.success(
                (
                    "No material evidence gaps "
                    "were identified."
                )
            )

        else:

            for item in combined_evidence:

                with st.expander(
                    item.get(
                        "question",
                        "Evidence item",
                    )
                ):

                    st.write(
                        item.get(
                            "why_it_matters",
                            "",
                        )
                    )

                    st.caption(
                        (
                            "Owner: "
                            f"{item.get('owner', 'Not assigned')}"
                        )
                    )

                    st.caption(
                        (
                            "Evidence type: "
                            f"{item.get('evidence_type', 'Not specified')}"
                        )
                    )


    # ========================================================
    # THREAT MODEL
    # ========================================================

    with threat_tab:

        st.subheader(
            "Threat model"
        )

        threats = safe_list(
            result.get(
                "threat_scenarios"
            )
        )

        if not threats:

            st.caption(
                (
                    "No threat scenarios "
                    "were returned."
                )
            )

        for i, threat in enumerate(
            threats,
            start=1,
        ):

            st.markdown(
                (
                    f"### {i}. "
                    f"{threat.get('scenario', 'Threat scenario')}"
                )
            )

            st.markdown(
                "**Impact**"
            )

            st.write(
                threat.get(
                    "impact",
                    "",
                )
            )

            st.markdown(
                "**Mitigation**"
            )

            st.write(
                threat.get(
                    "mitigation",
                    "",
                )
            )

            st.markdown(
                "**Engineering test**"
            )

            st.write(
                threat.get(
                    "test",
                    "",
                )
            )

            st.divider()


    # ========================================================
    # EVALUATIONS
    # ========================================================

    with eval_tab:

        st.subheader(
            "Pre-launch evaluations"
        )

        st.caption(
            (
                "LaunchGate suggests what should "
                "be tested but does not invent "
                "acceptance thresholds."
            )
        )

        evaluations = safe_list(
            result.get(
                "evaluation_plan"
            )
        )

        if not evaluations:

            st.caption(
                (
                    "No evaluations "
                    "were returned."
                )
            )

        for item in evaluations:

            st.markdown(
                (
                    f"### "
                    f"{item.get('test', 'Evaluation')}"
                )
            )

            st.write(
                (
                    "Pass condition: "
                    f"{item.get('success_criterion', 'Not defined')}"
                )
            )

            st.write(
                (
                    "If it fails: "
                    f"{item.get('failure_action', 'Escalate for review')}"
                )
            )

            st.divider()


    # ========================================================
    # REVIEW WORKFLOW
    # ========================================================

    with workflow_tab:

        st.subheader(
            "Required reviewers"
        )

        reviews = safe_list(
            result.get(
                "required_reviews"
            )
        )

        if not reviews:

            st.caption(
                (
                    "No specialist reviews "
                    "were identified."
                )
            )

        for review in reviews:

            status = (
                "Required before launch"
                if review.get(
                    "required_before_launch"
                )
                else "Recommended"
            )

            st.markdown(
                (
                    f"**{review.get('reviewer', 'Reviewer')} "
                    f"— {status}**"
                )
            )

            st.write(
                review.get(
                    "reason",
                    "",
                )
            )

            st.divider()


        st.subheader(
            "Human checkpoints"
        )

        checkpoints = safe_list(
            result.get(
                "human_checkpoints"
            )
        )

        for checkpoint in checkpoints:

            st.markdown(
                (
                    f"**{checkpoint.get('checkpoint', 'Checkpoint')}**"
                )
            )

            st.write(
                checkpoint.get(
                    "trigger",
                    "",
                )
            )

            st.caption(
                (
                    "Owner: "
                    f"{checkpoint.get('owner', 'Not assigned')}"
                )
            )

            st.divider()


        st.subheader(
            "Recommended actions"
        )

        for action in safe_list(
            result.get(
                "recommended_actions"
            )
        ):

            st.markdown(
                (
                    f"**{action.get('priority', 'P2')} · "
                    f"{action.get('owner', 'Unassigned')}** — "
                    f"{action.get('action', '')}"
                )
            )


    # ========================================================
    # CONTINUOUS CONTROLS
    # ========================================================

    with controls_tab:

        st.subheader(
            "Continuous controls"
        )

        st.caption(
            (
                "If one of these conditions materially "
                "changes, the prior review may become stale."
            )
        )

        controls = safe_list(
            result.get(
                "continuous_controls"
            )
        )

        if not controls:

            st.caption(
                (
                    "No continuous controls "
                    "were returned."
                )
            )

        for item in controls:

            st.markdown(
                (
                    f"**{item.get('condition', 'Condition')}**"
                )
            )

            st.write(
                item.get(
                    "why_it_matters",
                    "",
                )
            )

            st.caption(
                (
                    "Monitor: "
                    f"{item.get('monitor', 'Not specified')}"
                )
            )

            st.divider()


    # ========================================================
    # EXPORT
    # ========================================================

    review_record = {

        "review_id": review_id,

        "generated_at_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "model": MODEL_NAME,

        "gate": gate,

        "gate_reasons": (
            gate_reasons
        ),

        "system": intake,

        "deterministic_evidence_requirements": (
            deterministic_evidence
        ),

        "assumption_registry": (
            assumptions
        ),

        "material_changes_since_previous_session_review": (
            changes
        ),

        "assessment": result,
    }


    st.divider()

    st.subheader("Take the review with you")

    if build_pdf_report:
        pdf_bytes = build_pdf_report(review_record, reduction_options)
        st.download_button(
            "Download detailed PDF report",
            data=pdf_bytes,
            file_name=f"{review_id.lower()}-launchgate-report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    else:
        st.info("PDF downloads require the reportlab package. Install the project requirements, then restart the app.")

    with st.expander("Technical export"):
        st.download_button(
            "Download JSON",
            data=json.dumps(review_record, indent=2),
            file_name=f"{review_id.lower()}-launch-review.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption(
        (
            f"Model: {MODEL_NAME} · "
            f"Generated "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
            "Preliminary decision support only."
        )
    )

    st.session_state.last_intake = (
        intake
    )
