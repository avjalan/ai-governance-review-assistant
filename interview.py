"""Short, plain-language intake for LaunchGate."""

QUESTIONS = [
    ("use_case", "What would you like AI to help your team do?", "text", None, True),
    ("users", "Who will use it, and which team owns it?", "short", None, True),
    ("data_description", "What information will the AI see?", "text", None, True),
    ("data_categories", "Does that information include any of these?", "multiple", ["Personal information", "Sensitive personal information", "Confidential company data", "Customer data", "Financial data", "Potentially regulated data"], False),
    ("deployment_environment", "Who will be able to use or see the AI's output?", "choice", ["Internal tool", "Employee-facing product", "Customer-facing product", "Public-facing experience", "Developer tool", "Research / experiment"], False),
    ("human_review", "Will a person check the AI's work before anyone relies on it?", "choice", ["Always", "For high-impact outputs only", "Sometimes", "No", "Not decided"], False),
    ("decision_impact", "Could it affect a decision about a person?", "choice", ["No", "Provides recommendations", "Materially influences decisions", "Makes automated decisions", "Not sure"], False),
    ("agentic_capability", "What can the AI do on its own?", "choice", ["No — output only", "Can retrieve data", "Can modify data", "Can call tools / APIs", "Can trigger real-world actions", "Not decided"], False),
    ("model_source", "How will your team access the AI model?", "choice", ["Third-party cloud model", "Company-hosted model", "On-device model", "Hybrid / multiple models", "Not decided"], False),
    ("trust_profile", "What do you know about data handling and monitoring?", "profile", None, False),
    ("additional_context", "Is there anything else we should know?", "text", None, False),
]

HELP = {
    "use_case": "Example: summarize customer messages and suggest replies for support staff.",
    "users": "Example: customer support employees; owned by Customer Operations.",
    "data_description": "Use everyday language, such as customer messages, contracts, or public articles.",
    "data_categories": "Select everything that might apply. It is okay to select nothing if you are unsure.",
    "human_review": "Think about whether an employee checks the answer before it is sent, published, or used.",
    "agentic_capability": "For example, can it only draft text, or can it send messages, edit records, or make purchases?",
    "model_source": "Choose third-party cloud if requests go to an outside AI service. Choose Not decided if you do not know.",
    "trust_profile": "Unknown is a valid answer. LaunchGate will flag what your team needs to verify.",
    "additional_context": "Optional: mention access controls, testing, redaction, or safeguards already planned.",
}


def to_form_values(answers):
    """Map the shortened interview to the existing review engine."""
    values = dict(answers)
    selected = values.pop("data_categories", [])
    profile = values.pop("trust_profile", {}) or {}
    for label, key in [("Personal information", "personal"), ("Sensitive personal information", "sensitive_personal"), ("Confidential company data", "confidential"), ("Customer data", "customer"), ("Financial data", "financial"), ("Potentially regulated data", "regulated")]:
        values[key] = label in selected
    values.update(profile)
    values.setdefault("business_owner", "Other")
    values.setdefault("lifecycle_stage", "Concept")
    values.setdefault("model_provider", "Not decided")
    values.setdefault("external_visibility", {"Internal tool": "Internal users only", "Employee-facing product": "Internal users only", "Customer-facing product": "Customers", "Public-facing experience": "Public"}.get(values.get("deployment_environment"), "Not decided"))
    return values
