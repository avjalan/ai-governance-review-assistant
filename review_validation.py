"""Validate model output before it can influence a launch gate."""

DOMAINS = (
    "privacy", "security", "intellectual_property", "compliance",
    "reliability", "ai_security",
)


def validate_assessment(value):
    if not isinstance(value, dict):
        raise ValueError("The assessment must be a JSON object.")
    domains = value.get("risk_domains")
    if not isinstance(domains, dict):
        raise ValueError("The assessment is missing risk domains.")
    for name in DOMAINS:
        domain = domains.get(name)
        if not isinstance(domain, dict):
            raise ValueError(f"The assessment is missing the {name} domain.")
        score = domain.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
            raise ValueError(f"The {name} score must be a number from 0 to 10.")
    evidence = value.get("missing_evidence")
    if not isinstance(evidence, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("question"), str)
        for item in evidence
    ):
        raise ValueError("The missing evidence list is malformed.")
    return value
