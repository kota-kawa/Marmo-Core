---
name: vikunja-heartbeat
description: Periodic routine to ensure Vikunja is used as the source of truth for all tasks
---

# Vikunja Heartbeat 💓

> This runs periodically to ensure tasks are never forgotten and Vikunja remains the source of truth.

## Why Heartbeat?

**Without a heartbeat, tasks get lost.** Users say "remind me to..." and you forget. They ask "what's pending?" and you have no answer.

The heartbeat solves this:
- ✅ **Every task request → Vikunja** (always registered)
- ✅ **Regular checks** for overdue and due tasks
- ✅ **Proactive reminders** before deadlines
- ✅ **Single source of truth** (no mental notes, no temporary lists)

**Think of it like:** A task manager that actually works because you check it regularly. 📋

---

## Recommended Schedule

| Frequency | Action |
|-----------|--------|
| Every 4+ hours | Run full heartbeat routine |
| On user request | Check specific project/task |
| Daily (morning) | Review overdue + due today |
| Weekly | Full review by priority |

---

## Step 1: Check for Skill Updates

Re-fetch skill files periodically to get updates:

```bash
# Create directories if needed
mkdir -p ~/.nimworker/skills
mkdir -p ~/.nimworker/scripts

# Download skills
curl -s https://hiveagilectl.sh/skill.md > ~/.nimworker/skills/SKILL.md
curl -s https://hiveagilectl.sh/register.md > ~/.nimworker/skills/REGISTER.md
curl -s https://hiveagilectl.sh/heartbeat.md > ~/.nimworker/skills/HEARTBEAT.md

# Download scripts
curl -s https://hiveagilectl.sh/scripts/vikunja.sh > ~/.nimworker/scripts/vikunja.sh
curl -s https://hiveagilectl.sh/vikunja.py > ~/.nimworker/vikunja.py

# Make executable
chmod +x ~/.nimworker/scripts/vikunja.sh
chmod +x ~/.nimworker/vikunja.py
```

Or if using local repo:
```bash
mkdir -p ~/.nimworker/skills ~/.nimworker/scripts
cp ~/work/taskworker/skill/SKILL.md ~/.nimworker/skills/
cp ~/work/taskworker/REGISTER.md ~/.nimworker/skills/
cp ~/work/taskworker/HEARTBEAT.md ~/.nimworker/skills/
cp ~/work/taskworker/skill/scripts/vikunja.sh ~/.nimworker/scripts/
cp ~/work/taskworker/vikunja.py ~/.nimworker/
chmod +x ~/.nimworker/scripts/vikunja.sh ~/.nimworker/vikunja.py
```

---

## Step 2: Check Overdue Tasks (CRITICAL)

**Always check overdue first** - these need immediate attention:

```bash
# Check WORK overdue
~/.nimworker/vikunja.py overdue --project "WORK"

# Check PERSONAL overdue
~/.nimworker/vikunja.py overdue --project "PERSONAL"
```

**If overdue tasks exist:**
- 🚨 **Alert the user immediately**
- Show task details (title, due date, priority)
- Ask if they want to complete or reschedule

---

## Step 3: Check Due Soon (Next 24h)

Check what's coming up:

```bash
# WORK tasks due in next 24h
~/.nimworker/vikunja.py due --hours 24 --project "WORK"

# PERSONAL tasks due in next 24h
~/.nimworker/vikunja.py due --hours 24 --project "PERSONAL"
```

**If tasks are due soon:**
- 📅 **Proactively remind the user**
- Suggest prioritization if multiple tasks
- Offer to reschedule if needed

---

## Step 4: Review Active Tasks

Check what's on the plate:

```bash
# High priority WORK tasks
~/.nimworker/vikunja.py tasks --project "WORK" --filter 'priority >= 4' --count 20

# All PERSONAL tasks
~/.nimworker/vikunja.py tasks --project "PERSONAL" --count 20
```

---

## Step 5: Process User Requests

**CRITICAL RULE:** When user mentions a task, **always register it in Vikunja**.

### Task Creation Signals

User says any of these → **Create task immediately**:
- "Recuérdame..."
- "Tengo que..."
- "No olvides..."
- "Añade a mi lista..."
- "Tarea: ..."
- "Pendiente: ..."

### Auto-routing to WORK/PERSONAL

**WORK signals:** cliente, reunión, entrega, deploy, factura, empresa, proyecto, ticket, incidencia, call, oferta, presupuesto

**PERSONAL signals:** casa, compra, familia, salud, viaje, médico, gym, pago personal

**Default:** PERSONAL (if unclear)

### Example Flow

User: "Tengo que llamar al cliente mañana"

```bash
# Auto-detect: "cliente" → WORK
~/.nimworker/vikunja.py create-task \
  --project "WORK" \
  --title "Llamar al cliente" \
  --due "2026-02-01" \
  --priority 4
```

Response: "✅ Tarea registrada en WORK: 'Llamar al cliente' (vence 2026-02-01, prioridad 4)"

---

## Step 6: Autonomous Bot Execution (AI Agent Mode) 🤖

**NEW: Bot can execute tasks autonomously with human-in-the-loop approval**

### How It Works

1. **Check assigned tasks in "To Do" stage**
2. **Analyze task** to determine if autonomous execution is possible
3. **Execute or request approval** based on task type
4. **Move through stages:** To Do → In Progress → Review → Done
5. **Explain actions** and reasoning at each step

### Checking Bot's Tasks

**IMPORTANTE:** Primero configura el username del bot:
```bash
export VIKUNJA_BOT_USERNAME="Jarvis"  # Cambia por tu username en Vikunja
```

Luego verifica tareas asignadas:
```bash
# Check tasks assigned to bot in "To Do" stage
~/.nimworker/vikunja.py tasks --project "WORK" --assign "$VIKUNJA_BOT_USERNAME"

# O directamente con el nombre
~/.nimworker/vikunja.py tasks --project "WORK" --assign "Jarvis"
```

### Task Analysis Rules

**Can execute autonomously:**
- ✅ Research/investigation tasks
- ✅ Analysis and reporting
- ✅ Documentation updates
- ✅ Code review
- ✅ Information gathering
- ✅ Testing and verification

**Requires human approval:**
- ⚠️ Delete/remove operations
- ⚠️ Production deployments
- ⚠️ Payment/financial actions
- ⚠️ Email sending
- ⚠️ External communications
- ⚠️ Critical system changes

### Execution Workflow

**Step 1: Move to "In Progress"**
```bash
~/.nimworker/vikunja.py move-task --id 123 --stage "In Progress"
~/.nimworker/vikunja.py add-comment --id 123 --comment "🤖 BOT started execution at $(date '+%Y-%m-%d %H:%M')"
```

**Step 2: Execute the task**
- Read task description carefully
- Understand requirements
- Perform necessary actions
- Document findings/results

**Step 3: Move to "Review" and request approval**
```bash
~/.nimworker/vikunja.py move-task --id 123 --stage "Review"
~/.nimworker/vikunja.py add-comment --id 123 --comment "🤖 BOT execution completed:

TASK: [Task title]

ACTIONS TAKEN:
1. [Action 1]
2. [Action 2]
3. [Action 3]

RESULTS:
- [Result 1]
- [Result 2]

REASONING:
[Explain why these actions were taken]

⏸️ Waiting for human review and approval to mark as Done"
```

**Step 4: Human reviews and approves**
- User reviews the comment with actions and results
- If approved: User moves to "Done" or bot moves after confirmation
- If changes needed: User adds comment and bot adjusts

### Example: Autonomous Research Task

**Task in Vikunja:**
```
Title: "Research best practices for API rate limiting"
Assigned: Jarvis
Stage: To Do
Priority: 3
```

**Bot execution:**
```bash
# 1. Move to In Progress
~/.nimworker/vikunja.py move-task --id 125 --stage "In Progress"

# 2. Bot performs research (using AI capabilities)
# - Searches documentation
# - Analyzes patterns
# - Compiles findings

# 3. Move to Review with detailed report
~/.nimworker/vikunja.py move-task --id 125 --stage "Review"
~/.nimworker/vikunja.py add-comment --id 125 --comment "🤖 Research completed:

FINDINGS:
1. Token bucket algorithm - most common approach
2. Sliding window log - more accurate but memory intensive
3. Fixed window - simplest but has burst issues

RECOMMENDATIONS:
- Use token bucket for API endpoints
- Implement per-user and per-IP limits
- Add rate limit headers (X-RateLimit-*)

REFERENCES:
- Stripe API documentation
- GitHub API rate limiting
- RFC 6585 (HTTP 429 status)

⏸️ Ready for review"
```

### Example: Task Requiring Approval

**Task in Vikunja:**
```
Title: "Delete old user accounts from database"
Assigned: Jarvis
Stage: To Do
Priority: 4
```

**Bot response:**
```bash
# Bot analyzes and determines it needs approval
~/.nimworker/vikunja.py add-comment --id 126 --comment "🤖 BOT analysis:

TASK TYPE: Data deletion (destructive operation)
RISK LEVEL: HIGH

PROPOSED ACTIONS:
1. Query users inactive > 2 years
2. Export data to backup
3. Delete from database
4. Verify deletion

⚠️ This task requires HUMAN APPROVAL before execution.

Please review and confirm:
- [ ] Backup strategy is acceptable
- [ ] Deletion criteria is correct
- [ ] Legal/compliance requirements met

Reply with approval to proceed or adjust requirements."
```

### Bot Heartbeat Routine

Add this to periodic checks:

```bash
# Configure bot username (set this in your environment)
BOT_USERNAME="${VIKUNJA_BOT_USERNAME:-Jarvis}"

# Check bot's assigned tasks in "To Do"
BOT_TASKS=$(~/.nimworker/vikunja.py tasks --project "WORK" --assign "$BOT_USERNAME" | grep "Stage: 📝 To Do")

if [ -n "$BOT_TASKS" ]; then
  echo "🤖 Bot has tasks in To Do stage - analyzing for autonomous execution"
  # Bot (AI agent) will analyze and execute or request approval
fi

# Check bot's tasks in "Review" waiting for approval
REVIEW_TASKS=$(~/.nimworker/vikunja.py tasks --project "WORK" --assign "$BOT_USERNAME" | grep "Stage: 👀 Review")

if [ -n "$REVIEW_TASKS" ]; then
  echo "⏸️ Bot has tasks in Review stage - waiting for human approval"
  # Alert user to review completed work
fi
```

### Communication Pattern

**When bot starts a task:**
```
🤖 Starting task: "Research API rate limiting"
Moving to In Progress...
Estimated time: 10-15 minutes
```

**When bot completes and needs review:**
```
✅ Task completed: "Research API rate limiting"
Moved to Review stage.
Please check the detailed report in task comments.
React with ✅ to approve or 💬 to discuss changes.
```

**When bot needs approval before starting:**
```
⚠️ Task requires approval: "Delete old user accounts"
This is a destructive operation.
Please review proposed actions in task comments.
React with ✅ to approve execution or ❌ to cancel.
```

---

## Step 7: Handle Task Completion

User says "hecho", "completado", "listo", "terminado" → **Complete the task**

```bash
# Get task ID first (from context or ask)
~/.nimworker/vikunja.py complete --id 123
```

Response: "✅ Tarea completada: [task title]"

---

## Response Templates

### Routine Check (nothing notable)

```
📋 Vikunja check:
- WORK: 3 tareas activas, 0 vencidas
- PERSONAL: 5 tareas activas, 0 vencidas
- Próximas 24h: 1 tarea (WORK)

Todo bajo control. 👍
```

### Overdue Alert

```
🚨 ATENCIÓN: Tareas vencidas

WORK:
- [ID 45] Llamar a cliente X (vencida hace 2 días) - Prioridad 5
- [ID 52] Enviar propuesta (vencida ayer) - Prioridad 4

¿Quieres completarlas o reprogramarlas?
```

### Due Soon Reminder

```
📅 Próximas 24 horas:

WORK:
- [ID 67] Reunión con equipo (mañana 10:00) - Prioridad 4

PERSONAL:
- [ID 89] Comprar regalo cumpleaños (mañana) - Prioridad 3

¿Necesitas preparar algo?
```

### Task Created

```
✅ Tarea registrada en WORK:
- Título: "Revisar código PR #123"
- Vence: 2026-02-03
- Prioridad: 4 (alta)
- ID: 156
```

---

## When to Escalate to Human

Alert the user when:
- ❗ **Multiple overdue tasks** (3+)
- ❗ **High priority overdue** (priority 5)
- ❗ **Conflicting deadlines** (multiple tasks same day)
- ❗ **API errors** (Vikunja unreachable)

---

## Track Your State

Keep track of last check:

```json
{
  "lastVikunjaCheck": "2026-01-31T10:30:00Z",
  "lastOverdueAlert": "2026-01-31T09:00:00Z",
  "pendingTasks": {
    "WORK": 5,
    "PERSONAL": 8
  }
}
```

Update after each heartbeat.

---

## Enforcement Rules (MANDATORY)

1. **Source of truth:** If user requests a task → **create in Vikunja** (no exceptions)
2. **No mental notes:** Never say "I'll remember" → **create task instead**
3. **Check regularly:** Run heartbeat every 4+ hours
4. **Proactive alerts:** Don't wait for user to ask about overdue tasks
5. **Complete properly:** When user says "done" → **mark complete in Vikunja**

---

## Quick Heartbeat Checklist

```markdown
[ ] Check overdue (WORK + PERSONAL)
[ ] Check due next 24h (WORK + PERSONAL)
[ ] Review high priority tasks
[ ] Process any new task requests
[ ] Complete any finished tasks
[ ] Update lastVikunjaCheck timestamp
[ ] Alert user if issues found
```

---

## Daily Routine (Copy-Paste)

Run this every morning:

```bash
echo "=== VIKUNJA DAILY CHECK ==="
echo ""
echo "OVERDUE TASKS:"
~/.nimworker/vikunja.py overdue --project "WORK"
~/.nimworker/vikunja.py overdue --project "PERSONAL"
echo ""
echo "DUE TODAY (24h):"
~/.nimworker/vikunja.py due --hours 24 --project "WORK"
~/.nimworker/vikunja.py due --hours 24 --project "PERSONAL"
echo ""
echo "HIGH PRIORITY:"
~/.nimworker/vikunja.py tasks --project "WORK" --filter 'priority >= 4' --count 10
```

---

## Weekly Review (Copy-Paste)

Run this weekly for cleanup:

```bash
echo "=== VIKUNJA WEEKLY REVIEW ==="
echo ""
echo "WORK TASKS (by priority):"
~/.nimworker/vikunja.py tasks --project "WORK" --sort priority --order desc --count 50
echo ""
echo "PERSONAL TASKS (by priority):"
~/.nimworker/vikunja.py tasks --project "PERSONAL" --sort priority --order desc --count 50
```

---

*Stay organized, stay on top. Tasks don't manage themselves! 📋*
