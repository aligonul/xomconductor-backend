"""
Claude Email Drafter Module.

Integrates L2G context and email templates with Claude 3.5 Sonnet
for automated Salesforce email drafting.
"""

import os
from anthropic import Anthropic

from knowledge.cm_l2g_context import (
    L2G_ROLE_DEFINITION,
    POD_SCOPE,
    PROCEDURES_MAP,
    get_procedure_for_case_type,
    build_system_context,
)
from knowledge.email_templates import (
    EMAIL_TEMPLATES,
    get_template,
)


CASE_TYPE_KEYWORDS = {
    case_type: procedure.get("keywords", [])
    for case_type, procedure in PROCEDURES_MAP.items()
}


def detect_case_type(note: str) -> str:
    """
    Auto-detect case type from vendor note using keyword matching.

    Args:
        note: The vendor note or case description text

    Returns:
        Detected case type key (e.g., 'dfm', 'rma_new') or 'general_inquiry' as fallback
    """
    if not note:
        return "general_inquiry"

    note_lower = note.lower()
    scores = {}

    for case_type, keywords in CASE_TYPE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in note_lower:
                score += len(keyword)
        if score > 0:
            scores[case_type] = score

    if not scores:
        return "general_inquiry"

    return max(scores, key=scores.get)


def build_system_prompt(job_data: dict) -> str:
    """
    Build the complete system prompt for Claude, injecting role context
    and the most relevant template based on case type.

    Args:
        job_data: Dictionary containing job/case information including:
            - vendor_note: The note from vendor/customer (used for case detection)
            - case_type: Optional explicit case type (overrides auto-detection)
            - customer_name: Customer's name
            - job_id: Job/order ID
            - Additional fields as needed by templates

    Returns:
        Complete system prompt string for Claude
    """
    vendor_note = job_data.get("vendor_note", "")
    explicit_case_type = job_data.get("case_type")

    case_type = explicit_case_type or detect_case_type(vendor_note)

    context = build_system_context(case_type)

    template = get_template(case_type)

    system_parts = [
        context,
        "\n\n--- Email Drafting Instructions ---",
        "Draft a professional email for the customer based on the case details below.",
        "Use the template structure as a guide, but adapt the content to the specific situation.",
        "Maintain Xometry's professional and empathetic tone throughout.",
    ]

    if template:
        system_parts.append(f"\n\nReference Template ({template['name']}):")
        system_parts.append(f"Subject Line Format: {template['subject']}")
        system_parts.append(f"\nTemplate Body:\n{template['body']}")

    system_parts.append("\n\n--- Job/Case Data ---")
    for key, value in job_data.items():
        if value:
            formatted_key = key.replace("_", " ").title()
            system_parts.append(f"{formatted_key}: {value}")

    system_parts.append("\n\n--- Output Requirements ---")
    system_parts.append("1. Generate a subject line first, on its own line starting with 'Subject: '")
    system_parts.append("2. Then provide the email body")
    system_parts.append("3. Do not include template placeholders - use actual values from the job data")
    system_parts.append("4. If information is missing, write naturally around it or request it from the customer")
    system_parts.append("5. Sign off with the CM name if provided, otherwise use 'Your Xometry Case Manager'")

    return "\n".join(system_parts)


def draft_email(job_data: dict, client: Anthropic | None = None) -> dict:
    """
    Draft an email using Claude 3.5 Sonnet.

    Args:
        job_data: Dictionary containing job/case information
        client: Optional Anthropic client (creates new one if not provided)

    Returns:
        Dictionary with 'subject' and 'body' keys
    """
    if client is None:
        client = Anthropic()

    system_prompt = build_system_prompt(job_data)

    user_message = job_data.get("vendor_note", "Please draft an email for this case.")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    raw_response = response.content[0].text

    subject = ""
    body = raw_response

    lines = raw_response.split("\n")
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line[8:].strip()
            body = "\n".join(lines[i + 1:]).strip()
            break

    return {
        "subject": subject,
        "body": body,
        "case_type": job_data.get("case_type") or detect_case_type(job_data.get("vendor_note", "")),
        "model": "claude-sonnet-4-20250514"
    }
