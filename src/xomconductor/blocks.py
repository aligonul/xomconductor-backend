"""Slack Block Kit UI components."""

from typing import Optional


def case_input_modal(
    sf_enabled: bool = False,
    prefill_case_number: str = "",
    prefill_customer_name: str = "",
    prefill_customer_email: str = "",
    prefill_issue_summary: str = "",
) -> dict:
    """Modal for entering case details to draft an email."""
    blocks = []

    # SF lookup section if enabled
    if sf_enabled:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Enter a case number and click *Lookup* to auto-fill from Salesforce, or fill manually below.",
            },
        })
        blocks.append({
            "type": "actions",
            "block_id": "sf_lookup_block",
            "elements": [
                {
                    "type": "plain_text_input",
                    "action_id": "sf_case_lookup",
                    "placeholder": {"type": "plain_text", "text": "Case # (e.g., 00123456)"},
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Lookup"},
                    "action_id": "lookup_sf_case",
                },
            ],
        })
        blocks.append({"type": "divider"})

    # Case number input
    case_input = {
        "type": "plain_text_input",
        "action_id": "case_number",
        "placeholder": {"type": "plain_text", "text": "e.g., 00123456"},
    }
    if prefill_case_number:
        case_input["initial_value"] = prefill_case_number

    blocks.append({
        "type": "input",
        "block_id": "case_number_block",
        "element": case_input,
        "label": {"type": "plain_text", "text": "Case Number"},
    })

    # Customer name input
    name_input = {
        "type": "plain_text_input",
        "action_id": "customer_name",
        "placeholder": {"type": "plain_text", "text": "Customer's name"},
    }
    if prefill_customer_name:
        name_input["initial_value"] = prefill_customer_name

    blocks.append({
        "type": "input",
        "block_id": "customer_name_block",
        "element": name_input,
        "label": {"type": "plain_text", "text": "Customer Name"},
    })

    # Customer email input (new for SF)
    email_input = {
        "type": "plain_text_input",
        "action_id": "customer_email",
        "placeholder": {"type": "plain_text", "text": "customer@company.com"},
    }
    if prefill_customer_email:
        email_input["initial_value"] = prefill_customer_email

    blocks.append({
        "type": "input",
        "block_id": "customer_email_block",
        "optional": not sf_enabled,
        "element": email_input,
        "label": {"type": "plain_text", "text": "Customer Email"},
    })

    # Issue summary input
    summary_input = {
        "type": "plain_text_input",
        "action_id": "issue_summary",
        "multiline": True,
        "placeholder": {
            "type": "plain_text",
            "text": "Describe the issue and what you want to communicate...",
        },
    }
    if prefill_issue_summary:
        summary_input["initial_value"] = prefill_issue_summary

    blocks.append({
        "type": "input",
        "block_id": "issue_summary_block",
        "element": summary_input,
        "label": {"type": "plain_text", "text": "Issue Summary"},
    })

    # Tone selector
    blocks.append({
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
                {"text": {"type": "plain_text", "text": "Professional"}, "value": "professional"},
                {"text": {"type": "plain_text", "text": "Friendly"}, "value": "friendly"},
                {"text": {"type": "plain_text", "text": "Urgent"}, "value": "urgent"},
                {"text": {"type": "plain_text", "text": "Apologetic"}, "value": "apologetic"},
            ],
        },
        "label": {"type": "plain_text", "text": "Tone"},
    })

    # Additional context
    blocks.append({
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
    })

    return {
        "type": "modal",
        "callback_id": "draft_email_modal",
        "title": {"type": "plain_text", "text": "Draft Email"},
        "submit": {"type": "plain_text", "text": "Generate Draft"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": blocks,
    }


def email_draft_blocks(
    case_number: str,
    customer_name: str,
    subject: str,
    body: str,
    draft_id: str,
    customer_email: Optional[str] = None,
    sf_case_id: Optional[str] = None,
    sf_enabled: bool = False,
) -> list:
    """Blocks displaying an email draft with action buttons."""
    to_text = f"*To:* {customer_name}"
    if customer_email:
        to_text += f" <{customer_email}>"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Email Draft for Case {case_number}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": to_text},
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
    ]

    # Primary action buttons
    action_elements = [
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
    ]

    blocks.append({
        "type": "actions",
        "block_id": f"draft_actions_{draft_id}",
        "elements": action_elements,
    })

    # SF-specific actions
    if sf_enabled and sf_case_id and customer_email:
        blocks.append({
            "type": "actions",
            "block_id": f"sf_actions_{draft_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Send via Salesforce"},
                    "style": "primary",
                    "action_id": "send_via_sf",
                    "value": draft_id,
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Send Email?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": f"This will send the email to *{customer_email}* via Salesforce and log it on Case {case_number}.",
                        },
                        "confirm": {"type": "plain_text", "text": "Send"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Save as SF Draft"},
                    "action_id": "save_sf_draft",
                    "value": draft_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Add as Case Comment"},
                    "action_id": "add_case_comment",
                    "value": draft_id,
                },
            ],
        })

    return blocks


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


def home_tab_blocks(sf_connected: bool = False) -> list:
    """Blocks for the App Home tab."""
    status = "Connected to Salesforce" if sf_connected else "Salesforce not configured"
    status_emoji = ":white_check_mark:" if sf_connected else ":warning:"

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
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"{status_emoji} {status}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Quick Actions*"},
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
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Lookup Case"},
                    "action_id": "open_case_lookup",
                },
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Powered by Claude | Type `/draft` in any channel to start"},
            ],
        },
    ]


def case_lookup_modal() -> dict:
    """Modal for looking up a Salesforce case."""
    return {
        "type": "modal",
        "callback_id": "case_lookup_modal",
        "title": {"type": "plain_text", "text": "Lookup Case"},
        "submit": {"type": "plain_text", "text": "Lookup"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "case_search_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "case_search",
                    "placeholder": {"type": "plain_text", "text": "Case number or search term"},
                },
                "label": {"type": "plain_text", "text": "Search"},
            },
        ],
    }


def case_details_blocks(case) -> list:
    """Display case details from Salesforce."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Case {case.case_number}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Status:*\n{case.status}"},
                {"type": "mrkdwn", "text": f"*Priority:*\n{case.priority}"},
                {"type": "mrkdwn", "text": f"*Contact:*\n{case.contact_name}"},
                {"type": "mrkdwn", "text": f"*Email:*\n{case.contact_email or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Account:*\n{case.account_name}"},
                {"type": "mrkdwn", "text": f"*Owner:*\n{case.owner_name}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Subject:*\n{case.subject}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{case.description[:500] if case.description else 'No description'}{'...' if case.description and len(case.description) > 500 else ''}",
            },
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Draft Email for This Case"},
                    "style": "primary",
                    "action_id": "draft_for_case",
                    "value": case.id,
                },
            ],
        },
    ]
