"""Claude integration for email drafting."""

from anthropic import Anthropic

from .config import config

client = Anthropic(api_key=config.anthropic_api_key) if config else None

SYSTEM_PROMPT = """You are an expert Salesforce Case Manager email assistant at Xometry.
Your job is to draft professional, concise emails to customers regarding their cases.

Guidelines:
- Be professional but friendly
- Keep emails concise and action-oriented
- Include relevant case details when provided
- Use clear subject lines
- End with appropriate next steps or calls to action
- Match the tone to the situation (urgent issues = more direct, general inquiries = warmer)

Format your response as:
SUBJECT: <subject line>

<email body>"""


def draft_email(
    case_number: str,
    customer_name: str,
    issue_summary: str,
    tone: str = "professional",
    additional_context: str = "",
) -> dict:
    """
    Draft an email response for a Salesforce case.

    Returns:
        dict with 'subject' and 'body' keys
    """
    prompt = f"""Draft an email for this Salesforce case:

Case Number: {case_number}
Customer Name: {customer_name}
Issue Summary: {issue_summary}
Desired Tone: {tone}
{f"Additional Context: {additional_context}" if additional_context else ""}

Draft a complete email response."""

    response = client.messages.create(
        model=config.claude_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text

    # Parse subject and body
    if "SUBJECT:" in content:
        parts = content.split("\n", 2)
        subject = parts[0].replace("SUBJECT:", "").strip()
        body = "\n".join(parts[1:]).strip()
    else:
        subject = f"Re: Case {case_number}"
        body = content

    return {"subject": subject, "body": body}


def refine_email(original_draft: str, feedback: str) -> dict:
    """Refine an email draft based on user feedback."""
    prompt = f"""Here's an email draft that needs refinement:

{original_draft}

User feedback: {feedback}

Please revise the email based on this feedback."""

    response = client.messages.create(
        model=config.claude_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text

    if "SUBJECT:" in content:
        parts = content.split("\n", 2)
        subject = parts[0].replace("SUBJECT:", "").strip()
        body = "\n".join(parts[1:]).strip()
    else:
        subject = ""
        body = content

    return {"subject": subject, "body": body}
