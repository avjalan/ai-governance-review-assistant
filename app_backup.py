import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("GROQ_API_KEY was not found. Check your .env file.")
    st.stop()

client = Groq(api_key=api_key)

st.set_page_config(
    page_title="AI Governance Review Assistant",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ AI Governance Review Assistant")

st.markdown("""
Evaluate proposed AI projects before deployment.

Complete the form below to generate a preliminary governance review.
""")

st.divider()

st.header("Project Information")

use_case = st.text_area(
    "Describe the proposed AI use case",
    placeholder="Example: Summarize legal contracts using AI..."
)

users = st.text_input(
    "Who will use this AI?",
    placeholder="Lawyers, HR, Customer Support..."
)

data = st.text_area(
    "What data will the AI process?",
    placeholder="Contracts, employee records, customer chats..."
)

st.subheader("Data Types")

personal = st.checkbox("Personal Information")
confidential = st.checkbox("Confidential Company Data")
financial = st.checkbox("Financial Data")
customer = st.checkbox("Customer Data")

third_party = st.selectbox(
    "Is a third-party AI model used?",
    ["Yes", "No", "Not Sure"]
)
submit = st.button("Generate Assessment", type="primary")
if submit:
    if not use_case.strip():
        st.warning("Please describe the proposed AI use case.")
        st.stop()

    selected_data_types = []

    if personal:
        selected_data_types.append("Personal information")

    if confidential:
        selected_data_types.append("Confidential company data")

    if financial:
        selected_data_types.append("Financial data")

    if customer:
        selected_data_types.append("Customer data")

    if not selected_data_types:
        selected_data_types.append("No specific data types selected")

    prompt = f"""
You are an AI governance analyst assisting a legal team with a preliminary
review of a proposed AI use case.

This report is decision support only. Do not claim to provide legal advice,
make final legal conclusions, or approve the project.

Proposed AI use case:
{use_case}

Intended users:
{users or "Not provided"}

Data processed:
{data or "Not provided"}

Selected data types:
{", ".join(selected_data_types)}

Third-party AI model:
{third_party}

Generate a structured and concise governance assessment with these exact sections:

## Executive Summary

Summarize the proposed system, its intended purpose, users, and major concerns.

## Privacy Assessment

Include:
- Risk level: Low, Medium, High, or Needs More Information
- Potential risks
- Why those risks matter
- Recommended safeguards

## Security Assessment

Include:
- Risk level
- Potential risks
- Recommended technical and operational controls

## Intellectual Property Assessment

Include:
- Risk level
- Copyright, licensing, confidentiality, ownership, and training-data concerns
- Recommended safeguards

## Compliance Assessment

Include:
- Risk level
- Potential regulatory, policy, recordkeeping, and vendor-review considerations
- Do not state that any specific law conclusively applies

## Human Review Checkpoints

List specific moments when a qualified person should review, approve, or
escalate the system or its outputs.

## Overall Recommendation

Choose one:
- Proceed
- Proceed with safeguards
- Escalate for specialist review
- Do not proceed in current form

Explain the recommendation and list three to five next steps.

Be specific to the information provided. Clearly identify missing information.
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
                            "assessments for preliminary legal and operational review."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )

        report = response.choices[0].message.content

        st.divider()
        st.header("Governance Assessment")
        st.markdown(report)

        st.download_button(
            "Download Assessment",
            data=report,
            file_name="ai_governance_assessment.md",
            mime="text/markdown",
        )

        st.caption(
            "This prototype provides preliminary decision support and does not "
            "constitute legal advice or final project approval."
        )

    except Exception as error:
        st.error(f"Unable to generate the assessment: {error}")