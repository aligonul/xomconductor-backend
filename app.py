"""
Xomconductor Backend API.

Flask application providing the /extension_trigger endpoint for
Claude-powered email drafting.
"""

import os
from flask import Flask, request, jsonify
from anthropic import Anthropic

from claude_drafter import build_system_prompt, detect_case_type

app = Flask(__name__)

anthropic_client = None

MOCK_MODE = os.environ.get("ANTHROPIC_API_KEY", "").startswith("test_") or \
            os.environ.get("MOCK_MODE", "").lower() == "true"


def get_anthropic_client() -> Anthropic:
    """Get or create the Anthropic client singleton."""
    global anthropic_client
    if anthropic_client is None:
        anthropic_client = Anthropic()
    return anthropic_client


def mock_draft_email(job_data: dict) -> dict:
    case_type = job_data.get("case_type") or detect_case_type(job_data.get("vendor_note", ""))
    customer = job_data.get("customer_name", "Valued Customer")
    job_id = job_data.get("job_id", "N/A")
    cm_name = job_data.get("cm_name", "Your Xometry Case Manager")
    vendor_note = job_data.get("vendor_note", "")

    subject = f"Update Regarding Your Order #{job_id}"
    body = (
        f"Dear {customer},\n\n"
        f"Thank you for reaching out to Xometry. I wanted to follow up regarding your order #{job_id}.\n\n"
        f"We have reviewed your request: \"{vendor_note[:120]}{'...' if len(vendor_note) > 120 else ''}\"\n\n"
        f"Our team is actively working on this and will provide a full update shortly. "
        f"Please don't hesitate to contact us if you have any questions in the meantime.\n\n"
        f"Best regards,\n{cm_name}"
    )
    return {"subject": subject, "body": body, "case_type": case_type, "model": "mock"}


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "xomconductor-backend"})


@app.route("/extension_trigger", methods=["POST"])
def extension_trigger():
    """
    Trigger Claude email drafting from browser extension.

    Expected JSON payload (job_data):
        - vendor_note: str - The vendor/customer note (required)
        - customer_name: str - Customer's name
        - job_id: str - Job/order ID
        - case_type: str - Optional explicit case type
        - cm_name: str - Case manager's name
        - Additional fields as needed

    Returns:
        JSON response with:
            - email_body: str - The drafted email (includes subject)
            - subject: str - Extracted subject line
            - case_type: str - Detected or provided case type
            - success: bool - Whether drafting succeeded
    """
    try:
        job_data = request.get_json()

        if not job_data:
            return jsonify({
                "success": False,
                "error": "No JSON payload provided"
            }), 400

        vendor_note = job_data.get("vendor_note", "")
        if not vendor_note:
            return jsonify({
                "success": False,
                "error": "vendor_note is required"
            }), 400

        if MOCK_MODE:
            result = mock_draft_email(job_data)
            return jsonify({
                "success": True,
                "email_body": result["body"],
                "subject": result["subject"],
                "case_type": result["case_type"],
                "full_response": f"Subject: {result['subject']}\n\n{result['body']}",
                "mock": True,
            })

        system_prompt = build_system_prompt(job_data)

        client = get_anthropic_client()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": vendor_note}
            ]
        )

        raw_response = response.content[0].text

        subject = ""
        body = raw_response

        lines = raw_response.split("\n")
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
                body = "\n".join(lines[i + 1:]).strip()
                break

        detected_case_type = job_data.get("case_type") or detect_case_type(vendor_note)

        return jsonify({
            "success": True,
            "email_body": body,
            "subject": subject,
            "case_type": detected_case_type,
            "full_response": raw_response
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/case_types", methods=["GET"])
def list_case_types():
    """List all available case types and their descriptions."""
    from knowledge.cm_l2g_context import PROCEDURES_MAP

    case_types = {
        key: {
            "name": proc["name"],
            "description": proc["description"]
        }
        for key, proc in PROCEDURES_MAP.items()
    }

    return jsonify({
        "success": True,
        "case_types": case_types
    })


@app.route("/templates", methods=["GET"])
def list_templates():
    """List all available email templates."""
    from knowledge.email_templates import EMAIL_TEMPLATES

    templates = {
        key: {
            "name": tmpl["name"],
            "subject": tmpl["subject"]
        }
        for key, tmpl in EMAIL_TEMPLATES.items()
    }

    return jsonify({
        "success": True,
        "templates": templates
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
