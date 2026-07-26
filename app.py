import json
import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq


# Load the Groq API key from the .env file
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")


# Page configuration
st.set_page_config(
    page_title="AI Governance Review Assistant",
    page_icon="⚖️",
    layout="wide",
)


# App title and description
st.title("⚖️ AI Governance Review Assistant")

st.write(
    """
    This prototype helps legal and governance teams conduct a preliminary
    risk assessment of proposed AI use cases.

    It reviews privacy, security, intellectual property, compliance, and
    human-review considerations.
    """
)

st.caption(
    "This tool provides preliminary decision support and does not constitute "
    "legal advice or final project approval."
)


# Check whether the API key exists
if not api_key:
    st.error(
        "Your Groq API key was not found. Make sure your .env file contains "
        "GROQ_API_KEY=your_key_here"
    )
    st.stop()


# Connect to Groq
client = Groq(api_key=api_key)


# Input section
st.header("Project Information")

use_case = st.text_area(
    "Describe the proposed AI use case",
    placeholder=(
        "Example: Develop an internal AI assistant that summarizes commercial "
        "agreements and identifies important clauses for attorneys."
    ),
    height=140,
)

users = st.text_input(
    "Who will use this AI?",
    placeholder="Example: Corporate attorneys and legal operations professionals",
)

data = st.text_area(
    "What data will the AI process?",
    placeholder=(
        "Example: Confidential contracts, internal policies, personal "
        "information, and proprietary business information"
    ),
    height=120,
)


st.subheader("Data Categories")

col1, col2 = st.columns(2)

with col1:
    personal = st.checkbox("Personal Information")
    confidential = st.checkbox("Confidential Company Data")

with col2:
    financial = st.checkbox("Financial Data")
    customer = st.checkbox("Customer Data")


third_party = st.selectbox(
    "Is a third-party AI model used?",
    ["Yes", "No", "Unknown"],
)


submit = st.button(
    "Generate Assessment",
    type="primary",
)


# Generate the assessment
if submit:

    if not use_case.strip():
        st.warning("Please describe the proposed AI use case.")

    elif not users.strip():
        st.warning("Please identify who will use the AI.")

    elif not data.strip():
        st.warning("Please describe the data the AI will process.")

    else:

        selected_data_categories = []

        if personal:
            selected_data_categories.append("Personal Information")

        if confidential:
            selected_data_categories.append("Confidential Company Data")

        if financial:
            selected_data_categories.append("Financial Data")

        if customer:
            selected_data_categories.append("Customer Data")

        if not selected_data_categories:
            selected_data_categories.append("No specific categories selected")


        prompt = f"""
You are an AI governance analyst supporting a corporate legal team.

Perform a preliminary governance and risk assessment of the proposed AI use
case below.

This assessment is for decision support only. It is not legal advice or final
approval.

PROJECT INFORMATION

Proposed AI use case:
{use_case}

Intended users:
{users}

Data processed:
{data}

Selected data categories:
{", ".join(selected_data_categories)}

Third-party AI model used:
{third_party}

Return only one valid JSON object.

Do not use Markdown.
Do not place the JSON inside code fences.
Do not include any text before or after the JSON.

Use this exact top-level structure:

{{
  "Executive Summary": {{
    "summary": "Two or three sentence summary of the proposed use case.",
    "intended_purpose": "Brief description of the system's intended purpose.",
    "intended_users": [
      "User group"
    ],
    "major_concerns": [
      "Major concern"
    ]
  }},

  "Privacy Assessment": {{
    "risk_level": "Low, Medium, High, or Needs More Information",
    "risk_score": 0,
    "identified_risks": [
      "Specific privacy risk"
    ],
    "recommended_safeguards": [
      "Specific privacy safeguard"
    ]
  }},

  "Security Assessment": {{
    "risk_level": "Low, Medium, High, or Needs More Information",
    "risk_score": 0,
    "identified_risks": [
      "Specific security risk"
    ],
    "recommended_safeguards": [
      "Specific security safeguard"
    ]
  }},

  "Intellectual Property Assessment": {{
    "risk_level": "Low, Medium, High, or Needs More Information",
    "risk_score": 0,
    "identified_risks": [
      "Specific intellectual-property risk"
    ],
    "recommended_safeguards": [
      "Specific intellectual-property safeguard"
    ]
  }},

  "Compliance Assessment": {{
    "risk_level": "Low, Medium, High, or Needs More Information",
    "risk_score": 0,
    "identified_risks": [
      "Specific compliance or internal-policy consideration"
    ],
    "recommended_safeguards": [
      "Specific compliance safeguard"
    ]
  }},

  "Human Review Checkpoints": [
    {{
      "checkpoint": "Point where human review is required",
      "reason": "Why human review is necessary",
      "suggested_owner": "Suggested team or role"
    }}
  ],

  "Overall Recommendation": {{
    "overall_risk": "Low, Medium, High, or Needs More Information",
    "overall_score": 0,
    "decision": "Proceed, Proceed with Safeguards, Escalate for Specialist Review, or Do Not Proceed in Current Form",
    "reason": "Brief explanation of the recommendation.",
    "required_reviewers": [
      "Legal"
    ],
    "missing_information": [
      "Important unanswered question"
    ],
    "next_steps": [
      "Specific next step"
    ]
  }}
}}

Use risk scores from 0 to 10 for each individual risk category.

Use an overall score from 0 to 100.

Be specific to the information supplied by the user.

Do not invent facts.

When important details are missing, identify them clearly.

Do not state that a particular law definitely applies. Identify areas that
may require specialist legal review instead.
"""


        try:
            with st.spinner("Generating governance assessment..."):

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You produce careful, structured AI governance "
                                "assessments for preliminary legal and operational "
                                "review. Return only valid JSON."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )


            raw_response = response.choices[0].message.content
            assessment = json.loads(raw_response)


            st.divider()
            st.header("Governance Assessment")


            # Executive Summary
            executive_summary = assessment["Executive Summary"]

            st.subheader("Executive Summary")
            st.write(executive_summary["summary"])

            st.markdown(
                f"**Intended purpose:** "
                f"{executive_summary['intended_purpose']}"
            )

            st.markdown("**Intended users:**")

            for user_group in executive_summary["intended_users"]:
                st.write(f"- {user_group}")

            st.markdown("**Major concerns:**")

            for concern in executive_summary["major_concerns"]:
                st.write(f"- {concern}")


            # Overall Recommendation
            recommendation = assessment["Overall Recommendation"]

            risk_icons = {
                "Low": "🟢",
                "Medium": "🟡",
                "High": "🔴",
                "Needs More Information": "⚪",
            }

            overall_risk = recommendation["overall_risk"]
            overall_icon = risk_icons.get(overall_risk, "⚪")


            st.subheader("Overall Recommendation")

            metric1, metric2, metric3 = st.columns(3)

            with metric1:
                st.metric(
                    "Overall Risk",
                    f"{overall_icon} {overall_risk}",
                )

            with metric2:
                st.metric(
                    "Overall Score",
                    f"{recommendation['overall_score']}/100",
                )

            with metric3:
                st.metric(
                    "Decision",
                    recommendation["decision"],
                )

            st.info(recommendation["reason"])


            # Risk Assessments
            st.subheader("Risk Assessments")

            risk_sections = [
                (
                    "🔒 Privacy",
                    "Privacy Assessment",
                ),
                (
                    "🛡️ Security",
                    "Security Assessment",
                ),
                (
                    "⚖️ Intellectual Property",
                    "Intellectual Property Assessment",
                ),
                (
                    "📋 Compliance",
                    "Compliance Assessment",
                ),
            ]


            for title, key in risk_sections:

                section = assessment[key]
                risk_level = section["risk_level"]
                icon = risk_icons.get(risk_level, "⚪")

                with st.expander(
                    (
                        f"{icon} {title} — {risk_level} Risk "
                        f"({section['risk_score']}/10)"
                    ),
                    expanded=True,
                ):

                    st.markdown("**Identified risks**")

                    for risk in section["identified_risks"]:
                        st.write(f"- {risk}")

                    st.markdown("**Recommended safeguards**")

                    for safeguard in section["recommended_safeguards"]:
                        st.write(f"- {safeguard}")


            # Human Review Checkpoints
            st.subheader("Human Review Checkpoints")

            checkpoints = assessment["Human Review Checkpoints"]

            if checkpoints:

                for checkpoint in checkpoints:

                    st.markdown(
                        f"**{checkpoint['checkpoint']}**"
                    )

                    st.write(checkpoint["reason"])

                    st.caption(
                        f"Suggested owner: "
                        f"{checkpoint['suggested_owner']}"
                    )

                    st.divider()

            else:
                st.write("No human-review checkpoints were identified.")


            # Required Reviewers
            st.subheader("Required Reviewers")

            required_reviewers = recommendation["required_reviewers"]

            if required_reviewers:

                reviewer_columns = st.columns(3)

                for index, reviewer in enumerate(required_reviewers):

                    with reviewer_columns[index % 3]:

                        st.checkbox(
                            reviewer,
                            value=False,
                            key=f"reviewer_{index}_{reviewer}",
                        )

            else:
                st.write("No specific reviewers were identified.")


            # Missing Information
            st.subheader("Missing Information")

            missing_information = recommendation["missing_information"]

            if missing_information:

                st.warning(
                    "Additional information should be collected before "
                    "final approval."
                )

                for item in missing_information:
                    st.write(f"- {item}")

            else:
                st.success(
                    "No major missing information was identified."
                )


            # Next Steps
            st.subheader("Recommended Next Steps")

            for number, step in enumerate(
                recommendation["next_steps"],
                start=1,
            ):
                st.write(f"{number}. {step}")


            # Download Button
            download_report = json.dumps(
                assessment,
                indent=2,
            )

            st.download_button(
                "Download Assessment",
                data=download_report,
                file_name="ai_governance_assessment.json",
                mime="application/json",
            )


            st.caption(
                "This prototype provides preliminary decision support and "
                "does not constitute legal advice or final project approval."
            )


        except json.JSONDecodeError:
            st.error(
                "The AI returned an unexpected response format. "
                "Please click Generate Assessment again."
            )

        except KeyError as error:
            st.error(
                f"The assessment was missing an expected section: {error}. "
                "Please generate the assessment again."
            )

        except Exception as error:
            st.error(
                f"Unable to generate the assessment: {error}"
            )