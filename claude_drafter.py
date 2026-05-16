import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def create_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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

    Returns:
        Dictionary with 'subject' and 'body' keys
    """
    client = create_client()

    system_prompt = """You are a professional customer service email drafter for Xometry,
a manufacturing marketplace. Write concise, professional emails that:
- Are warm but professional in tone
- Address the customer's specific concern
- Provide clear next steps when applicable
- Keep paragraphs short (2-3 sentences max)
- Sign off appropriately without including a specific name (use "Best regards," or similar)

Respond with JSON containing exactly two keys: "subject" and "body"."""

    user_prompt = f"""Draft an email for the following case:

Case Number: {case_context.get('case_number', 'N/A')}
Customer Name: {case_context.get('customer_name', 'Customer')}
Issue Summary: {case_context.get('issue_summary', '')}
Requested Action: {case_context.get('requested_action', 'general response')}
Tone: {case_context.get('tone', 'professional')}
Additional Context: {case_context.get('additional_context', 'None')}

Generate a professional email response. Return only valid JSON with "subject" and "body" keys."""

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
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {
            "subject": f"Re: Case {case_context.get('case_number', '')}",
            "body": response_text
        }


def refine_draft(original_draft: dict, feedback: str) -> dict:
    """
    Refine an existing email draft based on user feedback.
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
