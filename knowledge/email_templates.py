"""
Xometry Approved Email Templates.

Structured dictionary of all approved email templates for CM operations.
Templates include placeholders for dynamic content injection.
"""

EMAIL_TEMPLATES = {
    "dfm": {
        "name": "DFM Review Feedback",
        "subject": "DFM Review Required - Order #{job_id}",
        "body": """Hi {customer_name},

Thank you for your order with Xometry. During our Design for Manufacturability (DFM) review, we identified the following items that require your attention:

{dfm_issues}

To proceed with your order, please:
{action_items}

Once we receive the updated files or your confirmation, we'll proceed with production immediately.

Please let me know if you have any questions or would like to discuss these items further.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "2d3d_diff": {
        "name": "2D/3D Drawing Discrepancy",
        "subject": "Drawing Clarification Needed - Order #{job_id}",
        "body": """Hi {customer_name},

While reviewing your order #{job_id}, we noticed a discrepancy between your 2D drawing and 3D model:

{discrepancy_details}

To ensure we manufacture your parts exactly to your specifications, please clarify which version should take precedence, or provide updated files.

Your order is on hold pending this clarification. Once resolved, we'll immediately resume production.

Thank you for your prompt attention to this matter.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "delay_short": {
        "name": "Short-Term Delay Notification",
        "subject": "Shipping Update - Order #{job_id}",
        "body": """Hi {customer_name},

I wanted to update you on your order #{job_id}.

We're experiencing a brief delay, and your new estimated delivery date is {new_delivery_date}. {delay_reason}

No action is needed on your end. We're working to get your parts to you as quickly as possible.

I apologize for any inconvenience this may cause. Please don't hesitate to reach out if you have any questions.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "delay_long": {
        "name": "Long-Term Delay Notification",
        "subject": "Important Update - Order #{job_id} Delivery Delay",
        "body": """Hi {customer_name},

I'm reaching out regarding a significant delay with your order #{job_id}.

{delay_explanation}

Your new estimated delivery date is {new_delivery_date}.

We understand this may impact your plans, and we want to offer the following options:
1. Continue with the order at the new timeline
2. Cancel the order for a full refund
3. {additional_option}

As a token of our apology, we'd like to offer {compensation}.

Please let me know how you'd like to proceed, and I'll personally ensure your order receives priority attention.

Sincerely,
{cm_name}
Xometry Case Manager"""
    },
    "qc_failed": {
        "name": "QC Failure Notification",
        "subject": "Quality Update - Order #{job_id}",
        "body": """Hi {customer_name},

During our quality inspection of your order #{job_id}, we identified an issue:

{qc_issue_details}

We're committed to delivering parts that meet your specifications. Here's what we're doing:
{resolution_action}

Your new estimated delivery date is {new_delivery_date}.

We apologize for this delay and appreciate your patience as we ensure your parts meet Xometry's quality standards.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "rma_new": {
        "name": "New RMA Confirmation",
        "subject": "RMA #{rma_number} - Return Instructions for Order #{job_id}",
        "body": """Hi {customer_name},

Thank you for contacting us regarding your order #{job_id}. We've initiated a return for the following:

{return_items}

Your RMA number is: {rma_number}

Please follow these return instructions:
1. Package parts securely in original or equivalent packaging
2. Include a copy of this email or write the RMA number on the outside
3. Ship to: {return_address}
4. Use the prepaid shipping label attached (if applicable)

Once we receive and inspect the parts, we will {resolution_type} within {resolution_timeline}.

Please let me know if you have any questions.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "rma_shipped": {
        "name": "RMA Replacement Shipped",
        "subject": "Replacement Parts Shipped - RMA #{rma_number}",
        "body": """Hi {customer_name},

Great news! Your replacement parts for RMA #{rma_number} have shipped.

Tracking Number: {tracking_number}
Carrier: {carrier}
Estimated Delivery: {delivery_date}

Shipped Items:
{shipped_items}

Thank you for your patience throughout this process. We value your business and are committed to your satisfaction.

Please let me know if there's anything else I can help with.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "cancellation": {
        "name": "Order Cancellation Confirmation",
        "subject": "Order #{job_id} Cancellation Confirmed",
        "body": """Hi {customer_name},

This email confirms the cancellation of your order #{job_id}.

Cancellation Details:
- Order Number: {job_id}
- Parts: {part_description}
- Refund Amount: {refund_amount}

{refund_details}

We're sorry to see this order cancelled. If there's anything we could have done differently, or if you have feedback to share, please don't hesitate to let me know.

We hope to have the opportunity to work with you again in the future.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "coupon": {
        "name": "Coupon/Discount Applied",
        "subject": "Discount Applied - Order #{job_id}",
        "body": """Hi {customer_name},

Good news! I've applied the {discount_type} to your order #{job_id}.

Discount Details:
- Code/Reason: {coupon_code}
- Discount Amount: {discount_amount}
- New Order Total: {new_total}

{additional_notes}

If you have any questions about this adjustment, please let me know.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "missing_parts": {
        "name": "Missing Parts Resolution",
        "subject": "Missing Parts - Order #{job_id} Resolution",
        "body": """Hi {customer_name},

I sincerely apologize that your order #{job_id} arrived incomplete. We take this seriously and are resolving it immediately.

Missing Items:
{missing_items}

Resolution:
{resolution_details}

Tracking Number: {tracking_number}
Estimated Delivery: {delivery_date}

As a token of apology for this inconvenience, {compensation}.

Thank you for bringing this to our attention, and again, I apologize for the error.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "apex_shipment": {
        "name": "APEX Expedited Shipment",
        "subject": "APEX Expedited Shipping Confirmed - Order #{job_id}",
        "body": """Hi {customer_name},

Your order #{job_id} has been upgraded to APEX expedited shipping.

Shipment Details:
- Carrier: {carrier}
- Tracking Number: {tracking_number}
- Guaranteed Delivery: {delivery_date} by {delivery_time}

{special_instructions}

{cost_note}

If you have any questions or need to make changes to delivery, please contact me immediately.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "2d_drawing_request": {
        "name": "2D Drawing Request",
        "subject": "2D Drawing Required - Order #{job_id}",
        "body": """Hi {customer_name},

To proceed with your order #{job_id}, we need a 2D drawing for the following part(s):

{parts_needing_drawings}

The 2D drawing should include:
- Critical dimensions and tolerances
- Surface finish requirements
- Thread specifications (if applicable)
- Any special notes or requirements

Accepted file formats: PDF, DWG, DXF

Please upload your drawing to {upload_link} or reply to this email with the file attached.

Your order is currently on hold. Once we receive the drawing, we'll resume production immediately.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "fair_report": {
        "name": "FAIR Report Confirmation",
        "subject": "FAIR Report - Order #{job_id}",
        "body": """Hi {customer_name},

{fair_status}

FAIR Report Details:
- Order: #{job_id}
- Part(s): {part_description}
- Report Format: {report_format}

{fair_details}

The FAIR report will be delivered {delivery_method}.

If you have any questions about the inspection process or report contents, please let me know.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "mcmaster_replacement": {
        "name": "McMaster-Carr Replacement",
        "subject": "Hardware Sourcing Update - Order #{job_id}",
        "body": """Hi {customer_name},

Regarding your order #{job_id}, I wanted to update you on the hardware component sourcing:

{mcmaster_details}

- McMaster Part Number: {mcmaster_pn}
- Description: {part_description}
- Quantity: {quantity}
- Lead Time: {lead_time}

{price_note}

This item will ship {shipping_method} with the rest of your order.

Please let me know if you have any questions or concerns.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "china_shipping_address": {
        "name": "China Shipping Address Request",
        "subject": "Shipping Address Required - Order #{job_id}",
        "body": """Hi {customer_name},

Your order #{job_id} is being manufactured at our China facility. To ensure smooth delivery, we need your complete shipping address in the following format:

Required Information:
1. Full Name (as it appears on ID for customs)
2. Company Name (if applicable)
3. Complete Street Address
4. City, Province/State
5. Postal Code
6. Country
7. Phone Number (including country code)
8. Email Address

Please also note:
- {customs_note}
- Estimated shipping time from China: {shipping_estimate}

Your order is on hold pending this information. Once received, we'll arrange shipment immediately.

Best regards,
{cm_name}
Xometry Case Manager"""
    },
    "on_hold_reminder": {
        "name": "Order On Hold Reminder",
        "subject": "Action Required - Order #{job_id} On Hold",
        "body": """Hi {customer_name},

This is a friendly reminder that your order #{job_id} is currently on hold, pending:

{hold_reason}

What we need from you:
{action_required}

Your order has been on hold since {hold_date}. {urgency_note}

To resume production, please {next_step}.

If you have any questions or need assistance, I'm happy to help.

Best regards,
{cm_name}
Xometry Case Manager"""
    }
}


def get_template(template_key: str) -> dict | None:
    """
    Retrieve an email template by key.

    Args:
        template_key: The template identifier (e.g., 'dfm', 'rma_new')

    Returns:
        Dictionary with template details or None if not found
    """
    return EMAIL_TEMPLATES.get(template_key.lower())


def get_all_template_keys() -> list[str]:
    """Return list of all available template keys."""
    return list(EMAIL_TEMPLATES.keys())


def format_template(template_key: str, **kwargs) -> dict | None:
    """
    Format a template with provided values.

    Args:
        template_key: The template identifier
        **kwargs: Values to substitute in the template

    Returns:
        Dictionary with formatted subject and body, or None if template not found
    """
    template = get_template(template_key)
    if not template:
        return None

    try:
        formatted_subject = template["subject"].format(**kwargs)
        formatted_body = template["body"].format(**kwargs)
        return {
            "name": template["name"],
            "subject": formatted_subject,
            "body": formatted_body
        }
    except KeyError:
        return {
            "name": template["name"],
            "subject": template["subject"],
            "body": template["body"]
        }
