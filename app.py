"""
Xomconductor Backend API.

Flask application providing endpoints for Chrome extension integration
and Claude-powered email drafting with Slack workflow.
"""

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import FLASK_PORT, FLASK_DEBUG, ALI_SLACK_CHANNEL_ID
from claude_drafter import draft_email, detect_case_type, build_system_prompt
from bolt_app import post_draft_to_channel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "xomconductor-backend"})


@app.route("/extension_trigger", methods=["POST"])
def extension_trigger():
    """
    Endpoint triggered by the Chrome extension when a case action is initiated.

    Expected payload:
    {
        "case_id": "5001234567890",
        "case_number": "12345678",
        "customer_name": "John Doe",
        "customer_email": "john.doe@example.com",
        "issue_summary": "Customer reported delayed shipment",
        "vendor_note": "Customer says order is late",
        "requested_action": "apology",
        "tone": "empathetic",
        "additional_context": "Order was 3 days late due to carrier issues",
        "erp_timezone": "America/New_York",
        "case_type": "delay_short"
    }

    Returns:
        JSON with draft_id, draft content, and detected case_type
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        required_fields = ["case_id", "case_number"]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        if not data.get("issue_summary") and not data.get("vendor_note"):
            return jsonify({
                "error": "Either issue_summary or vendor_note is required"
            }), 400

        logger.info(f"Extension trigger received for case: {data.get('case_number')}")

        case_context = {
            "case_number": data.get("case_number"),
            "customer_name": data.get("customer_name", "Valued Customer"),
            "issue_summary": data.get("issue_summary", ""),
            "vendor_note": data.get("vendor_note", data.get("issue_summary", "")),
            "requested_action": data.get("requested_action", "general response"),
            "tone": data.get("tone", "professional"),
            "additional_context": data.get("additional_context", ""),
            "case_type": data.get("case_type")
        }

        draft = draft_email(case_context)

        case_data = {
            "case_id": data.get("case_id"),
            "case_number": data.get("case_number"),
            "customer_name": data.get("customer_name", "Valued Customer"),
            "customer_email": data.get("customer_email", ""),
            "erp_timezone": data.get("erp_timezone", "UTC")
        }

        draft_id = post_draft_to_channel(case_data, draft, ALI_SLACK_CHANNEL_ID)

        return jsonify({
            "success": True,
            "draft_id": draft_id,
            "message": "Draft posted to Slack channel for review",
            "draft": draft,
            "case_type": draft.get("case_type", "general_inquiry")
        })

    except Exception as e:
        logger.error(f"Error processing extension trigger: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/draft_email", methods=["POST"])
def api_draft_email():
    """
    Direct API endpoint for generating email drafts without Slack posting.

    Expected payload:
    {
        "case_number": "12345678",
        "customer_name": "John Doe",
        "issue_summary": "Customer reported delayed shipment",
        "vendor_note": "Customer says order is late",
        "requested_action": "apology",
        "tone": "empathetic",
        "additional_context": "Order was 3 days late",
        "case_type": "delay_short"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        if not data.get("issue_summary") and not data.get("vendor_note"):
            return jsonify({"error": "Either issue_summary or vendor_note is required"}), 400

        draft = draft_email(data)

        return jsonify({
            "success": True,
            "draft": draft,
            "case_type": draft.get("case_type", "general_inquiry")
        })

    except Exception as e:
        logger.error(f"Error generating draft: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/detect_case_type", methods=["POST"])
def api_detect_case_type():
    """
    Detect case type from vendor note text.

    Expected payload:
    {
        "vendor_note": "Customer says the parts don't match the 3D model"
    }

    Returns:
        Detected case type key
    """
    try:
        data = request.get_json()
        vendor_note = data.get("vendor_note", "")
        case_type = detect_case_type(vendor_note)
        return jsonify({
            "success": True,
            "case_type": case_type
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


def run_flask():
    """Run the Flask application."""
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    run_flask()
