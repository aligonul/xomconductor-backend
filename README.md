# XomConductor Backend

Xometry Case Manager (CM) Operation Automation Engine — Integrates Slack Bolt Bot with Action Blocks, Claude for AI drafting, and Salesforce for case management.

## Features

- **Slack Bot with Socket Mode** - Real-time interaction without public endpoints
- **Interactive Modals** - Easy case input with tone selection
- **Claude-Powered Drafting** - AI generates professional email responses
- **Action Blocks** - Approve, refine, regenerate, or discard drafts inline
- **Refinement Loop** - Iteratively improve drafts with natural language feedback
- **Salesforce Integration** - Lookup cases, auto-fill details, send emails directly

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

### 2. Set up Salesforce (Optional)

1. Get your Salesforce credentials:
   - Username (your SF login email)
   - Password
   - Security Token (Setup → Personal Settings → Reset My Security Token)
2. For sandbox environments, set `SF_DOMAIN=test`

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

### Salesforce Actions (when SF is configured)
- **Send via Salesforce** - Send the email directly through SF
- **Save as SF Draft** - Save as an email draft in Salesforce
- **Add as Case Comment** - Add the content as an internal case comment

## Project Structure

```
src/xomconductor/
├── app.py              # Main Slack Bolt app & Socket Mode handler
├── blocks.py           # Slack Block Kit UI components
├── claude_service.py   # Claude API integration for drafting
├── config.py           # Environment configuration
├── draft_store.py      # In-memory draft storage
├── handlers.py         # Slack event & action handlers
└── salesforce_service.py # Salesforce API integration
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | App-Level Token for Socket Mode (`xapp-...`) |
| `ALI_SLACK_CHANNEL_ID` | Yes | Channel ID for posting drafts |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `CLAUDE_MODEL` | No | Model override (default: `claude-sonnet-4-20250514`) |
| `SF_USERNAME` | No | Salesforce username |
| `SF_PASSWORD` | No | Salesforce password |
| `SF_SECURITY_TOKEN` | No | Salesforce security token |
| `SF_DOMAIN` | No | `login` (production) or `test` (sandbox) |

## Salesforce Setup

### Getting Your Security Token

1. Log into Salesforce
2. Click your avatar → **Settings**
3. Search for "Reset My Security Token"
4. Click **Reset Security Token**
5. Check your email for the new token

### Required Salesforce Permissions

The SF user needs access to:
- Case object (read)
- Contact object (read)
- Account object (read)
- CaseComment object (create)
- EmailMessage object (create)

### API Access

Ensure API access is enabled for your Salesforce user profile:
1. Setup → Profiles → [Your Profile]
2. Check "API Enabled" is true
