import os
import json
import hashlib
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from groq import Groq


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

MODEL_NAME = "openai/gpt-oss-120b"

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
            max-width: 1180px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
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
            color: #666;
            max-width: 850px;
            margin-bottom: .5rem;
        }

        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.73rem;
            font-weight: 700;
            color: #777;
            margin-bottom: 0.25rem;
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
            border-radius: 10px;
        }
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

st.markdown(
    (
        '<div class="eyebrow">'
        'Continuous AI Launch Readiness'
        '</div>'
    ),
    unsafe_allow_html=True,
)

st.title(
    "LaunchGate"
)

st.markdown(
    """
    <div class="subtitle">
    Turn an AI system into an explainable deployment decision:
    what could fail, what evidence is missing, what must be tested,
    and which assumptions must remain true after launch.
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    (
        "Prototype · Preliminary decision support · "
        "Human approval required"
    )
)

demo_col, _ = st.columns(
    [1, 4]
)

with demo_col:

    st.button(
        "Load Demo Scenario",
        on_click=load_demo,
        use_container_width=True,
    )

d = st.session_state.demo_values


# ============================================================
# 1. DEFINE SYSTEM
# ============================================================

st.header(
    "1. Define the system"
)

left, right = st.columns(
    2
)

with left:

    use_case = st.text_area(
        "System purpose *",
        value=d.get(
            "use_case",
            "",
        ),
        height=145,
        placeholder=(
            "Describe what the AI "
            "system is intended to do."
        ),
    )

    users = st.text_input(
        "Primary users",
        value=d.get(
            "users",
            "",
        ),
        placeholder=(
            "Example: Legal operations "
            "and corporate attorneys"
        ),
    )

    business_options = [
        "Legal",
        "Engineering",
        "Security",
        "Privacy",
        "HR",
        "Finance",
        "Operations",
        "Customer Support",
        "Other",
    ]

    business_owner = st.selectbox(
        "Business owner",
        business_options,
        index=business_options.index(
            d.get(
                "business_owner",
                "Legal",
            )
        ),
    )

with right:

    data_description = st.text_area(
        "Data processed *",
        value=d.get(
            "data_description",
            "",
        ),
        height=145,
        placeholder=(
            "Describe the information "
            "the system will process."
        ),
    )

    deployment_options = [
        "Internal tool",
        "Employee-facing product",
        "Customer-facing product",
        "Public-facing experience",
        "Developer tool",
        "Research / experiment",
    ]

    deployment_environment = st.selectbox(
        "Deployment environment",
        deployment_options,
        index=deployment_options.index(
            d.get(
                "deployment_environment",
                "Internal tool",
            )
        ),
    )

    lifecycle_options = [
        "Concept",
        "Prototype",
        "Pilot",
        "Pre-production",
        "Production",
    ]

    lifecycle_stage = st.selectbox(
        "Current stage",
        lifecycle_options,
        index=lifecycle_options.index(
            d.get(
                "lifecycle_stage",
                "Concept",
            )
        ),
    )


st.subheader(
    "Data classification"
)

c1, c2, c3 = st.columns(
    3
)

with c1:

    personal = st.checkbox(
        "Personal information",
        value=d.get(
            "personal",
            False,
        ),
    )

    sensitive_personal = st.checkbox(
        "Sensitive personal information",
        value=d.get(
            "sensitive_personal",
            False,
        ),
    )

with c2:

    confidential = st.checkbox(
        "Confidential company data",
        value=d.get(
            "confidential",
            False,
        ),
    )

    customer = st.checkbox(
        "Customer data",
        value=d.get(
            "customer",
            False,
        ),
    )

with c3:

    financial = st.checkbox(
        "Financial data",
        value=d.get(
            "financial",
            False,
        ),
    )

    regulated = st.checkbox(
        "Potentially regulated data",
        value=d.get(
            "regulated",
            False,
        ),
    )


# ============================================================
# 2. MAP AI BEHAVIOR
# ============================================================

st.divider()

st.header(
    "2. Map the AI behavior"
)

left, right = st.columns(
    2
)

with left:

    model_options = [
        "Third-party cloud model",
        "Company-hosted model",
        "On-device model",
        "Hybrid / multiple models",
        "Not decided",
    ]

    model_source = st.selectbox(
        "Model architecture",
        model_options,
        index=model_options.index(
            d.get(
                "model_source",
                "Third-party cloud model",
            )
        ),
    )

    model_provider = st.text_input(
        "Model or provider",
        value=d.get(
            "model_provider",
            "",
        ),
        placeholder=(
            "Example: Groq, internal model, vendor API..."
        ),
    )

    visibility_options = [
        "Internal users only",
        "Authorized external users",
        "Customers",
        "Public",
        "Multiple audiences",
        "Not decided",
    ]

    external_visibility = st.selectbox(
        "Output exposure",
        visibility_options,
        index=visibility_options.index(
            d.get(
                "external_visibility",
                "Internal users only",
            )
        ),
    )

with right:

    review_options = [
        "Always",
        "For high-impact outputs only",
        "Sometimes",
        "No",
        "Not decided",
    ]

    human_review = st.selectbox(
        "Human review before output is acted on",
        review_options,
        index=review_options.index(
            d.get(
                "human_review",
                "Always",
            )
        ),
    )

    decision_options = [
        "No",
        "Provides recommendations",
        "Materially influences decisions",
        "Makes automated decisions",
        "Not sure",
    ]

    decision_impact = st.selectbox(
        "Does AI influence decisions about people?",
        decision_options,
        index=decision_options.index(
            d.get(
                "decision_impact",
                "No",
            )
        ),
    )

    action_options = [
        "No — output only",
        "Can retrieve data",
        "Can modify data",
        "Can call tools / APIs",
        "Can trigger real-world actions",
        "Not decided",
    ]

    agentic_capability = st.selectbox(
        "Can the AI take actions beyond generating content?",
        action_options,
        index=action_options.index(
            d.get(
                "agentic_capability",
                "No — output only",
            )
        ),
    )


# ============================================================
# 3. TRUST BOUNDARIES
# ============================================================

st.divider()

st.header(
    "3. Define trust boundaries"
)

st.caption(
    (
        "Identify where data leaves controlled environments "
        "and which external inputs or systems must be trusted."
    )
)

left, right = st.columns(
    2
)

with left:

    if (
        model_source
        == "Third-party cloud model"
    ):

        retention_options = [
            "Unknown",
            "Provider does not retain inputs",
            "Provider may retain inputs",
        ]

        desired_retention = d.get(
            "provider_retention",
            "Unknown",
        )

        if (
            desired_retention
            not in retention_options
        ):
            desired_retention = "Unknown"

        provider_retention = st.selectbox(
            "Provider data retention",
            retention_options,
            index=retention_options.index(
                desired_retention
            ),
        )

    else:

        retention_options = [
            "No third-party processing",
            "Unknown",
        ]

        desired_retention = d.get(
            "provider_retention",
            "No third-party processing",
        )

        if (
            desired_retention
            not in retention_options
        ):
            desired_retention = (
                "No third-party processing"
            )

        provider_retention = st.selectbox(
            "Third-party data retention",
            retention_options,
            index=retention_options.index(
                desired_retention
            ),
        )

    training_options = [
        "No",
        "Yes",
        "Unknown",
        "Not applicable",
    ]

    desired_training = d.get(
        "training_use",
        "No",
    )

    if (
        desired_training
        not in training_options
    ):
        desired_training = "No"

    training_use = st.selectbox(
        "Can submitted data be used for model training?",
        training_options,
        index=training_options.index(
            desired_training
        ),
    )

with right:

    untrusted_options = [
        "No",
        "Yes — documents",
        "Yes — websites",
        "Yes — email/messages",
        "Yes — user-generated content",
        "Multiple sources",
        "Unknown",
    ]

    untrusted_content = st.selectbox(
        "Will the model process untrusted external content?",
        untrusted_options,
        index=untrusted_options.index(
            d.get(
                "untrusted_content",
                "No",
            )
        ),
    )

    logging_options = [
        "Yes",
        "Partially",
        "No",
        "Not decided",
    ]

    logging = st.selectbox(
        "Are AI interactions logged for investigation/audit?",
        logging_options,
        index=logging_options.index(
            d.get(
                "logging",
                "Yes",
            )
        ),
    )


additional_context = st.text_area(
    "Architecture, safeguards, or additional context",
    value=d.get(
        "additional_context",
        "",
    ),
    placeholder=(
        "Optional: access controls, redaction, sandboxing, "
        "retrieval architecture, evaluation results, "
        "vendor guarantees, retention controls..."
    ),
)


# ============================================================
# SYSTEM MODEL
# ============================================================

st.subheader(
    "System model"
)

provider_label = (
    model_provider.strip()
    or "Model Provider"
)

if (
    model_source
    == "Third-party cloud model"
):

    trust_map = (
        f"{users or 'User'} → Application → "
        f"[ External trust boundary ] → "
        f"{provider_label} → Output"
    )

elif (
    model_source
    == "On-device model"
):

    trust_map = (
        f"{users or 'User'} → Application → "
        "On-device model → Output"
    )

else:

    trust_map = (
        f"{users or 'User'} → Application → "
        f"{provider_label} → Output"
    )


st.markdown(
    f"""
    <div class="trust-map">
        <strong>{trust_map}</strong><br><br>
        <span style="color:#777;">
            Data: {data_description or "Not yet described"}
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RUN REVIEW
# ============================================================

st.divider()

generate = st.button(
    "Run Launch Review",
    type="primary",
    use_container_width=True,
)


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

        result = json.loads(
            response
            .choices[0]
            .message
            .content
        )

    except json.JSONDecodeError:

        st.error(
            (
                "The model returned an invalid "
                "structured response. "
                "Run the review again."
            )
        )

        st.stop()

    except Exception as error:

        st.error(
            (
                "Unable to generate "
                f"the review: {error}"
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

    st.header(
        "Launch decision"
    )


    if gate == "BLOCKED":

        st.error(
            "BLOCKED"
        )

    elif gate == "EVIDENCE REQUIRED":

        st.warning(
            "EVIDENCE REQUIRED"
        )

    elif gate == "CONDITIONAL":

        st.warning(
            "CONDITIONAL"
        )

    else:

        st.success(
            "READY FOR REVIEW"
        )


    st.caption(
        (
            "Decision generated by LaunchGate's "
            "deterministic policy engine."
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

    st.subheader(
        "Risk surface"
    )

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
            "Risk analysis",
            "Assumptions",
            "Evidence",
            "Threat model",
            "Evaluations",
            "Review workflow",
            "Continuous controls",
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

    st.subheader(
        "Review record"
    )

    st.download_button(
        "Download structured review",
        data=json.dumps(
            review_record,
            indent=2,
        ),
        file_name=(
            f"{review_id.lower()}-"
            "launch-review.json"
        ),
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