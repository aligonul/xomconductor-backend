import json
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN, ALI_SLACK_CHANNEL_ID
from claude_drafter import draft_email, refine_draft
from sf_email import sf_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

draft_cache = {}


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
