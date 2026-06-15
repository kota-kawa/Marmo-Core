---
name: vikunja-register
description: Initial setup and configuration for Vikunja task management system
---

# Register Your Vikunja System

> Get your Vikunja task management system configured in minutes.

## Step 1: Configure Credentials

Edit `~/work/taskworker/credentials.json` with your Vikunja connection details:

```json
{
  "vikunja_url": "https://your-vikunja-instance.com",
  "vikunja_token": "your-api-token-here",
  "timezone": "Europe/Rome",
  "projects": {
    "personal": "PERSONAL",
    "work": "WORK"
  }
}
```

**⚠️ Keep this file secure!** It contains your API token.

The `vikunja.py` script automatically loads these credentials.

---

## Step 2: Get Your API Token

1. Log in to your Vikunja instance
2. Go to **Settings** → **API Tokens**
3. Click **Create token**
4. Copy the token and paste it in `credentials.json` as `vikunja_token`

---

## Step 3: Bootstrap Default Projects

Create the PERSONAL and WORK projects:

```bash
~/work/taskworker/skill/scripts/vikunja.sh ensure-default-projects
```

This will create both projects if they don't exist.

**Note:** When creating projects, the system automatically creates 5 Kanban stages with icons:
- 📋 **Backlog** - Ideas and future tasks
- 📝 **To Do** - Ready to start
- 🔄 **In Progress** - Currently working on
- 👀 **Review** - Waiting for review/approval
- ✅ **Done** - Completed tasks

---

## Step 4: Verify Setup

Check that everything works:

```bash
# List projects (should show PERSONAL and WORK)
~/work/taskworker/vikunja.py projects

# List tasks (should work without errors)
~/work/taskworker/vikunja.py tasks --project "WORK" --count 5
```

---

## Step 5: Set Up Your Heartbeat 💓

**This is critical!** Without the heartbeat, tasks won't be tracked consistently.

The heartbeat ensures:
- ✅ Tasks are always registered in Vikunja (source of truth)
- ✅ Overdue and due tasks are checked regularly
- ✅ No tasks are forgotten or lost

See `HEARTBEAT.md` for the full routine.

---

## Step 6: Test Task Creation

Create your first task:

```bash
~/work/taskworker/vikunja.py create-task \
  --project "PERSONAL" \
  --title "Test task - delete me" \
  --due "2026-02-01" \
  --priority 2
```

Then list it:

```bash
~/work/taskworker/vikunja.py tasks --project "PERSONAL"
```

Complete it:

```bash
~/work/taskworker/vikunja.py complete --id <task_id>
```

---

## Troubleshooting

### "Connection refused" or "Could not resolve host"

Check your `vikunja_url` in `credentials.json`:
```bash
cat ~/work/taskworker/credentials.json | jq -r '.vikunja_url'
curl -I $(cat ~/work/taskworker/credentials.json | jq -r '.vikunja_url')
```

### "Unauthorized" or "Invalid token"

Verify your token in `credentials.json`:
```bash
cat ~/work/taskworker/credentials.json | jq -r '.vikunja_token'
```

Re-generate the token in Vikunja Settings if needed and update `credentials.json`.

### "Project not found"

Run the bootstrap command:
```bash
~/work/taskworker/skill/scripts/vikunja.sh ensure-default-projects
```

---

## Quick Reference

```bash
# Check credentials
cat ~/work/taskworker/credentials.json | jq

# Bootstrap projects
~/work/taskworker/skill/scripts/vikunja.sh ensure-default-projects

# List projects
~/work/taskworker/vikunja.py projects

# Create task
~/work/taskworker/vikunja.py create-task --project "WORK" --title "Task title" --due "2026-02-01" --priority 3

# List tasks
~/work/taskworker/vikunja.py tasks --project "WORK"

# Check overdue
~/work/taskworker/vikunja.py overdue --project "WORK"

# Check due soon
~/work/taskworker/vikunja.py due --hours 24 --project "WORK"
```

---

**Next:** Set up your heartbeat routine in `HEARTBEAT.md` to ensure consistent task tracking!
