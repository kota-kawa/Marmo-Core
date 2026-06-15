---
name: sms
description: Send SMS in bulk from this Mac via iPhone+Mac SMS forwarding, and (optionally) scan replies in the local Messages database. Use when the user wants to send a personalized text message to one or more recipients ("send a text to ...", "remind everyone in this list", "text the team about ..."). Free, no external API.
model: sonnet
category: automation
version: 1.0.0
---

# sms Skill

Send SMS from a macOS Mac, routed through the user's iPhone over Continuity. Free (uses the user's existing mobile plan). Drives Messages.app via `osascript`. Reply scanning is via `~/Library/Messages/chat.db`.

## When to use

- User asks to text one or more people.
- User has a list of phone numbers and wants to send each a personalized message.
- User wants to check whether previously-texted people have replied.

## When NOT to use

- Sending to a single number where the user could just type it manually — only use the skill if there are multiple recipients, or the user wants the message logged, or wants a reply scan.
- Marketing / unsolicited outreach — flag the legal issue, don't proceed.
- When the user wants reliable delivery with anonymity — recommend Twilio instead.

## Prerequisites (check first)

1. Mac connected to iPhone via the same Apple ID.
2. iPhone setting: **Settings → Messages → Text Message Forwarding** → this Mac is enabled.
3. The repo or skill folder is somewhere accessible (default: `~/.claude/skills/sms/` or `~/claude-sms/`).

If the user hasn't done #2 yet, ask them to enable it before proceeding.

## Scripts

- `sms_send.py` — bulk sender. Reads CSV, calls `osascript`, logs to `~/sms_logs/sms_log.csv`.
- `sms_check.py` — reply scanner. Reads `chat.db`.

## CSV format

```csv
pid,phone,message
P001,+15551234567,"Hi Alice — meeting reminder for tomorrow 3pm."
```

Required columns: `pid`, `phone`. Optional: `message` (if missing, you can supply a template via `--template-file` with `{pid}` interpolation).

- `phone` must include country code: `+15551234567` (US) or `+821012345678` (KR).
- `pid` is any identifier the user chooses — appears in the log so they can match rows later.

## Standard workflow

### Step 1: Gather inputs

Get from the user:
- The list of recipients (names + phones).
- The message content. Either one template to interpolate per recipient, or a per-row message.
- Service preference (almost always `SMS`; `iMessage` only if the user explicitly wants to send via iMessage to iPhone recipients).

### Step 2: Build CSV

Write `/tmp/<purpose>_recipients.csv` with header `pid,phone,message`. Normalize phones to `+1XXXXXXXXXX` (or appropriate country code).

### Step 3: Dry-run

```bash
python3 sms_send.py /tmp/<purpose>_recipients.csv --service SMS --dry-run
```

### Step 4: Show drafts to user, get approval

Present the rendered drafts as a table or list. Show:
- Service (SMS / iMessage)
- Sender number (their iPhone number — exposed to recipients)
- Throttle (4s default)
- Total count

**Wait for explicit "send" / "go" / "보내" from user before invoking sms_send.py without `--dry-run`.** Never auto-send.

### Step 5: Send

```bash
echo "y" | python3 sms_send.py /tmp/<purpose>_recipients.csv --service SMS
```

### Step 6: Verify delivery

```bash
sqlite3 ~/Library/Messages/chat.db "
SELECT datetime(date/1000000000 + 978307200, 'unixepoch', 'localtime'),
       h.id, m.is_sent, m.is_delivered, m.service, m.error
FROM message m LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE m.is_from_me = 1
  AND m.date > (strftime('%s', 'now', '-3 minutes') - 978307200) * 1000000000
ORDER BY m.date DESC"
```

Field meanings:
- `is_sent=1` → message left the iPhone for the carrier (good).
- `is_sent=0` → silently blocked; usually iMessage cache (see caveats).
- `is_delivered=1` → confirmed (reliable for iMessage/RCS; SMS often delivers without receipt).
- `service` → `SMS` | `RCS` | `iMessage`.
- `error=0` → no error reported.

### Step 7: (Optional) Scan replies

After 24–72 hours:

```bash
python3 sms_check.py /tmp/<purpose>_recipients.csv --hours 48
```

The check script reports per-PID replies and auto-flags identical replies across multiple PIDs (a sign of templated / automated responses, which can be useful or suspicious depending on context).

## Caveats

### iMessage cache for iPhone recipients
For numbers registered with iMessage, `--service SMS` may silently fail because Apple's server caches iMessage registration even after the recipient turns iMessage off. The message appears in `chat.db` with `service=SMS, is_sent=0`. Fix: recipient deregisters at https://selfsolve.apple.com/deregister-imessage. Or just use `--service iMessage` if they're on iPhone.

### Sender number exposure
The recipient sees the user's personal iPhone number. If anonymity is needed, recommend a paid SMS API (Twilio, etc.).

### Carrier rate limits
Personal numbers sending many SMS rapidly can trip spam detection. Default 4-second throttle is fine for up to ~30 messages. For larger batches, bump throttle to 30–60 seconds.

### Unicode (Korean, emoji, etc.)
Plain ASCII SMS allows 160 chars per segment. Unicode SMS allows only 70 chars per segment. Multi-segment messages may arrive out of order on older phones. Warn the user if their message will be multi-segment.

### Legal / ethical
Phone outreach is regulated. Flag TCPA (US) or GDPR (EU) concerns if the user is sending to people they don't have a prior relationship with. Don't help with marketing, scams, or bulk unsolicited outreach.

## Output to user

After Step 6, report:

```
✅ Sent N/N messages.
   - SMS: X delivered (Y still pending receipt)
   - iMessage: Z delivered
   - Failed: 0
Log: ~/sms_logs/sms_log.csv
```

After Step 7 (if run), report per-PID reply status as a small table.

## Identity verification use case

A common use case: the user has a list of names + phones from a sign-up form and wants to confirm each phone actually belongs to the named person. Send:

> "Hi [NAME], this is [YOUR NAME]. You signed up for [WHATEVER]. Reply YES to confirm. Not [NAME]? Reply NO."

Then scan replies. `NO` replies indicate the phone doesn't belong to the named person. Identical text across multiple recipients indicates bot replies. Reply via iMessage when the user's sign-up data claimed Android indicates the original device claim was falsified (reply channel cannot be faked).

This is one specific application; the skill itself is general-purpose SMS automation.
