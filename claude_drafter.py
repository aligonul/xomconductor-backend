"""
Claude Email Drafter Module.

Integrates L2G context and email templates with Claude for
automated Salesforce email drafting.
"""

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

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


def create_client():
    """Create an Anthropic client with API key from config."""
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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
            - vendor_note / issue_summary: The note from vendor/customer
            - case_type: Optional explicit case type (overrides auto-detection)
            - customer_name: Customer's name
            - job_id / case_number: Job/order ID
            - Additional fields as needed by templates

    Returns:
        Complete system prompt string for Claude
    """
    vendor_note = job_data.get("vendor_note") or job_data.get("issue_summary", "")
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
    system_parts.append("Return JSON with 'subject' and 'body' keys.")
    system_parts.append("Do not include template placeholders - use actual values from the job data.")
    system_parts.append("If information is missing, write naturally around it or request it from the customer.")
    system_parts.append("Sign off with the CM name if provided, otherwise use 'Your Xometry Case Manager'.")

    return "\n".join(system_parts)


def draft_email(case_context: dict) -> dict:
    """
    Generate a professional email draft using Claude based on case context.

    Args:
        case_context: Dictionary containing case details:
            - case_number: str
            - customer_name: str
            - issue_summary: str
            - requested_action: str (e.g., "apology", "update", "resolution")
            - tone: str (e.g., "professional", "empathetic", "formal")
            - additional_context: str (optional)
            - vendor_note: str (optional, for case type detection)

    Returns:
        Dictionary with 'subject', 'body', and 'case_type' keys
    """
    client = create_client()

    system_prompt = build_system_prompt(case_context)

    user_prompt = case_context.get("vendor_note") or case_context.get("issue_summary", "")
    if not user_prompt:
        user_prompt = f"Draft an email for case {case_context.get('case_number', 'N/A')}"

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        system=system_prompt
    )

    response_text = message.content[0].text

    import json
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        result = json.loads(response_text.strip())
        result["case_type"] = detect_case_type(case_context.get("vendor_note") or case_context.get("issue_summary", ""))
        return result
    except json.JSONDecodeError:
        subject = ""
        body = response_text
        lines = response_text.split("\n")
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
                body = "\n".join(lines[i + 1:]).strip()
                break
        return {
            "subject": subject or f"Re: Case {case_context.get('case_number', '')}",
            "body": body,
            "case_type": detect_case_type(case_context.get("vendor_note") or case_context.get("issue_summary", ""))
        }


def refine_draft(original_draft: dict, feedback: str) -> dict:
    """
    Refine an existing email draft based on user feedback.

    Args:
        original_draft: Dictionary with 'subject' and 'body' keys
        feedback: User feedback on how to improve the draft

    Returns:
        Dictionary with updated 'subject' and 'body' keys
    """
    client = create_client()

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Here is an email draft:

Subject: {original_draft.get('subject', '')}
Body: {original_draft.get('body', '')}

User feedback: {feedback}

Please revise the email based on this feedback. Return only valid JSON with "subject" and "body" keys."""
            }
        ],
        system="You are revising an email draft. Incorporate the user's feedback while maintaining professionalism. Return only valid JSON."
    )

    response_text = message.content[0].text

    import json
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {
            "subject": original_draft.get('subject', ''),
            "body": response_text
        }
