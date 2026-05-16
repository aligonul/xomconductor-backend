# XomConductor Backend

Xometry Case Manager (CM) Operation Automation Engine — Integrates Slack Bolt Bot with Action Blocks, Claude for AI drafting, Salesforce for case management, and Gmail for email sending.

## Features

- **Slack Bot with Socket Mode** - Real-time interaction without public endpoints
- **Interactive Modals** - Easy case input with tone selection
- **Claude-Powered Drafting** - AI generates professional email responses
- **Action Blocks** - Approve, refine, regenerate, or discard drafts inline
- **Refinement Loop** - Iteratively improve drafts with natural language feedback
- **Salesforce Integration** - Lookup cases, auto-fill details, send emails directly
- **Gmail Integration** - Send emails via Gmail with automatic CC to global_cms@xometry.com

## Quick Start

### 1. Set up Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create/select your app
2. **OAuth & Permissions** → Add Bot Token Scopes:
   - `chat:write`, `chat:write.public`
   - `channels:read`, `groups:read`
3. **Socket Mode** → Enable and generate an App Token with `connections:write`
4. **Slash Commands** → Create `/draft` command
5. **Interactivity** → Enable (no URL needed for Socket Mode)
6. Install app to workspace and add bot to your channel

### 2. Set up Email Sending

**Option A: Gmail (Recommended for SSO orgs)**
1. Enable 2FA on your Google account
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password for "Mail"
4. Add to `.env`:
   ```bash
   GMAIL_ADDRESS=your.email@gmail.com
   GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   GMAIL_DEFAULT_CC=global_cms@xometry.com
   ```

**Option B: Salesforce Direct** (requires non-SSO org or Connected App)
- See Salesforce Setup section below

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 4. Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Test connection
python test_slack_connection.py

# Run the bot
python run.py
```

## Usage

### Slash Command
Type `/draft` in any channel to open the email drafting modal.

### App Home
- **Draft New Email** - Open the drafting modal
- **Lookup Case** - Search for a Salesforce case

### Draft Actions
- **Approve & Copy** - Finalize draft for pasting into Salesforce
- **Refine** - Provide feedback to improve the draft
- **Regenerate** - Create a fresh draft
- **Discard** - Remove the draft

### Email Actions
- **Send via Gmail** - Send with automatic CC to global_cms@xometry.com
- **Send via Salesforce** - Send & log to case (if SF configured)
- **Save as SF Draft** - Save as email draft in Salesforce
- **Add as Case Comment** - Add as internal case comment

## Project Structure

```
src/xomconductor/
├── app.py              # Main Slack Bolt app & Socket Mode handler
├── blocks.py           # Slack Block Kit UI components
├── claude_service.py   # Claude API integration for drafting
├── config.py           # Environment configuration
├── draft_store.py      # In-memory draft storage
├── gmail_service.py    # Gmail SMTP integration
├── handlers.py         # Slack event & action handlers
└── salesforce_service.py # Salesforce API integration
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | App-Level Token for Socket Mode (`xapp-...`) |
| `ALI_SLACK_CHANNEL_ID` | Channel ID for posting drafts |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |

### Gmail (Recommended)

| Variable | Description |
|----------|-------------|
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | App-specific password (16 chars) |
| `GMAIL_DEFAULT_CC` | CC address for all emails (default: `global_cms@xometry.com`) |

### Salesforce (Optional)

**For SSO orgs (Okta):**

| Variable | Description |
|----------|-------------|
| `SF_ACCESS_TOKEN` | OAuth access token or session ID |
| `SF_INSTANCE_URL` | e.g., `https://xometry5836.my.salesforce.com` |

**For non-SSO orgs:**

| Variable | Description |
|----------|-------------|
| `SF_USERNAME` | Salesforce username |
| `SF_PASSWORD` | Salesforce password |
| `SF_SECURITY_TOKEN` | Security token |
| `SF_DOMAIN` | `login` (prod) or `test` (sandbox) |

## Salesforce Setup for SSO Orgs (Xometry)

Since Xometry uses Okta SSO, you have two options:

### Option 1: Use Gmail for sending (Recommended)
Just configure Gmail - you can still lookup cases if you have SF OAuth access.

### Option 2: Get OAuth Access Token
1. Ask your SF Admin to create a **Connected App** with:
   - OAuth scopes: `api`, `refresh_token`
   - Callback URL for your local dev
2. Complete OAuth flow to get access token
3. Add to `.env`:
   ```bash
   SF_ACCESS_TOKEN=your-access-token
   SF_INSTANCE_URL=https://xometry5836.my.salesforce.com
   ```

### Option 3: Browser Session (Temporary)
1. Log into Salesforce via Okta
2. Open browser dev tools → Application → Cookies
3. Copy the `sid` cookie value
4. Add to `.env` (expires when session ends):
   ```bash
   SF_ACCESS_TOKEN=sid-cookie-value
   SF_INSTANCE_URL=https://xometry5836.my.salesforce.com
   ```

## Gmail App Password Setup

1. Go to your Google Account settings
2. Security → 2-Step Verification → Turn on
3. Go to https://myaccount.google.com/apppasswords
4. Select app: "Mail"
5. Select device: "Other" → name it "XomConductor"
6. Copy the 16-character password
7. Add to your `.env` file
