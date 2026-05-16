import json
import logging
import uuid
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN, ALI_SLACK_CHANNEL_ID
from claude_drafter import draft_email, refine_draft, detect_case_type
from sf_email import sf_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

draft_cache = {}


# ============ APP HOME TAB ============

@app.event("app_home_opened")
def handle_app_home_opened(client, event, logger):
    """Display the App Home tab when user opens it."""
    from knowledge.cm_l2g_context import PROCEDURES_MAP

    case_type_options = [
        {
            "text": {"type": "plain_text", "text": proc["name"]},
            "value": key
        }
        for key, proc in list(PROCEDURES_MAP.items())[:10]
    ]

    client.views_publish(
        user_id=event["user"],
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "XomConductor - AI Email Drafter"}
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Welcome to XomConductor! I help you draft professional customer emails using AI.\n\n*Quick Actions:*"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Draft a New Email*\nClick the button to start drafting an email for a customer case."
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "New Draft"},
                        "style": "primary",
                        "action_id": "open_draft_modal"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*View Case Types*\nSee all available case types and their SOPs."
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Case Types"},
                        "action_id": "show_case_types"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*View Templates*\nBrowse available email templates."
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Templates"},
                        "action_id": "show_templates"
                    }
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Powered by Claude AI | Use `/draft` to quickly create emails"
                        }
                    ]
                }
            ]
        }
    )


@app.action("open_draft_modal")
def handle_open_draft_modal(ack, body, client):
    """Open the draft creation modal from App Home."""
    ack()

    from knowledge.cm_l2g_context import PROCEDURES_MAP

    case_type_options = [
        {
            "text": {"type": "plain_text", "text": proc["name"]},
            "value": key
        }
        for key, proc in PROCEDURES_MAP.items()
    ]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "create_draft_modal",
            "title": {"type": "plain_text", "text": "Create Email Draft"},
            "submit": {"type": "plain_text", "text": "Generate Draft"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "case_number_block",
                    "label": {"type": "plain_text", "text": "Case Number"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "case_number_input",
                        "placeholder": {"type": "plain_text", "text": "e.g., 12345678"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "customer_name_block",
                    "label": {"type": "plain_text", "text": "Customer Name"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "customer_name_input",
                        "placeholder": {"type": "plain_text", "text": "e.g., John Doe"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "case_type_block",
                    "label": {"type": "plain_text", "text": "Case Type"},
                    "element": {
                        "type": "static_select",
                        "action_id": "case_type_select",
                        "placeholder": {"type": "plain_text", "text": "Select case type"},
                        "options": case_type_options
                    },
                    "optional": True
                },
                {
                    "type": "input",
                    "block_id": "issue_block",
                    "label": {"type": "plain_text", "text": "Issue Description / Vendor Note"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "issue_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "Describe the issue or paste the vendor note..."}
                    }
                },
                {
                    "type": "input",
                    "block_id": "additional_context_block",
                    "label": {"type": "plain_text", "text": "Additional Context"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "additional_context_input",
                        "multiline": True,
                        "placeholder": {"type": "plain_text", "text": "Any additional details..."}
                    },
                    "optional": True
                }
            ]
        }
    )


@app.view("create_draft_modal")
def handle_create_draft_submission(ack, body, client, view):
    """Handle the draft creation modal submission."""
    ack()

    user_id = body["user"]["id"]
    values = view["state"]["values"]

    case_number = values["case_number_block"]["case_number_input"]["value"]
    customer_name = values["customer_name_block"]["customer_name_input"]["value"]
    case_type_select = values["case_type_block"]["case_type_select"].get("selected_option")
    case_type = case_type_select["value"] if case_type_select else None
    issue = values["issue_block"]["issue_input"]["value"]
    additional_context = values.get("additional_context_block", {}).get("additional_context_input", {}).get("value", "")

    case_context = {
        "case_number": case_number,
        "customer_name": customer_name,
        "issue_summary": issue,
        "vendor_note": issue,
        "additional_context": additional_context,
        "case_type": case_type
    }

    draft = draft_email(case_context)

    case_data = {
        "case_id": "",
        "case_number": case_number,
        "customer_name": customer_name,
        "customer_email": ""
    }

    draft_id = str(uuid.uuid4())[:8]
    draft_cache[draft_id] = {
        "case_data": case_data,
        "draft": draft,
        "channel_id": None
    }

    blocks = build_draft_message_blocks(case_data, draft, draft_id)

    client.chat_postMessage(
        channel=user_id,
        blocks=blocks,
        text=f"Email draft for Case {case_number}"
    )


@app.action("show_case_types")
def handle_show_case_types(ack, body, client):
    """Show available case types in a modal."""
    ack()

    from knowledge.cm_l2g_context import PROCEDURES_MAP

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{proc['name']}* (`{key}`)\n{proc['description']}"
            }
        }
        for key, proc in list(PROCEDURES_MAP.items())[:15]
    ]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Case Types"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": blocks
        }
    )


@app.action("show_templates")
def handle_show_templates(ack, body, client):
    """Show available email templates in a modal."""
    ack()

    from knowledge.email_templates import EMAIL_TEMPLATES

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{tmpl['name']}* (`{key}`)\nSubject: _{tmpl['subject']}_"
            }
        }
        for key, tmpl in list(EMAIL_TEMPLATES.items())[:15]
    ]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Email Templates"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": blocks
        }
    )


# ============ SLASH COMMANDS ============

@app.command("/draft")
def handle_draft_command(ack, body, client, command):
    """
    Handle /draft slash command.
    Usage: /draft [issue description]
    """
    ack()

    text = command.get("text", "").strip()
    user_id = command["user_id"]
    channel_id = command["channel_id"]

    if not text:
        from knowledge.cm_l2g_context import PROCEDURES_MAP

        case_type_options = [
            {
                "text": {"type": "plain_text", "text": proc["name"]},
                "value": key
            }
            for key, proc in PROCEDURES_MAP.items()
        ]

        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "slash_draft_modal",
                "private_metadata": json.dumps({"channel_id": channel_id}),
                "title": {"type": "plain_text", "text": "Quick Draft"},
                "submit": {"type": "plain_text", "text": "Generate"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "case_number_block",
                        "label": {"type": "plain_text", "text": "Case Number"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "case_number_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "customer_name_block",
                        "label": {"type": "plain_text", "text": "Customer Name"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_name_input"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "case_type_block",
                        "label": {"type": "plain_text", "text": "Case Type"},
                        "element": {
                            "type": "static_select",
                            "action_id": "case_type_select",
                            "options": case_type_options
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "issue_block",
                        "label": {"type": "plain_text", "text": "Issue Description"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "issue_input",
                            "multiline": True
                        }
                    }
                ]
            }
        )
    else:
        detected_type = detect_case_type(text)

        case_context = {
            "case_number": "N/A",
            "customer_name": "Customer",
            "issue_summary": text,
            "vendor_note": text,
            "case_type": detected_type
        }

        draft = draft_email(case_context)

        case_data = {
            "case_id": "",
            "case_number": "N/A",
            "customer_name": "Customer",
            "customer_email": ""
        }

        draft_id = str(uuid.uuid4())[:8]
        draft_cache[draft_id] = {
            "case_data": case_data,
            "draft": draft,
            "channel_id": channel_id
        }

        blocks = build_draft_message_blocks(case_data, draft, draft_id)
        blocks.insert(0, {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Detected case type: *{detected_type}*"}]
        })

        client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=f"Email draft (detected: {detected_type})"
        )


@app.view("slash_draft_modal")
def handle_slash_draft_submission(ack, body, client, view):
    """Handle the /draft modal submission."""
    ack()

    metadata = json.loads(view.get("private_metadata", "{}"))
    channel_id = metadata.get("channel_id")
    values = view["state"]["values"]

    case_number = values["case_number_block"]["case_number_input"]["value"]
    customer_name = values["customer_name_block"]["customer_name_input"]["value"]
    case_type_select = values["case_type_block"]["case_type_select"].get("selected_option")
    case_type = case_type_select["value"] if case_type_select else None
    issue = values["issue_block"]["issue_input"]["value"]

    case_context = {
        "case_number": case_number,
        "customer_name": customer_name,
        "issue_summary": issue,
        "vendor_note": issue,
        "case_type": case_type
    }

    draft = draft_email(case_context)

    case_data = {
        "case_id": "",
        "case_number": case_number,
        "customer_name": customer_name,
        "customer_email": ""
    }

    draft_id = str(uuid.uuid4())[:8]
    draft_cache[draft_id] = {
        "case_data": case_data,
        "draft": draft,
        "channel_id": channel_id
    }

    blocks = build_draft_message_blocks(case_data, draft, draft_id)

    target_channel = channel_id or body["user"]["id"]
    client.chat_postMessage(
        channel=target_channel,
        blocks=blocks,
        text=f"Email draft for Case {case_number}"
    )


@app.command("/case_types")
def handle_case_types_command(ack, body, client, command):
    """Handle /case_types slash command to list available case types."""
    ack()

    from knowledge.cm_l2g_context import PROCEDURES_MAP

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Available Case Types"}}
    ]

    for key, proc in PROCEDURES_MAP.items():
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{proc['name']}* (`{key}`)\n{proc['description']}"
            }
        })

    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        blocks=blocks,
        text="Available case types"
    )


@app.command("/templates")
def handle_templates_command(ack, body, client, command):
    """Handle /templates slash command to list available email templates."""
    ack()

    from knowledge.email_templates import EMAIL_TEMPLATES

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Available Email Templates"}}
    ]

    for key, tmpl in EMAIL_TEMPLATES.items():
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{tmpl['name']}* (`{key}`)\n_{tmpl['subject']}_"
            }
        })

    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        blocks=blocks,
        text="Available email templates"
    )


# ============ DIRECT MESSAGES & MENTIONS ============

@app.event("message")
def handle_direct_message(event, client, logger):
    """Handle direct messages to the bot."""
    if event.get("channel_type") != "im":
        return

    if event.get("bot_id"):
        return

    text = event.get("text", "").strip()
    user_id = event.get("user")
    channel_id = event.get("channel")

    if not text:
        return

    help_keywords = ["help", "yardim", "nasil", "how", "what can you do"]
    if any(kw in text.lower() for kw in help_keywords):
        client.chat_postMessage(
            channel=channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*XomConductor Help*\n\nI can help you draft professional customer emails. Here's how to use me:"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Commands:*\n"
                                "- `/draft` - Open draft creation form\n"
                                "- `/draft [issue text]` - Quick draft with auto-detection\n"
                                "- `/case_types` - View all case types\n"
                                "- `/templates` - View all templates"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Direct Message:*\n"
                                "Just describe the customer issue and I'll draft an email for you!"
                    }
                }
            ],
            text="XomConductor Help"
        )
        return

    detected_type = detect_case_type(text)

    case_context = {
        "case_number": "N/A",
        "customer_name": "Customer",
        "issue_summary": text,
        "vendor_note": text,
        "case_type": detected_type
    }

    client.chat_postMessage(
        channel=channel_id,
        text=f"Drafting email for *{detected_type}* case type..."
    )

    draft = draft_email(case_context)

    case_data = {
        "case_id": "",
        "case_number": "N/A",
        "customer_name": "Customer",
        "customer_email": ""
    }

    draft_id = str(uuid.uuid4())[:8]
    draft_cache[draft_id] = {
        "case_data": case_data,
        "draft": draft,
        "channel_id": channel_id
    }

    blocks = build_draft_message_blocks(case_data, draft, draft_id)
    blocks.insert(0, {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Detected case type: *{detected_type}*"}]
    })

    client.chat_postMessage(
        channel=channel_id,
        blocks=blocks,
        text=f"Email draft for {detected_type}"
    )


@app.event("app_mention")
def handle_app_mention(event, client, logger):
    """Handle @mentions of the bot in channels."""
    text = event.get("text", "").strip()
    channel_id = event.get("channel")
    user_id = event.get("user")

    import re
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not clean_text or clean_text.lower() in ["hi", "hello", "hey", "merhaba"]:
        client.chat_postMessage(
            channel=channel_id,
            text=f"Hi <@{user_id}>! I'm XomConductor. Use `/draft` to create an email draft, or DM me with your issue and I'll draft an email for you."
        )
        return

    detected_type = detect_case_type(clean_text)

    case_context = {
        "case_number": "N/A",
        "customer_name": "Customer",
        "issue_summary": clean_text,
        "vendor_note": clean_text,
        "case_type": detected_type
    }

    draft = draft_email(case_context)

    case_data = {
        "case_id": "",
        "case_number": "N/A",
        "customer_name": "Customer",
        "customer_email": ""
    }

    draft_id = str(uuid.uuid4())[:8]
    draft_cache[draft_id] = {
        "case_data": case_data,
        "draft": draft,
        "channel_id": channel_id
    }

    blocks = build_draft_message_blocks(case_data, draft, draft_id)
    blocks.insert(0, {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"<@{user_id}> requested | Case type: *{detected_type}*"}]
    })

    client.chat_postMessage(
        channel=channel_id,
        blocks=blocks,
        text=f"Email draft for {detected_type}"
    )


# ============ DRAFT MESSAGE BLOCKS ============


def build_draft_message_blocks(case_data: dict, draft: dict, draft_id: str) -> list:
    """Build Slack blocks for displaying a draft email with action buttons."""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Email Draft for Case {case_data.get('case_number', 'N/A')}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Customer:* {case_data.get('customer_name', 'N/A')}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Subject:*\n{draft.get('subject', '')}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Body:*\n```{draft.get('body', '')}```"
            }
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"draft_actions_{draft_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Send Email", "emoji": True},
                    "style": "primary",
                    "action_id": "send_email",
                    "value": draft_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Edit Draft", "emoji": True},
                    "action_id": "edit_draft",
                    "value": draft_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Regenerate", "emoji": True},
                    "action_id": "regenerate_draft",
                    "value": draft_id
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Cancel", "emoji": True},
                    "style": "danger",
                    "action_id": "cancel_draft",
                    "value": draft_id
                }
            ]
        }
    ]


def post_draft_to_channel(case_data: dict, draft: dict, channel_id: str = None) -> str:
    """Post a draft email to Slack and return the draft_id."""
    import uuid
    draft_id = str(uuid.uuid4())[:8]

    draft_cache[draft_id] = {
        "case_data": case_data,
        "draft": draft,
        "channel_id": channel_id or ALI_SLACK_CHANNEL_ID
    }

    blocks = build_draft_message_blocks(case_data, draft, draft_id)

    app.client.chat_postMessage(
        channel=channel_id or ALI_SLACK_CHANNEL_ID,
        blocks=blocks,
        text=f"Email draft for Case {case_data.get('case_number', 'N/A')}"
    )

    return draft_id


@app.action("send_email")
def handle_send_email(ack, body, client, logger):
    """Handle the Send Email button click."""
    ack()

    draft_id = body["actions"][0]["value"]
    cached = draft_cache.get(draft_id)

    if not cached:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=body["user"]["id"],
            text="Draft expired. Please regenerate."
        )
        return

    case_data = cached["case_data"]
    draft = cached["draft"]

    try:
        contact_email = sf_client.get_case_contact_email(case_data.get("case_id", ""))

        result = sf_client.send_email(
            case_id=case_data.get("case_id", ""),
            to_address=contact_email or case_data.get("customer_email", ""),
            subject=draft["subject"],
            body=draft["body"]
        )

        if result.get("success"):
            client.chat_update(
                channel=body["channel"]["id"],
                ts=body["message"]["ts"],
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Email Sent Successfully*\n"
                                    f"Case: {case_data.get('case_number', 'N/A')}\n"
                                    f"To: {contact_email or case_data.get('customer_email', 'N/A')}"
                        }
                    }
                ],
                text="Email sent successfully"
            )
            del draft_cache[draft_id]
        else:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Failed to send email: {result.get('error', 'Unknown error')}"
            )

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=body["user"]["id"],
            text=f"Error sending email: {str(e)}"
        )


@app.action("edit_draft")
def handle_edit_draft(ack, body, client):
    """Open a modal to edit the draft."""
    ack()

    draft_id = body["actions"][0]["value"]
    cached = draft_cache.get(draft_id)

    if not cached:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=body["user"]["id"],
            text="Draft expired. Please regenerate."
        )
        return

    draft = cached["draft"]

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": f"edit_draft_modal_{draft_id}",
            "title": {"type": "plain_text", "text": "Edit Draft"},
            "submit": {"type": "plain_text", "text": "Save"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "subject_block",
                    "label": {"type": "plain_text", "text": "Subject"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "subject_input",
                        "initial_value": draft.get("subject", "")
                    }
                },
                {
                    "type": "input",
                    "block_id": "body_block",
                    "label": {"type": "plain_text", "text": "Body"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "body_input",
                        "multiline": True,
                        "initial_value": draft.get("body", "")
                    }
                }
            ],
            "private_metadata": json.dumps({
                "draft_id": draft_id,
                "channel_id": body["channel"]["id"],
                "message_ts": body["message"]["ts"]
            })
        }
    )


@app.view_regex(r"edit_draft_modal_.*")
def handle_edit_draft_submission(ack, body, client, view):
    """Handle the edit draft modal submission."""
    ack()

    metadata = json.loads(view["private_metadata"])
    draft_id = metadata["draft_id"]
    channel_id = metadata["channel_id"]
    message_ts = metadata["message_ts"]

    cached = draft_cache.get(draft_id)
    if not cached:
        return

    new_subject = view["state"]["values"]["subject_block"]["subject_input"]["value"]
    new_body = view["state"]["values"]["body_block"]["body_input"]["value"]

    cached["draft"]["subject"] = new_subject
    cached["draft"]["body"] = new_body

    blocks = build_draft_message_blocks(cached["case_data"], cached["draft"], draft_id)

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=blocks,
        text=f"Email draft for Case {cached['case_data'].get('case_number', 'N/A')}"
    )


@app.action("regenerate_draft")
def handle_regenerate_draft(ack, body, client):
    """Open a modal for regeneration feedback."""
    ack()

    draft_id = body["actions"][0]["value"]
    cached = draft_cache.get(draft_id)

    if not cached:
        client.chat_postEphemeral(
            channel=body["channel"]["id"],
            user=body["user"]["id"],
            text="Draft expired. Please regenerate."
        )
        return

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": f"regenerate_modal_{draft_id}",
            "title": {"type": "plain_text", "text": "Regenerate Draft"},
            "submit": {"type": "plain_text", "text": "Regenerate"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "feedback_block",
                    "label": {"type": "plain_text", "text": "What would you like to change?"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "feedback_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "E.g., 'Make it more apologetic' or 'Add shipping timeline'"
                        }
                    }
                }
            ],
            "private_metadata": json.dumps({
                "draft_id": draft_id,
                "channel_id": body["channel"]["id"],
                "message_ts": body["message"]["ts"]
            })
        }
    )


@app.view_regex(r"regenerate_modal_.*")
def handle_regenerate_submission(ack, body, client, view):
    """Handle the regenerate modal submission."""
    ack()

    metadata = json.loads(view["private_metadata"])
    draft_id = metadata["draft_id"]
    channel_id = metadata["channel_id"]
    message_ts = metadata["message_ts"]

    cached = draft_cache.get(draft_id)
    if not cached:
        return

    feedback = view["state"]["values"]["feedback_block"]["feedback_input"]["value"]

    new_draft = refine_draft(cached["draft"], feedback)
    cached["draft"] = new_draft

    blocks = build_draft_message_blocks(cached["case_data"], new_draft, draft_id)

    client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=blocks,
        text=f"Email draft for Case {cached['case_data'].get('case_number', 'N/A')}"
    )


@app.action("cancel_draft")
def handle_cancel_draft(ack, body, client):
    """Handle the Cancel button click."""
    ack()

    draft_id = body["actions"][0]["value"]

    if draft_id in draft_cache:
        del draft_cache[draft_id]

    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Draft cancelled*"
                }
            }
        ],
        text="Draft cancelled"
    )


def start_bolt_app():
    """Start the Slack Bolt app in Socket Mode."""
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("Starting Slack Bolt app in Socket Mode...")
    handler.start()


if __name__ == "__main__":
    start_bolt_app()
