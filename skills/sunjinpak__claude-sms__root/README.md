# claude-sms

**Send SMS from your Mac, driven by Claude Code, for $0.**

This is a small toolkit + [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that lets you:

1. **Send personalized SMS in bulk** from your Mac, without any third-party SMS API (Twilio, etc.).
2. **Scan replies automatically** by reading your Mac's local Messages database.
3. **Drive the whole thing from a natural-language prompt** in Claude Code.

It works because macOS's Messages.app can forward outgoing SMS through your iPhone over Continuity. Your Mac runs a tiny AppleScript, your iPhone sends the actual SMS over its modem, and your mobile plan eats the cost (which is $0 for any modern unlimited-text US plan).

---

## Why this exists

If you want to send SMS programmatically, the usual answer is: sign up for Twilio, get an API key, pay per message. That's fine for production apps. But for personal automation — sending yourself reminders, sending personalized messages to a list of people you already know, checking in with a small group — it's overkill.

You already have:
- An iPhone with a mobile plan.
- A Mac with Messages.app.
- The Continuity feature that already lets you send SMS from your Mac manually.

This toolkit just **scripts what Messages.app can already do**, and packages it as a Claude Code skill so you can say:

> "Send a reminder text to everyone in `/tmp/reminders.csv`"

…and Claude handles the rest.

---

## What you get

| File | Purpose |
| ---- | ------- |
| `sms_send.py` | Bulk SMS sender. Reads a CSV, calls `osascript` to drive Messages.app. |
| `sms_check.py` | Reply scanner. Reads `~/Library/Messages/chat.db` to find inbound messages. |
| `skill.md` | Claude Code skill definition — drop the folder under `~/.claude/skills/` and Claude can invoke this workflow on your behalf. |
| `example_recipients.csv` | Example input format. |

---

## Prerequisites

- A Mac and an iPhone with the same Apple ID.
- iPhone **Settings → Messages → Text Message Forwarding** → enable for this Mac.
- Python 3.8+ on the Mac.
- A mobile plan that includes SMS.

Verify the Continuity SMS setup is working by sending a regular SMS manually from Messages.app on the Mac to a non-iMessage contact. If that delivers, this toolkit will work.

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/sunjinpak/claude-sms.git ~/claude-sms
cd ~/claude-sms
```

### 2. Build a CSV

```csv
pid,phone,message
P001,+15551234567,"Hi Alice — reminder that our meeting is tomorrow at 3pm."
P002,+15559876543,"Hi Bob — your library book is due Friday."
```

The `pid` column is just an identifier you choose; it appears in the log so you can match sent rows to outcomes later.

### 3. Dry-run

```bash
python3 sms_send.py example_recipients.csv --service SMS --dry-run
```

This prints what would be sent without sending anything.

### 4. Send

```bash
python3 sms_send.py example_recipients.csv --service SMS
```

You'll be prompted for `y/N` before any messages go out.

### 5. (Optional) Scan replies later

```bash
python3 sms_check.py example_recipients.csv --hours 48
```

This queries your local Messages database for inbound messages from the same numbers within the last N hours. Useful for things like "did the recipient confirm?" or "who hasn't replied yet?"

---

## How it works (technical)

### Sending

```applescript
tell application "Messages"
    set targetService to 1st service whose service type = SMS
    set targetBuddy to participant "+15551234567" of targetService
    send "your message here" to targetBuddy
end tell
```

`sms_send.py` builds this AppleScript per row and shells out to `osascript`. Messages.app hands the request to your connected iPhone over Continuity, and the iPhone's modem sends the SMS through your carrier.

### Reading replies

`~/Library/Messages/chat.db` is the SQLite database that Messages.app uses. The script queries:

```sql
SELECT m.text, m.date, m.is_from_me, m.service
FROM message m
JOIN handle h ON m.handle_id = h.ROWID
WHERE h.id LIKE '%XXXXXXXXXX'
  AND m.date > ?
ORDER BY m.date DESC;
```

(Apple stores dates as nanoseconds since 2001-01-01, so the script offsets accordingly.)

Recent macOS versions stash the actual message text in `attributedBody` (a binary blob) rather than the `text` column. `sms_check.py` extracts both.

### Service selection

`--service SMS` requests the SMS service. `--service iMessage` requests iMessage. For recipients on iPhones, Messages.app may force-route to iMessage even when SMS is requested (this is by design — Apple's "smart routing"). For Android recipients, you'll always get SMS.

---

## Using it as a Claude Code skill

If you use Claude Code, you can drop this directory under your skills folder:

```bash
cp -r ~/claude-sms ~/.claude/skills/sms
```

Then in Claude Code:

> "Send everyone in `/tmp/team-reminder.csv` a text reminding them about Friday's meeting"

Claude reads `skill.md`, builds the CSV from your input data if needed, shows you the drafts, waits for your approval, sends, and reports the results. It can also schedule a follow-up reply scan via `sms_check.py`.

The skill definition (`skill.md`) tells Claude:
- The CSV schema it should generate.
- The standard workflow (dry-run → approval → send → optional reply scan).
- The caveats below (iMessage cache, sender number exposure).
- What to do with each kind of reply.

---

## Caveats

### iMessage cache
For phone numbers registered with iMessage, `--service SMS` may silently fail (the message inserts into `chat.db` but `is_sent` stays 0). This is because Apple's server caches iMessage registration even after the recipient turns iMessage off. The recipient has to deregister at https://selfsolve.apple.com/deregister-imessage. For Android-only targets this is not an issue.

### Sender number exposure
Outbound SMS exposes your iPhone's number to recipients. If anonymity matters, use a paid service like Twilio instead. This toolkit is intentionally simple and free at the cost of revealing your number.

### Carrier rate limits
Sending too many SMS too fast from a personal number may trip your carrier's spam detector. The default 4-second throttle between sends is conservative; bump it up (`--throttle 60`) if you're sending dozens of messages.

### Legal / ethical
Phone outreach is regulated (TCPA in the US, GDPR in the EU, etc.). **Use this only for outreach where you have a legitimate prior relationship with the recipient.** Don't use it for marketing, scams, or unsolicited messages.

---

## Privacy

This toolkit is **fully local**. Nothing is sent to any external service:

- All recipient data lives in your CSV input.
- Sent messages are logged to `~/sms_logs/sms_log.csv` by default (configurable via `--log-dir`).
- Reply detection reads your own Mac's `chat.db`.
- No phone-home, no analytics, no telemetry.

---

## License

MIT — see [LICENSE](LICENSE).

## Contributing

PRs welcome. Particularly interested in:
- iMessage cache workarounds beyond Apple's deregistration page.
- Better message rendering (Unicode handling, segment counting).
- Linux / Windows alternatives.
