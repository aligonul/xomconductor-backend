"""Slack Block Kit UI components."""


def case_input_modal() -> dict:
    """Modal for entering case details to draft an email."""
    return {
        "type": "modal",
        "callback_id": "draft_email_modal",
        "title": {"type": "plain_text", "text": "Draft Email"},
        "submit": {"type": "plain_text", "text": "Generate Draft"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "case_number_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "case_number",
                    "placeholder": {"type": "plain_text", "text": "e.g., 00123456"},
                },
                "label": {"type": "plain_text", "text": "Case Number"},
            },
            {
                "type": "input",
                "block_id": "customer_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "customer_name",
                    "placeholder": {"type": "plain_text", "text": "Customer's name"},
                },
                "label": {"type": "plain_text", "text": "Customer Name"},
            },
            {
                "type": "input",
                "block_id": "issue_summary_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "issue_summary",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Describe the issue and what you want to communicate...",
                    },
                },
                "label": {"type": "plain_text", "text": "Issue Summary"},
            },
            {
                "type": "input",
                "block_id": "tone_block",
                "element": {
                    "type": "static_select",
                    "action_id": "tone",
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Professional"},
                        "value": "professional",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Professional"},
                            "value": "professional",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Friendly"},
                            "value": "friendly",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Urgent"},
                            "value": "urgent",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Apologetic"},
                            "value": "apologetic",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Tone"},
            },
            {
                "type": "input",
                "block_id": "context_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "additional_context",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Any additional context or specific points to include...",
                    },
                },
                "label": {"type": "plain_text", "text": "Additional Context"},
            },
        ],
    }


def email_draft_blocks(
    case_number: str,
    customer_name: str,
    subject: str,
    body: str,
    draft_id: str,
) -> list:
    """Blocks displaying an email draft with action buttons."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Email Draft for Case {case_number}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*To:* {customer_name}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Subject:* {subject}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"draft_actions_{draft_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve & Copy"},
                    "style": "primary",
                    "action_id": "approve_draft",
                    "value": draft_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Refine"},
                    "action_id": "refine_draft",
                    "value": draft_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Regenerate"},
                    "action_id": "regenerate_draft",
                    "value": draft_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Discard"},
                    "style": "danger",
                    "action_id": "discard_draft",
                    "value": draft_id,
                },
            ],
        },
    ]


def refine_modal(draft_id: str, current_draft: str) -> dict:
    """Modal for providing refinement feedback."""
    return {
        "type": "modal",
        "callback_id": "refine_email_modal",
        "private_metadata": draft_id,
        "title": {"type": "plain_text", "text": "Refine Email"},
        "submit": {"type": "plain_text", "text": "Apply Changes"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Current Draft:*\n" + current_draft[:500] + ("..." if len(current_draft) > 500 else ""),
                },
            },
            {"type": "divider"},
            {
                "type": "input",
                "block_id": "feedback_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "feedback",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "What changes would you like? e.g., 'Make it shorter', 'Add more urgency', 'Include the part number XYZ-123'",
                    },
                },
                "label": {"type": "plain_text", "text": "Your Feedback"},
            },
        ],
    }


def home_tab_blocks() -> list:
    """Blocks for the App Home tab."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "XomConductor"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Your AI-powered assistant for drafting Salesforce case emails.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Quick Actions*",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Draft New Email"},
                    "style": "primary",
                    "action_id": "open_draft_modal",
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Powered by Claude | Type `/draft` in any channel to start",
                },
            ],
        },
    ]
