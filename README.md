# xomconductor-backend

Xometry Case Manager (CM) Operation Automation Engine | Integrates ERP Timezones, Slack Bolt Bot with Action Blocks, and Claude for automated Salesforce Email drafting.

## Architecture

```
Chrome Extension
      │
      ▼
┌─────────────────┐     ┌─────────────────┐
│   Flask API     │────▶│  Claude Drafter │
│ /extension_     │     │  (Anthropic)    │
│    trigger      │     └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Slack Bolt Bot │────▶│   Salesforce    │
│  Action Blocks  │     │  Email API      │
└─────────────────┘     └─────────────────┘
```

## Features

- **Chrome Extension Integration**: Receives case data from browser extension
- **Claude Email Drafting**: Generates professional customer emails using Claude
- **Slack Interactive UI**: Review, edit, regenerate, or send emails via Slack buttons
- **Salesforce Integration**: Sends emails directly linked to SF Cases
- **Draft Refinement**: Iteratively improve drafts with natural language feedback

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### 3. Slack App Setup

Create a Slack app at https://api.slack.com/apps with:

**Bot Token Scopes:**
- `chat:write`
- `chat:write.public`

**Socket Mode:** Enable and create an App-Level Token with `connections:write`

**Interactivity:** Enable for action block buttons

### 4. Run the Application

```bash
python main.py
```

This starts both:
- Flask server on port 5000 (configurable via `FLASK_PORT`)
- Slack Bolt in Socket Mode

## API Endpoints

### POST /extension_trigger

Triggered by Chrome extension to initiate email drafting flow.

```json
{
  "case_id": "5001234567890",
  "case_number": "12345678",
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "issue_summary": "Delayed shipment reported",
  "requested_action": "apology",
  "tone": "empathetic",
  "additional_context": "3 days late due to carrier"
}
```

### POST /draft_email

Direct API for generating drafts without Slack posting.

### GET /health

Health check endpoint.

## Slack Actions

| Button | Action |
|--------|--------|
| **Send Email** | Sends via Salesforce, linked to Case |
| **Edit Draft** | Opens modal to manually edit subject/body |
| **Regenerate** | Prompts for feedback, refines with Claude |
| **Cancel** | Discards the draft |

## File Structure

```
xomconductor-backend/
├── app.py              # Flask endpoints
├── bolt_app.py         # Slack Bolt handlers
├── claude_drafter.py   # Claude API integration
├── sf_email.py         # Salesforce email client
├── config.py           # Environment configuration
├── main.py             # Entry point (runs both servers)
├── requirements.txt    # Python dependencies
└── .env.example        # Environment template
```

## License

Private - Xometry Internal Use
