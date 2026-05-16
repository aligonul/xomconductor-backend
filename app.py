"""
XomConductor Backend — Core Engine
Listens for live ERP alerts from the Chrome extension, filters by CM ownership,
and dispatches intelligent Slack notifications with Claude-powered action buttons.
"""

import os
import logging
from flask import Flask, request, jsonify
from slack_bolt import App as BoltApp
from slack_bolt.adapter.flask import SlackRequestHandler
import anthropic

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("xomconductor")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
slack_app = BoltApp(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CM_OWNER_FILTER = "Ali Gönül"
# The Slack channel/DM ID where Ali receives private alerts.
# Set via env var so it never needs to be hard-coded.
ALI_CHANNEL_ID = os.environ.get("ALI_SLACK_CHANNEL_ID", "")


# ---------------------------------------------------------------------------
# Slack Block Builder
# ---------------------------------------------------------------------------
def _build_alert_blocks(payload: dict) -> list:
    """Compose a clean Block Kit message for the incoming ERP alert."""
    job_id = payload.get("job_id", "N/A")
    timezone = payload.get("timezone", "N/A")
    vendor_alert = payload.get("vendor_alert", "")
    cm_name = payload.get("cm_name", "N/A")
    order_id = payload.get("order_id", "N/A")

    header_text = f":rotating_light: *New ERP Alert — Job `{job_id}`*"
    detail_lines = [
        f"*Order ID:* `{order_id}`",
        f"*CM / Owner:* {cm_name}",
        f"*Timezone:* {timezone}",
    ]
    if vendor_alert:
        detail_lines.append(f"*Vendor Note:* {vendor_alert}")

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "XomConductor Alert", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(detail_lines)},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"alert_actions_{job_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🚀 Push to Client (SF)", "emoji": True},
                    "style": "primary",
                    "action_id": "push_sf_email",
                    "value": job_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "⚠️ Escalate to AE", "emoji": True},
                    "style": "danger",
                    "action_id": "escalate_to_ae",
                    "value": job_id,
                },
            ],
        },
    ]


# ---------------------------------------------------------------------------
# CM Noise Filter + Dispatcher
# ---------------------------------------------------------------------------
def _dispatch_alert(payload: dict) -> None:
    """
    Core routing logic.
    Silently drops alerts where the CM/owner is not Ali Gönül.
    For Ali's jobs, fires a private Slack Block message to his channel.
    """
    cm_name = payload.get("cm_name", "").strip()

    if cm_name != CM_OWNER_FILTER:
        log.info(
            "Alert for CM '%s' suppressed — not in filter scope (job_id=%s).",
            cm_name,
            payload.get("job_id"),
        )
        return

    if not ALI_CHANNEL_ID:
        log.error("ALI_SLACK_CHANNEL_ID is not set. Cannot route the alert.")
        return

    blocks = _build_alert_blocks(payload)

    slack_app.client.chat_postMessage(
        channel=ALI_CHANNEL_ID,
        text=f"New ERP alert for job {payload.get('job_id', '?')}",  # fallback plain text
        blocks=blocks,
    )
    log.info("Alert dispatched to Ali's channel for job_id=%s.", payload.get("job_id"))


# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
flask_app = Flask(__name__)
slack_handler = SlackRequestHandler(slack_app)


@flask_app.route("/extension_trigger", methods=["POST"])
def extension_trigger():
    """
    Receives live ERP alert payloads from the Chrome/Opera browser extension.

    Expected JSON body:
    {
        "job_id":      "XOM-123456",
        "order_id":    "ORD-789",
        "cm_name":     "Ali Gönül",
        "timezone":    "America/New_York",
        "vendor_alert": "Vendor delayed — needs client update"
    }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or empty JSON body"}), 400

    job_id = payload.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 422

    log.info(
        "Extension trigger received: job_id=%s cm=%s tz=%s",
        job_id,
        payload.get("cm_name"),
        payload.get("timezone"),
    )

    try:
        _dispatch_alert(payload)
    except Exception:
        log.exception("Failed to dispatch alert for job_id=%s", job_id)
        return jsonify({"status": "error", "message": "Dispatch failed"}), 500

    return jsonify({"status": "ok", "job_id": job_id}), 200


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Entry point for all Slack Events API and interactive payloads."""
    return slack_handler.handle(request)


# ---------------------------------------------------------------------------
# Slack Action Handlers
# ---------------------------------------------------------------------------
@slack_app.action("push_sf_email")
def handle_push_sf_email(ack, body, client):
    """
    Triggered when the '🚀 Push to Client (SF)' button is pressed.
    Uses Claude to draft a professional Salesforce email, then opens a modal
    so Ali can review/edit before sending.
    """
    ack()

    job_id = body["actions"][0]["value"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    trigger_id = body["trigger_id"]

    log.info("SF email action triggered for job_id=%s by user=%s", job_id, body["user"]["id"])

    try:
        draft = _draft_sf_email_with_claude(job_id)
    except Exception:
        log.exception("Claude email draft failed for job_id=%s", job_id)
        draft = f"[Draft unavailable — Claude error]\n\nJob ID: {job_id}"

    # Open a review modal so Ali can refine before sending
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "sf_email_modal",
            "title": {"type": "plain_text", "text": "Review SF Email Draft"},
            "submit": {"type": "plain_text", "text": "Send to Salesforce"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": job_id,
            "blocks": [
                {
                    "type": "input",
                    "block_id": "email_body_block",
                    "label": {"type": "plain_text", "text": "Email Draft (Claude)"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "email_body_input",
                        "multiline": True,
                        "initial_value": draft,
                    },
                }
            ],
        },
    )


@slack_app.action("escalate_to_ae")
def handle_escalate_to_ae(ack, body, client):
    """
    Triggered when the '⚠️ Escalate to AE' button is pressed.
    Placeholder: will route the job to the Account Executive escalation workflow.
    """
    ack()

    job_id = body["actions"][0]["value"]
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]

    log.info("AE escalation triggered for job_id=%s by user=%s", job_id, user_id)

    # TODO: Implement AE escalation workflow
    # e.g. post to AE channel, create Salesforce task, send email to AE team
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=f":construction: AE escalation for job `{job_id}` is queued. (Workflow coming soon.)",
    )


@slack_app.view("sf_email_modal")
def handle_sf_email_modal_submit(ack, body, client, view):
    """
    Handles the modal submission after Ali reviews/edits the Claude email draft.
    Placeholder: will push the final email into Salesforce via SF API.
    """
    ack()

    job_id = view["private_metadata"]
    email_body = view["state"]["values"]["email_body_block"]["email_body_input"]["value"]
    user_id = body["user"]["id"]

    log.info("SF email modal submitted for job_id=%s by user=%s", job_id, user_id)

    # TODO: Integrate with Salesforce API to send the email
    # e.g. sf_client.send_case_email(job_id=job_id, body=email_body)

    client.chat_postMessage(
        channel=ALI_CHANNEL_ID or user_id,
        text=f":white_check_mark: SF email for job `{job_id}` submitted for sending. (SF integration pending.)",
    )


# ---------------------------------------------------------------------------
# Claude Helper
# ---------------------------------------------------------------------------
def _draft_sf_email_with_claude(job_id: str, extra_context: str = "") -> str:
    """
    Calls Claude to draft a concise, professional client-facing Salesforce email
    for the given job. Returns the raw email text.
    """
    system_prompt = (
        "You are an expert Xometry Case Manager assistant. "
        "Draft concise, professional, client-facing emails for job status updates. "
        "Tone: warm but efficient. No fluff. Always include the Job ID in the subject line."
    )

    user_prompt = (
        f"Draft a Salesforce case update email to the client for Job ID: {job_id}.\n"
        f"Context: {extra_context or 'Vendor delay — client needs a status update.'}\n"
        "Include: subject line, greeting, one-paragraph status summary, next steps, and sign-off."
    )

    message = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    log.info("XomConductor starting on port %d …", port)
    flask_app.run(host="0.0.0.0", port=port, debug=False)
