"""Slack event and action handlers."""

import os
from slack_bolt import App

from . import blocks, claude_service, salesforce_service, gmail_service
from .config import config
from .draft_store import store


def register_handlers(app: App) -> None:
    """Register all Slack handlers with the app."""

    sf_enabled = salesforce_service.is_configured()
    gmail_enabled = gmail_service.is_configured()
    default_cc = os.getenv("GMAIL_DEFAULT_CC", "global_cms@xometry.com")

    @app.event("app_home_opened")
    def handle_app_home(client, event):
        """Update the App Home tab when opened."""
        sf_connected = False
        if sf_enabled:
            try:
                salesforce_service.get_client().connect()
                sf_connected = True
            except Exception:
                pass

        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": blocks.home_tab_blocks(sf_connected=sf_connected),
            },
        )

    @app.command("/draft")
    def handle_draft_command(ack, body, client):
        """Handle /draft slash command to open the draft modal."""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.case_input_modal(sf_enabled=sf_enabled),
        )

    @app.action("open_draft_modal")
    def handle_open_draft_modal(ack, body, client):
        """Handle button click to open draft modal from App Home."""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.case_input_modal(sf_enabled=sf_enabled),
        )

    @app.action("open_case_lookup")
    def handle_open_case_lookup(ack, body, client):
        """Open case lookup modal."""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=blocks.case_lookup_modal(),
        )

    @app.view("case_lookup_modal")
    def handle_case_lookup_submit(ack, body, client, view):
        """Handle case lookup submission."""
        ack()

        search_term = view["state"]["values"]["case_search_block"]["case_search"]["value"]
        user_id = body["user"]["id"]
        channel_id = config.slack_channel_id

        if not sf_enabled:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="Salesforce is not configured. Please add SF credentials to your .env file.",
            )
            return

        try:
            sf = salesforce_service.get_client()
            case = sf.get_case_by_number(search_term)

            if not case:
                cases = sf.search_cases(search_term, limit=5)
                if cases:
                    case = cases[0]

            if not case:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"No case found matching '{search_term}'",
                )
                return

            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks.case_details_blocks(case),
                text=f"Case {case.case_number}: {case.subject}",
            )

        except Exception as e:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=f"Error looking up case: {e}",
            )

    @app.action("draft_for_case")
    def handle_draft_for_case(ack, body, client):
        """Open draft modal pre-filled with case details."""
        ack()
        sf_case_id = body["actions"][0]["value"]

        try:
            sf = salesforce_service.get_client()
            case = sf.get_case_by_id(sf_case_id)

            if not case:
                return

            client.views_open(
                trigger_id=body["trigger_id"],
                view=blocks.case_input_modal(
                    sf_enabled=True,
                    prefill_case_number=case.case_number,
                    prefill_customer_name=case.contact_name,
                    prefill_customer_email=case.contact_email,
                    prefill_issue_summary=f"{case.subject}\n\n{case.description[:500] if case.description else ''}",
                ),
            )
        except Exception:
            client.views_open(
                trigger_id=body["trigger_id"],
                view=blocks.case_input_modal(sf_enabled=sf_enabled),
            )

    @app.action("lookup_sf_case")
    def handle_inline_sf_lookup(ack, body, client):
        """Handle inline SF lookup from within the draft modal."""
        ack()
        # Note: This action happens within the modal but Slack's block actions
        # in modals don't allow updating the view directly. User must reopen.
        # For now, we'll post an ephemeral message with instructions.

    @app.view("draft_email_modal")
    def handle_draft_submission(ack, body, client, view):
        """Handle the draft email modal submission."""
        ack()

        values = view["state"]["values"]
        case_number = values["case_number_block"]["case_number"]["value"]
        customer_name = values["customer_name_block"]["customer_name"]["value"]
        customer_email = values.get("customer_email_block", {}).get("customer_email", {}).get("value") or ""
        issue_summary = values["issue_summary_block"]["issue_summary"]["value"]
        tone = values["tone_block"]["tone"]["selected_option"]["value"]
        additional_context = values["context_block"]["additional_context"]["value"] or ""

        user_id = body["user"]["id"]
        channel_id = config.slack_channel_id

        # Try to get SF case ID
        sf_case_id = None
        if sf_enabled and case_number:
            try:
                sf = salesforce_service.get_client()
                case = sf.get_case_by_number(case_number)
                if case:
                    sf_case_id = case.id
                    if not customer_email and case.contact_email:
                        customer_email = case.contact_email
                    if not customer_name and case.contact_name:
                        customer_name = case.contact_name
            except Exception:
                pass

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
            customer_email=customer_email,
            subject=draft_result["subject"],
            body=draft_result["body"],
            tone=tone,
            user_id=user_id,
            channel_id=channel_id,
            sf_case_id=sf_case_id,
            issue_summary=issue_summary,
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
                customer_email=customer_email,
                sf_case_id=sf_case_id,
                sf_enabled=sf_enabled,
                gmail_enabled=gmail_enabled,
                default_cc=default_cc,
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
                customer_email=draft.customer_email,
                sf_case_id=draft.sf_case_id,
                sf_enabled=sf_enabled,
                gmail_enabled=gmail_enabled,
                default_cc=default_cc,
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

        # Use stored issue_summary if available
        issue_summary = draft.issue_summary or f"(Regenerating based on previous draft about: {draft.subject})"

        new_draft = claude_service.draft_email(
            case_number=draft.case_number,
            customer_name=draft.customer_name,
            issue_summary=issue_summary,
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
                customer_email=draft.customer_email,
                sf_case_id=draft.sf_case_id,
                sf_enabled=sf_enabled,
                gmail_enabled=gmail_enabled,
                default_cc=default_cc,
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

    # Salesforce-specific actions
    @app.action("send_via_sf")
    def handle_send_via_sf(ack, body, client):
        """Send the email through Salesforce."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft or not draft.sf_case_id or not draft.customer_email:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text="Cannot send: missing case ID or customer email.",
            )
            return

        try:
            sf = salesforce_service.get_client()
            email_id = sf.send_email_from_case(
                case_id=draft.sf_case_id,
                to_address=draft.customer_email,
                subject=draft.subject,
                body=draft.body,
            )

            client.chat_update(
                channel=draft.channel_id,
                ts=draft.message_ts,
                text=f"Email sent for Case {draft.case_number}",
                blocks=[
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"Sent: Case {draft.case_number}"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*To:* {draft.customer_email}\n*Subject:* {draft.subject}"},
                    },
                    {"type": "divider"},
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"Email sent via Salesforce (ID: {email_id})"},
                        ],
                    },
                ],
            )

            store.delete(draft_id)

        except Exception as e:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Failed to send email: {e}",
            )

    @app.action("save_sf_draft")
    def handle_save_sf_draft(ack, body, client):
        """Save as draft in Salesforce."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft or not draft.sf_case_id:
            return

        try:
            sf = salesforce_service.get_client()
            email_id = sf.create_email_draft(
                case_id=draft.sf_case_id,
                to_address=draft.customer_email or "",
                subject=draft.subject,
                body=draft.body,
            )

            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Draft saved to Salesforce (ID: {email_id}). Open the case in SF to review and send.",
            )

        except Exception as e:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Failed to save draft: {e}",
            )

    @app.action("add_case_comment")
    def handle_add_case_comment(ack, body, client):
        """Add the email content as a case comment."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft or not draft.sf_case_id:
            return

        try:
            sf = salesforce_service.get_client()
            comment_body = f"Subject: {draft.subject}\n\n{draft.body}"
            comment_id = sf.add_case_comment(
                case_id=draft.sf_case_id,
                comment_body=comment_body,
                is_public=False,
            )

            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Added as internal comment to Case {draft.case_number} (ID: {comment_id})",
            )

        except Exception as e:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Failed to add comment: {e}",
            )

    # Gmail action
    @app.action("send_via_gmail")
    def handle_send_via_gmail(ack, body, client):
        """Send the email via Gmail SMTP."""
        ack()
        draft_id = body["actions"][0]["value"]
        draft = store.get(draft_id)

        if not draft or not draft.customer_email:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text="Cannot send: missing customer email.",
            )
            return

        result = gmail_service.send_email(
            to_address=draft.customer_email,
            subject=draft.subject,
            body=draft.body,
        )

        if result.success:
            client.chat_update(
                channel=draft.channel_id,
                ts=draft.message_ts,
                text=f"Email sent for Case {draft.case_number}",
                blocks=[
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"Sent: Case {draft.case_number}"},
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*To:* {draft.customer_email}\n*CC:* {default_cc}\n*Subject:* {draft.subject}",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": "Email sent via Gmail"},
                        ],
                    },
                ],
            )
            store.delete(draft_id)
        else:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=body["user"]["id"],
                text=f"Failed to send email: {result.error}",
            )
