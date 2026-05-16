# XomConductor Backend

Xometry Case Manager (CM) Operation Automation Engine — Integrates Slack Bolt Bot with Action Blocks and Claude for automated Salesforce email drafting.

## Features

- **Slack Bot with Socket Mode** - Real-time interaction without public endpoints
- **Interactive Modals** - Easy case input with tone selection
- **Claude-Powered Drafting** - AI generates professional email responses
- **Action Blocks** - Approve, refine, regenerate, or discard drafts inline
- **Refinement Loop** - Iteratively improve drafts with natural language feedback

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

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 3. Install & Run

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
Click **Draft New Email** button in the bot's App Home tab.

### Draft Actions
- **Approve & Copy** - Finalize draft for pasting into Salesforce
- **Refine** - Provide feedback to improve the draft
- **Regenerate** - Create a fresh draft
- **Discard** - Remove the draft

## Project Structure

```
src/xomconductor/
├── app.py           # Main Slack Bolt app & Socket Mode handler
├── blocks.py        # Slack Block Kit UI components
├── claude_service.py # Claude API integration for drafting
├── config.py        # Environment configuration
├── draft_store.py   # In-memory draft storage
└── handlers.py      # Slack event & action handlers
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | App-Level Token for Socket Mode (`xapp-...`) |
| `ALI_SLACK_CHANNEL_ID` | Channel ID for posting drafts |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `CLAUDE_MODEL` | (Optional) Model override, default: `claude-sonnet-4-20250514` |
