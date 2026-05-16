"""Slack event and action handlers."""

from slack_bolt import App

from . import blocks, claude_service
from .config import config
from .draft_store import store


def register_handlers(app: App) -> None:
    """Register all Slack handlers with the app."""

    @app.event("app_home_opened")
    def handle_app_home(client, event):
        """Update the App Home tab when opened."""
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": blocks.home_tab_blocks(),
            },
        )

    @app.command("/draft")
    def handle_draft_command(ack, body, client):
        """Handle /draft slash command to open the draft modal."""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.case_input_modal(),
        )

    @app.action("open_draft_modal")
    def handle_open_draft_modal(ack, body, client):
        """Handle button click to open draft modal from App Home."""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.case_input_modal(),
        )

    @app.view("draft_email_modal")
    def handle_draft_submission(ack, body, client, view):
        """Handle the draft email modal submission."""
        ack()

        values = view["state"]["values"]
        case_number = values["case_number_block"]["case_number"]["value"]
        customer_name = values["customer_name_block"]["customer_name"]["value"]
        issue_summary = values["issue_summary_block"]["issue_summary"]["value"]
        tone = values["tone_block"]["tone"]["selected_option"]["value"]
        additional_context = values["context_block"]["additional_context"]["value"] or ""

        user_id = body["user"]["id"]
        channel_id = config.slack_channel_id

        # Send "generating" message
        result = client.chat_postMessage(
            channel=channel_id,
            text=f"Generating email draft for Case {case_number}...",
        )
        temp_ts = result["ts"]

        # Generate draft with Claude
        draft_result = claude_service.draft_email(
            case_number=case_number,
            customer_name=customer_name,
            issue_summary=issue_summary,
            tone=tone,
            additional_context=additional_context,
        )

        # Store draft
        draft = store.create(
            case_number=case_number,
            customer_name=customer_name,
            subject=draft_result["subject"],
            body=draft_result["body"],
            tone=tone,
            user_id=user_id,
            channel_id=channel_id,
        )

        # Update message with draft
        client.chat_update(
            channel=channel_id,
            ts=temp_ts,
            text=f"Email draft for Case {case_number}",
            blocks=blocks.email_draft_blocks(
                case_number=case_number,
                customer_name=customer_name,
                subject=draft_result["subject"],
                body=draft_result["body"],
                draft_id=draft.id,
            ),
        )
        store.set_message_ts(draft.id, temp_ts)

    @app.action("approve_draft")
    def handle_approve(ack, body, client):
        """Handle draft approval - copy to clipboard instruction."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft:
            return

        # Update message to show approved status
        client.chat_update(
            channel=draft.channel_id,
            ts=draft.message_ts,
            text=f"Approved email for Case {draft.case_number}",
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"Approved: Case {draft.case_number}"},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Subject:* {draft.subject}"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": draft.body},
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": "Copy the email above and paste into Salesforce"},
                    ],
                },
            ],
        )

        # Send ephemeral confirmation
        client.chat_postEphemeral(
            channel=draft.channel_id,
            user=body["user"]["id"],
            text=f"Draft approved! Copy the email content above and paste it into Salesforce Case {draft.case_number}.",
        )

        store.delete(draft_id)

    @app.action("refine_draft")
    def handle_refine(ack, body, client):
        """Open refinement modal."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft:
            return

        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.refine_modal(draft_id, draft.full_text),
        )

    @app.view("refine_email_modal")
    def handle_refine_submission(ack, body, client, view):
        """Handle refinement feedback submission."""
        ack()

        draft_id = view["private_metadata"]
        draft = store.get(draft_id)

        if not draft:
            return

        feedback = view["state"]["values"]["feedback_block"]["feedback"]["value"]

        # Refine with Claude
        refined = claude_service.refine_email(draft.full_text, feedback)

        # Update draft
        store.update(draft_id, refined["subject"] or draft.subject, refined["body"])
        draft = store.get(draft_id)

        # Update message
        client.chat_update(
            channel=draft.channel_id,
            ts=draft.message_ts,
            text=f"Refined email for Case {draft.case_number}",
            blocks=blocks.email_draft_blocks(
                case_number=draft.case_number,
                customer_name=draft.customer_name,
                subject=draft.subject,
                body=draft.body,
                draft_id=draft.id,
            ),
        )

    @app.action("regenerate_draft")
    def handle_regenerate(ack, body, client):
        """Regenerate the draft from scratch."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft:
            return

        # Show regenerating status
        client.chat_update(
            channel=draft.channel_id,
            ts=draft.message_ts,
            text=f"Regenerating draft for Case {draft.case_number}...",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"Regenerating draft for Case {draft.case_number}..."},
                },
            ],
        )

        # Regenerate (we don't have the original issue_summary stored, so we use a generic prompt)
        new_draft = claude_service.draft_email(
            case_number=draft.case_number,
            customer_name=draft.customer_name,
            issue_summary=f"(Regenerating based on previous draft about: {draft.subject})",
            tone=draft.tone,
        )

        store.update(draft_id, new_draft["subject"], new_draft["body"])
        draft = store.get(draft_id)

        client.chat_update(
            channel=draft.channel_id,
            ts=draft.message_ts,
            text=f"Regenerated email for Case {draft.case_number}",
            blocks=blocks.email_draft_blocks(
                case_number=draft.case_number,
                customer_name=draft.customer_name,
                subject=draft.subject,
                body=draft.body,
                draft_id=draft.id,
            ),
        )

    @app.action("discard_draft")
    def handle_discard(ack, body, client):
        """Discard the draft."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft:
            return

        client.chat_update(
            channel=draft.channel_id,
            ts=draft.message_ts,
            text="Draft discarded",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "~Draft discarded~"},
                },
            ],
        )

        store.delete(draft_id)
