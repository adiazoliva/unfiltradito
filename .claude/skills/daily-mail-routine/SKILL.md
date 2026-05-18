---
name: daily-mail-routine
description: Set up a recurring scheduled task (daily/weekly/etc.) that uses Claude to do work and emails the result to the user, running on GitHub Actions and authenticated via the user's Claude MAX/Pro subscription so it costs nothing extra in API charges. Use when the user asks for a "boletín diario", "daily digest", "cron job that emails me", "scheduled prompt", "newsletter automation", "routine que corra todos los días", or similar recurring email-delivery tasks.
---

# Daily Mail Routine

Build a self-contained GitHub repository that runs Claude on a cron schedule and emails the result to the user. Authentication uses the user's Claude MAX/Pro subscription via OAuth token, so the workflow costs nothing extra beyond their existing Claude subscription.

## Architecture

```
GitHub Actions cron
    ↓
anthropics/claude-code-action@v1
  authenticated via CLAUDE_CODE_OAUTH_TOKEN (MAX subscription)
  reads scripts/prompt.md, allowed tools include WebSearch, WebFetch, Write, Read
    ↓
Claude writes ./email.json with {subject, html, text}
    ↓
python3 scripts/send_email.py ./email.json
  reads JSON, sends via Gmail SMTP (port 465 SSL)
    ↓
Email lands in user's inbox
```

## Conversation flow

When invoked, you are walking a (typically non-technical) user through a multi-step setup. Be patient, take it slow, confirm each step before the next.

### Step 1: Gather requirements

Ask the user, in one go (use AskUserQuestion or a single message with all 4 questions):

1. **Topic / what should the email contain?** (e.g., "specialty coffee news", "weather forecast for Buenos Aires", "summary of yesterday's tech news"). This becomes the heart of the prompt.
2. **Recipient email address** — usually their own.
3. **Schedule** — what time, in their local timezone, how often. (Default daily.)
4. **Voice/style** — short description of tone, audience, anything to avoid. (Optional; can skip and use a neutral editorial voice.)

Also confirm:
- They have a Claude **MAX or Pro** subscription (Free plan does not work — Claude Code requires Pro+).
- They have a Gmail account they want to send from.
- They have access to a desktop computer for the one-time OAuth token setup (cannot be done from mobile alone).
- They have a GitHub account and will create or use an existing repo for this.

### Step 2: Generate the project files

Create these four files in the repo's working directory. **Customize the prompt and cron based on the user's answers.**

#### `.github/workflows/daily-mail.yml`

```yaml
name: <name based on topic, e.g. "Boletín diario de café">

on:
  schedule:
    # <human-readable description>
    # <local time> = <UTC time>
    - cron: "<MM HH * * *>"  # in UTC
  workflow_dispatch: {}

jobs:
  newsletter:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Cargar prompt en variable de entorno
        run: |
          {
            echo 'NEWSLETTER_PROMPT<<MAILEOF'
            cat scripts/prompt.md
            echo 'MAILEOF'
          } >> "$GITHUB_ENV"

      - name: Generar contenido
        uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: ${{ env.NEWSLETTER_PROMPT }}
          claude_args: --model claude-opus-4-7 --allowedTools "WebSearch,WebFetch,Write,Read"

      - name: Enviar email
        run: python3 scripts/send_email.py ./email.json
        env:
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          RECIPIENT: <recipient email>
```

**Cron tip:** GitHub Actions schedules can be delayed 30-90 min. Schedule earlier than the user actually wants the email. If user says "I want it at 8 AM", schedule for 6:30 UTC equivalent or even 1-2 hours earlier in their local time, so even with delays it arrives before they need it.

**Top-of-hour pitfall:** Avoid scheduling at exact :00. Use a random minute like :03, :17, :43 to dodge the load spike at the top of every hour.

#### `scripts/prompt.md`

The full system prompt for Claude. Should include:

1. **Role and goal.** What Claude is doing, who reads the email, what the email should look like.
2. **Tone and style.** Quote real examples if the user provided them. If not, default to clear, neutral editorial voice.
3. **Search instructions** (if relevant). What to search for, source priorities, date ranges. Tell Claude to use WebSearch.
4. **Selection criteria.** What makes a good entry, what to skip.
5. **Output structure.** Tell Claude to write the result to `./email.json` (in the repo working directory, NOT `/tmp/`) with exactly three fields: `subject` (string), `html` (string), `text` (string).
6. **Email body structure** in HTML, and the matching Markdown version for the plain-text alternative.
7. **No-data fallback.** Tell Claude what to do if its searches return nothing useful — still write the JSON, but with a short "no news today" message.
8. **End condition.** "Once `./email.json` is written correctly, you are done — do NOT send the email yourself."

#### `scripts/send_email.py`

Use Python stdlib only (no `pip install` needed on the runner). Reads JSON from argv[1], sends via `smtplib.SMTP_SSL("smtp.gmail.com", 465)` with multipart text/html. Validates that subject, html, text are all non-empty before sending. Recipient is read from `RECIPIENT` env var with a default fallback.

```python
"""Send an email via Gmail SMTP from a JSON payload."""
import json, os, smtplib, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def main(payload_path: str) -> int:
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)

    for field in ("subject", "html", "text"):
        if not payload.get(field):
            raise ValueError(f"Payload is missing or empty field: {field}")

    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = payload["subject"]
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(payload["text"], "plain", "utf-8"))
    msg.attach(MIMEText(payload["html"], "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

    print(f"Sent: {payload['subject']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: send_email.py <payload.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
```

#### `README.md`

User-facing instructions for the one-time setup (next step).

### Step 3: Walk the user through the one-time setup

This is where users get stuck. Do this **slowly, one step at a time**, waiting for confirmation before moving on.

#### 3a. Generate the Claude OAuth token (requires desktop)

Walk them through this **slowly**, asking what OS first.

1. Open a terminal (PowerShell on Windows, Terminal on Mac, etc.).
2. Install Claude Code if not already:
   - Mac/Linux/WSL: `curl -fsSL https://claude.ai/install.sh | bash`
   - Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`
3. **Common pitfall on Windows:** after install, `claude` may not be in PATH. If they see "claude: command not recognized", have them run `$env:PATH += ";$env:USERPROFILE\.local\bin"` in PowerShell (this is a temporary fix for the current session).
4. Generate the token: `claude setup-token` (opens browser, they log in with their MAX account, authorize, token appears in terminal).
5. **Common pitfall on Windows:** when copying the token from PowerShell, line wrapping can introduce hidden newlines that break HTTP headers later. Two ways to avoid:
   - Maximize the PowerShell window before running `claude setup-token` so the token fits on one line.
   - Or pipe to a file: `claude setup-token > $env:USERPROFILE\Desktop\token.txt`, then `notepad $env:USERPROFILE\Desktop\token.txt`, then copy from Notepad.
6. **Security:** the token they paste must NEVER appear in any file, commit, chat message, or screenshot. If a user pastes it visibly, immediately tell them to regenerate (running `claude setup-token` again invalidates the old token).
7. The token must start with `sk-ant-oat01-`. If it starts with `sk-ant-api-`, that's an API key (pay-per-use), not the OAuth token — they ran the wrong command or generated the wrong type.

#### 3b. Generate Gmail app password

1. Direct them to https://myaccount.google.com/security and confirm 2-step verification is on (required).
2. Then https://myaccount.google.com/apppasswords — create a new app password with any descriptive name. Gmail returns a 16-character password with spaces every 4 chars (spaces are optional, don't matter).
3. They store this password somewhere safe; it's only shown once.

#### 3c. Set up GitHub repo and secrets

1. If user doesn't have a repo yet, walk them through creating one on github.com (private is fine).
2. They commit and push the four files generated in Step 2.
3. Repo Settings → Secrets and variables → Actions → New repository secret. Three secrets:
   - `CLAUDE_CODE_OAUTH_TOKEN`: the `sk-ant-oat01-...` token
   - `GMAIL_USER`: their full Gmail address
   - `GMAIL_APP_PASSWORD`: the 16-character app password (with or without spaces)

#### 3d. Test manually

Actions tab → click the workflow name → "Run workflow" button → run from the default branch. It should take ~4-5 min. If green, check inbox AND spam folder. First-time SMTP from a new sender often lands in spam — have them mark "Not spam" once and Gmail learns.

### Common failure modes and fixes

| Error in workflow log | Fix |
|---|---|
| `Could not fetch an OIDC token` | Missing `id-token: write` in workflow permissions. Add it. |
| `API Error: 401 Invalid bearer token` | Token is wrong format, expired, or got truncated when pasted. Verify it starts with `sk-ant-oat01-` and re-paste carefully. |
| `API Error: Header '14' has invalid value: '***'` | Token has hidden newline or control char from how it was copied. Re-copy the token using the Notepad-from-file trick (3a step 5). |
| `claude: command not recognized` (Windows) | PATH not updated. Run `$env:PATH += ";$env:USERPROFILE\.local\bin"`. |
| Workflow doesn't fire at scheduled time | GH Actions delay (30-90 min normal). Schedule earlier. First scheduled run after creating a new repo may take up to a day to start firing reliably. |
| Email never arrives but workflow is green | Check spam folder. Sender = recipient often triggers spam filters. Have user mark "Not spam" once. |
| Email arrives but is missing some notes | Claude hit token/time limits. Increase `timeout-minutes` in the workflow. |

### What NOT to do

- **Do not** put the `anthropic` Python SDK in `requirements.txt` and call the API directly — that would bill against the user's API account, not their MAX. The whole point of this routine is to ride on their existing subscription via `claude-code-action` + OAuth token.
- **Do not** check secrets into the repo. They go in GitHub Settings → Secrets.
- **Do not** suggest scheduling the workflow at the top of the hour (`0 X * * *`) — use an off-cycle minute like `:03`, `:17`, `:43` to avoid GH Actions load spikes.
- **Do not** use `/tmp/email.json` as the JSON path — it works for one job-run but is unreliable across runners. Use `./email.json` (repo working dir).
- **Do not** use `anthropic_api_key` input on the action when the user wants subscription auth — use `claude_code_oauth_token` instead.

### When NOT to use this skill

- The user wants instant interactive results (not a scheduled job) — they just want to chat with Claude.
- The user is on Free plan — Claude Code requires Pro/MAX. Suggest they upgrade or use the paid API path (and warn them about the per-call cost).
- The user wants delivery to anything other than email — Slack, Discord, SMS, etc. would require swapping out the send step. This skill is email-specific; for other deliveries, build the send step separately.
- The user needs delivery within a tight time window — GH Actions schedules have 30-90 min delays. For minute-accurate timing, they need a different scheduler.
