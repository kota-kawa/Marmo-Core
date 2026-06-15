#!/bin/bash
# Vikunja CLI - Manage tasks and projects
# Uses Vikunja REST API v1
#
# Requires environment variables:
#   VIKUNJA_URL - Your Vikunja instance URL (e.g., https://todo.example.com)
#   VIKUNJA_TOKEN - Your Vikunja API token
#
# Usage:
#   vikunja.sh tasks [--project NAME] [--search TEXT] [--filter EXPR] [--count N] [--sort FIELD] [--order asc|desc]
#   vikunja.sh overdue
#   vikunja.sh due [--hours N]
#   vikunja.sh create-task --project NAME --title TEXT [--description TEXT] [--due DATE] [--priority 1-5] [--bucket STAGE]
#   vikunja.sh edit-task --id ID [--title TEXT] [--description TEXT] [--due DATE] [--priority 1-5]
#   vikunja.sh delete-task --id ID
#   vikunja.sh complete --id ID
#   vikunja.sh move-task --id ID --bucket STAGE [--project NAME]
#   vikunja.sh search --query TEXT
#   vikunja.sh assign-task --id ID --user USERNAME
#   vikunja.sh labels
#   vikunja.sh add-label --id ID --label TEXT
#   vikunja.sh remove-label --id ID --label TEXT
#   vikunja.sh comments --id ID
#   vikunja.sh add-comment --id ID --comment TEXT
#   vikunja.sh users --project NAME
#   vikunja.sh project-teams --project NAME
#   vikunja.sh invite-user --project NAME --user USERNAME|EMAIL [--rights read|write|admin]
#   vikunja.sh teams
#   vikunja.sh create-team --name NAME [--description TEXT]
#   vikunja.sh share-project --project NAME --team TEAMNAME [--rights read|write|admin]
#   vikunja.sh projects
#   vikunja.sh create-project --title TEXT [--description TEXT] [--parent ID] [--no-stages]
#   vikunja.sh buckets --project NAME
#   vikunja.sh create-bucket --project NAME --title TEXT [--position N]
#   vikunja.sh notifications
#   vikunja.sh task --id ID

set -e

# --- Config ---
if [ -z "$VIKUNJA_URL" ] || [ -z "$VIKUNJA_TOKEN" ]; then
  echo "Error: VIKUNJA_URL and VIKUNJA_TOKEN must be set" >&2
  exit 1
fi

API="${VIKUNJA_URL}/api/v1"
AUTH="Authorization: Bearer ${VIKUNJA_TOKEN}"

# --- Helpers ---
api_get() {
  curl -s -H "$AUTH" "${API}/$1"
}

api_put() {
  curl -s -X PUT -H "$AUTH" -H "Content-Type: application/json" "${API}/$1" -d "$2"
}

api_post() {
  curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" "${API}/$1" -d "$2"
}

api_delete() {
  curl -s -X DELETE -H "$AUTH" "${API}/$1"
}

get_project_id() {
  local NAME="$1"
  api_get "projects" | jq -r --arg name "$NAME" '.[] | select(.title | ascii_downcase == ($name | ascii_downcase)) | .id' | head -1
}

format_tasks() {
  # Read tasks from stdin
  local TASKS
  TASKS=$(cat)
  
  # Get unique project IDs and fetch all buckets
  local PROJECT_IDS
  PROJECT_IDS=$(echo "$TASKS" | jq -r '[.[].project_id] | unique | .[]' 2>/dev/null)
  
  local ALL_BUCKETS="[]"
  local HAS_NULL_PROJECT=false
  
  for PID in $PROJECT_IDS; do
    if [ -n "$PID" ] && [ "$PID" != "null" ]; then
      local BUCKETS
      BUCKETS=$(api_get "projects/${PID}/buckets" 2>/dev/null || echo "[]")
      ALL_BUCKETS=$(echo "$ALL_BUCKETS" "$BUCKETS" | jq -s 'add // []')
    else
      HAS_NULL_PROJECT=true
    fi
  done
  
  # If any tasks have null project_id, fetch buckets from all projects
  if [ "$HAS_NULL_PROJECT" = true ]; then
    local ALL_PROJECTS
    ALL_PROJECTS=$(api_get "projects" | jq -r '.[].id')
    for PID in $ALL_PROJECTS; do
      local BUCKETS
      BUCKETS=$(api_get "projects/${PID}/buckets" 2>/dev/null || echo "[]")
      ALL_BUCKETS=$(echo "$ALL_BUCKETS" "$BUCKETS" | jq -s 'add // []')
    done
  fi
  
  # Get all unique project IDs and fetch their names
  local PROJECT_NAMES="{}"
  
  # If we have null projects, we need to map bucket_id to project
  if [ "$HAS_NULL_PROJECT" = true ]; then
    # Create a mapping of bucket_id to project info
    local ALL_PROJECTS_INFO
    ALL_PROJECTS_INFO=$(api_get "projects")
    
    # For each project, get its buckets and create bucket_id -> project mapping
    echo "$ALL_PROJECTS_INFO" | jq -r '.[] | .id' | while read -r PID; do
      local PNAME
      PNAME=$(echo "$ALL_PROJECTS_INFO" | jq -r --arg pid "$PID" '.[] | select(.id == ($pid | tonumber)) | .title')
      PROJECT_NAMES=$(echo "$PROJECT_NAMES" | jq --arg pid "$PID" --arg pname "$PNAME" '. + {($pid): $pname}')
    done
  else
    # Normal case: just fetch project names for known project_ids
    local PIDS
    PIDS=$(echo "$TASKS" | jq -r '[.[].project_id] | unique | .[]' 2>/dev/null)
    for PID in $PIDS; do
      if [ -n "$PID" ] && [ "$PID" != "null" ]; then
        local PNAME
        PNAME=$(api_get "projects/${PID}" 2>/dev/null | jq -r '.title // "Unknown"')
        PROJECT_NAMES=$(echo "$PROJECT_NAMES" | jq --arg pid "$PID" --arg pname "$PNAME" '. + {($pid): $pname}')
      fi
    done
  fi

  echo "$TASKS" | jq -r --argjson buckets "$ALL_BUCKETS" --argjson projects "$PROJECT_NAMES" '
    if length == 0 then "No tasks found."
    else
      .[] | 
      . as $task |
      "[\(if .done then "✅" else "⬜" end)] \(.title)" +
      (if .project_id != null and .project_id > 0 then 
        "\n    Project: " + ($projects[.project_id | tostring] // "Unknown")
      elif .bucket_id != null and .bucket_id > 0 then
        # Infer project from bucket
        ([$buckets[] | select(.id == $task.bucket_id)][0] | 
         if . != null then "\n    Project: " + ($projects[.project_id | tostring] // "Unknown") else "" end)
      else "" end) +
      (if .bucket_id != null and .bucket_id > 0 and ($buckets | length) > 0 then 
        "\n    Stage: " + ([$buckets[] | select(.id == $task.bucket_id)][0].title // "Unknown")
      else "" end) +
      (if .assignees != null and (.assignees | length) > 0 then 
        "\n    Assigned: " + ([.assignees[].username] | join(", "))
      else "" end) +
      (if .due_date != null and .due_date != "0001-01-01T00:00:00Z" then "\n    Due: \(.due_date[0:10])" else "" end) +
      (if .priority > 0 then "\n    Priority: \(.priority)/5" else "" end) +
      "\n    ID: \(.id)\n"
    end
  ' 2>/dev/null || echo "Error parsing tasks" >&2
}

# --- Commands ---

cmd_search() {
  local QUERY=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --query) QUERY="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$QUERY" ]; then
    echo "Error: --query is required" >&2
    exit 1
  fi

  # Get all projects and search in each by fetching all tasks
  local PROJECTS
  PROJECTS=$(api_get "projects" | jq -r '.[].id')
  
  local FOUND=0
  local QUERY_LOWER
  QUERY_LOWER=$(echo "$QUERY" | tr '[:upper:]' '[:lower:]')
  
  for PID in $PROJECTS; do
    local TASKS
    TASKS=$(api_get "projects/${PID}/tasks" 2>/dev/null)
    
    if [ -n "$TASKS" ]; then
      # Filter tasks locally by title or description containing query (case insensitive)
      local FILTERED
      FILTERED=$(echo "$TASKS" | jq --arg query "$QUERY_LOWER" '
        [.[] | select(
          (.title | ascii_downcase | contains($query)) or 
          (.description | ascii_downcase | contains($query))
        )]
      ')
      
      if [ "$(echo "$FILTERED" | jq 'length')" -gt 0 ]; then
        # Get project name
        local PROJECT_NAME
        PROJECT_NAME=$(api_get "projects/${PID}" | jq -r '.title')
        
        # Get buckets for this project
        local BUCKETS
        BUCKETS=$(api_get "projects/${PID}/buckets" 2>/dev/null)
        
        echo "$FILTERED" | jq -r --arg project "$PROJECT_NAME" --argjson buckets "$BUCKETS" '
          .[] | 
          (if .done then "[✅]" else "[⬜]" end) + " \(.title)" +
          "\n    Project: \($project)" +
          (if .bucket_id > 0 then 
            "\n    Stage: " + ([$buckets[] | select(.id == (.bucket_id // 0))][0].title // "Unknown")
          else "" end) +
          (if .due_date != null and .due_date != "0001-01-01T00:00:00Z" then "\n    Due: \(.due_date | split("T")[0])" else "" end) +
          (if .priority > 0 then "\n    Priority: \(.priority)/5" else "" end) +
          "\n    ID: \(.id)\n"
        '
        FOUND=1
      fi
    fi
  done
  
  if [ $FOUND -eq 0 ]; then
    echo "No tasks found matching: $QUERY"
  fi
}

cmd_tasks() {
  local COUNT=20
  local SEARCH=""
  local FILTER=""
  local PROJECT=""
  local ASSIGN=""
  local SORT="due_date"
  local ORDER="asc"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --count) COUNT="$2"; shift 2 ;;
      --search) SEARCH="$2"; shift 2 ;;
      --filter) FILTER="$2"; shift 2 ;;
      --project) PROJECT="$2"; shift 2 ;;
      --assign|--assignee) ASSIGN="$2"; shift 2 ;;
      --sort) SORT="$2"; shift 2 ;;
      --order) ORDER="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  local URL="tasks/all?per_page=${COUNT}&sort_by=${SORT}&order_by=${ORDER}&filter_timezone=America/Denver"

  if [ -n "$SEARCH" ]; then
    URL="${URL}&s=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SEARCH'))")"
  fi

  if [ -n "$FILTER" ]; then
    URL="${URL}&filter=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$FILTER'))")"
  fi

  if [ -n "$PROJECT" ]; then
    local PID
    PID=$(get_project_id "$PROJECT")
    if [ -z "$PID" ]; then
      echo "Error: Project '$PROJECT' not found" >&2
      exit 1
    fi
    
    # Use project-specific endpoint instead of filter
    local PROJECT_URL="projects/${PID}/tasks?per_page=${COUNT}&sort_by=${SORT}&order_by=${ORDER}"
    if [ -n "$SEARCH" ]; then
      PROJECT_URL="${PROJECT_URL}&s=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SEARCH'))")"
    fi
    if [ -n "$FILTER" ]; then
      PROJECT_URL="${PROJECT_URL}&filter=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$FILTER'))")"
    fi
    
    # Get tasks and buckets for this project
    local RESULT
    RESULT=$(api_get "$PROJECT_URL")
    local BUCKETS
    BUCKETS=$(api_get "projects/${PID}/buckets" 2>/dev/null || echo "[]")
    
    # Filter by assignee if specified
    if [ -n "$ASSIGN" ]; then
      RESULT=$(echo "$RESULT" | jq --arg user "$ASSIGN" '[.[] | select(.assignees != null and (.assignees | any(.username == $user)))]')
    fi
    
    # Format with bucket names - store bucket_id in variable for matching
    echo "$RESULT" | jq -r --argjson buckets "$BUCKETS" '
      if length == 0 then "No tasks found."
      else
        .[] | 
        . as $task |
        "[\(if .done then "✅" else "⬜" end)] \(.title)" +
        (if .bucket_id != null and .bucket_id > 0 then 
          "\n    Stage: " + (($buckets[] | select(.id == $task.bucket_id) | .title) // ("bucket " + (.bucket_id | tostring)))
        else "" end) +
        (if .assignees != null and (.assignees | length) > 0 then 
          "\n    Assigned: " + ([.assignees[].username] | join(", "))
        else "" end) +
        (if .due_date != null and .due_date != "0001-01-01T00:00:00Z" then "\n    Due: \(.due_date[0:10])" else "" end) +
        (if .priority > 0 then "\n    Priority: \(.priority)/5" else "" end) +
        "\n    ID: \(.id)\n"
      end
    '
  else
    # Get all tasks
    local RESULT
    RESULT=$(api_get "$URL")
    
    # Filter by assignee if specified
    if [ -n "$ASSIGN" ]; then
      RESULT=$(echo "$RESULT" | jq --arg user "$ASSIGN" '[.[] | select(.assignees != null and (.assignees | any(.username == $user)))]')
    fi
    
    echo "$RESULT" | format_tasks
  fi
}

cmd_overdue() {
  local NOW
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%S")
  local FILTER="due_date < '${NOW}' && done = false"
  local URL="tasks/all?per_page=50&sort_by=due_date&order_by=asc&filter_timezone=America/Denver"
  URL="${URL}&filter=$(python3 -c "import urllib.parse; print(urllib.parse.quote(\"$FILTER\"))")"
  api_get "$URL" | format_tasks
}

cmd_due() {
  local HOURS=24
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --hours) HOURS="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  local NOW
  local FUTURE
  NOW=$(date -u +"%Y-%m-%dT%H:%M:%S")
  FUTURE=$(date -u -v+${HOURS}H +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || date -u -d "+${HOURS} hours" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null)

  local FILTER="due_date > '${NOW}' && due_date < '${FUTURE}' && done = false"
  local URL="tasks/all?per_page=50&sort_by=due_date&order_by=asc&filter_timezone=America/Denver"
  URL="${URL}&filter=$(python3 -c "import urllib.parse; print(urllib.parse.quote(\"$FILTER\"))")"
  api_get "$URL" | format_tasks
}

get_bucket_id() {
  local PROJECT_ID="$1"
  local BUCKET_NAME="$2"
  
  api_get "projects/${PROJECT_ID}/buckets" | jq -r --arg name "$BUCKET_NAME" '
    .[] | select(.title | ascii_downcase | contains($name | ascii_downcase)) | .id
  ' | head -1
}

cmd_create_task() {
  local TITLE=""
  local DESCRIPTION=""
  local DUE=""
  local PRIORITY=0
  local PROJECT=""
  local BUCKET=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE="$2"; shift 2 ;;
      --description) DESCRIPTION="$2"; shift 2 ;;
      --due) DUE="$2"; shift 2 ;;
      --priority) PRIORITY="$2"; shift 2 ;;
      --project) PROJECT="$2"; shift 2 ;;
      --bucket|--stage) BUCKET="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$TITLE" ] || [ -z "$PROJECT" ]; then
    echo "Error: --title and --project are required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  local BODY
  BODY=$(jq -n \
    --arg title "$TITLE" \
    --arg desc "$DESCRIPTION" \
    --arg due "$DUE" \
    --argjson priority "$PRIORITY" \
    '{title: $title, description: $desc, priority: $priority} + (if $due != "" then {due_date: ($due + "T00:00:00Z")} else {} end)')

  # Add bucket_id if specified
  if [ -n "$BUCKET" ]; then
    local BUCKET_ID
    BUCKET_ID=$(get_bucket_id "$PID" "$BUCKET")
    if [ -n "$BUCKET_ID" ]; then
      BODY=$(echo "$BODY" | jq --argjson bucket_id "$BUCKET_ID" '. + {bucket_id: $bucket_id}')
    else
      echo "Warning: Bucket '$BUCKET' not found, using default" >&2
    fi
  fi

  local RESPONSE
  RESPONSE=$(api_put "projects/${PID}/tasks" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local ID
    ID=$(echo "$RESPONSE" | jq -r '.id')
    local BUCKET_NAME
    BUCKET_NAME=$(echo "$RESPONSE" | jq -r '.bucket_id // empty')
    if [ -n "$BUCKET_NAME" ] && [ -n "$BUCKET" ]; then
      echo "Created task: $TITLE (id: $ID) in project: $PROJECT → $BUCKET"
    else
      echo "Created task: $TITLE (id: $ID) in project: $PROJECT"
    fi
  else
    echo "Error creating task:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_complete() {
  local ID=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ]; then
    echo "Error: --id is required" >&2
    exit 1
  fi

  local RESPONSE
  RESPONSE=$(api_post "tasks/${ID}" '{"done": true}')

  if echo "$RESPONSE" | jq -e '.done' > /dev/null 2>&1; then
    local TITLE
    TITLE=$(echo "$RESPONSE" | jq -r '.title')
    echo "Completed: $TITLE (id: $ID) ✅"
  else
    echo "Error completing task:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_edit_task() {
  local ID=""
  local TITLE=""
  local DESCRIPTION=""
  local DUE=""
  local PRIORITY=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --title) TITLE="$2"; shift 2 ;;
      --description) DESCRIPTION="$2"; shift 2 ;;
      --due) DUE="$2"; shift 2 ;;
      --priority) PRIORITY="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ]; then
    echo "Error: --id is required" >&2
    exit 1
  fi

  # Build update body with only provided fields
  local UPDATES=()
  [ -n "$TITLE" ] && UPDATES+=("\"title\": $(jq -n --arg t "$TITLE" '$t')")
  [ -n "$DESCRIPTION" ] && UPDATES+=("\"description\": $(jq -n --arg d "$DESCRIPTION" '$d')")
  [ -n "$DUE" ] && UPDATES+=("\"due_date\": $(jq -n --arg d "${DUE}T00:00:00Z" '$d')")
  [ -n "$PRIORITY" ] && UPDATES+=("\"priority\": $PRIORITY")

  if [ ${#UPDATES[@]} -eq 0 ]; then
    echo "Error: At least one field to update is required (--title, --description, --due, --priority)" >&2
    exit 1
  fi

  local BODY
  BODY=$(printf '{%s}' "$(IFS=,; echo "${UPDATES[*]}")")

  local RESPONSE
  RESPONSE=$(api_post "tasks/${ID}" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local TASK_TITLE
    TASK_TITLE=$(echo "$RESPONSE" | jq -r '.title')
    echo "Updated task: $TASK_TITLE (id: $ID)"
  else
    echo "Error updating task:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_delete_task() {
  local ID=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ]; then
    echo "Error: --id is required" >&2
    exit 1
  fi

  # Get task title before deleting
  local TASK_INFO
  TASK_INFO=$(api_get "tasks/${ID}")
  local TITLE
  TITLE=$(echo "$TASK_INFO" | jq -r '.title')

  local RESPONSE
  RESPONSE=$(curl -s -X DELETE \
    -H "Authorization: Bearer ${VIKUNJA_TOKEN}" \
    -H "Content-Type: application/json" \
    "${VIKUNJA_URL}/api/v1/tasks/${ID}")

  if echo "$RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    echo "Deleted task: $TITLE (id: $ID) 🗑️"
  else
    echo "Error deleting task:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_move_task() {
  local ID=""
  local BUCKET=""
  local PROJECT=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --bucket|--stage) BUCKET="$2"; shift 2 ;;
      --project) PROJECT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ] || [ -z "$BUCKET" ]; then
    echo "Error: --id and --bucket are required" >&2
    exit 1
  fi

  # Get task to find its project if not specified
  if [ -z "$PROJECT" ]; then
    local TASK_INFO
    TASK_INFO=$(api_get "tasks/${ID}")
    local PROJECT_ID
    PROJECT_ID=$(echo "$TASK_INFO" | jq -r '.project_id')
  else
    local PROJECT_ID
    PROJECT_ID=$(get_project_id "$PROJECT")
    if [ -z "$PROJECT_ID" ]; then
      echo "Error: Project '$PROJECT' not found" >&2
      exit 1
    fi
  fi

  # Get bucket ID
  local BUCKET_ID
  BUCKET_ID=$(get_bucket_id "$PROJECT_ID" "$BUCKET")
  
  if [ -z "$BUCKET_ID" ]; then
    echo "Error: Bucket '$BUCKET' not found in project" >&2
    exit 1
  fi

  # Move task to bucket
  local BODY
  BODY=$(jq -n --argjson bucket_id "$BUCKET_ID" '{bucket_id: $bucket_id}')
  
  local RESPONSE
  RESPONSE=$(api_post "tasks/${ID}" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local TITLE
    TITLE=$(echo "$RESPONSE" | jq -r '.title')
    echo "Moved task: $TITLE (id: $ID) → $BUCKET"
  else
    echo "Error moving task:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_task() {
  local ID=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ]; then
    echo "Error: --id is required" >&2
    exit 1
  fi

  api_get "tasks/${ID}" | jq '{
    id: .id,
    title: .title,
    description: .description,
    done: .done,
    due_date: .due_date,
    priority: .priority,
    percent_done: .percent_done,
    project: .project.title,
    assignees: [.assignees[]? | {username: .username, name: .name}],
    labels: [.labels[]?.title],
    created: .created,
    updated: .updated
  }'
}

cmd_comments() {
  local ID=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ]; then
    echo "Error: --id is required" >&2
    exit 1
  fi

  api_get "tasks/${ID}/comments" | jq -r '
    if length == 0 then "No comments found."
    else
      .[] | "[\(.id)] \(.author.username) (\(.created | split("T")[0])):\n    \(.comment)"
    end
  '
}

cmd_add_comment() {
  local ID=""
  local COMMENT=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --comment) COMMENT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ] || [ -z "$COMMENT" ]; then
    echo "Error: --id and --comment are required" >&2
    exit 1
  fi

  local BODY
  BODY=$(jq -n --arg comment "$COMMENT" '{comment: $comment}')
  
  local RESPONSE
  RESPONSE=$(api_put "tasks/${ID}/comments" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    echo "Added comment to task (id: $ID)"
  else
    echo "Error adding comment:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_users() {
  local PROJECT=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project) PROJECT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$PROJECT" ]; then
    echo "Error: --project is required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  api_get "projects/${PID}/users" | jq -r '
    if length == 0 then "No individual users found."
    else
      .[] | "[\(.id)] \(.username) - \(.name // "No name") - \(.rights // "unknown") rights"
    end
  '
}

cmd_project_teams() {
  local PROJECT=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project) PROJECT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$PROJECT" ]; then
    echo "Error: --project is required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  local TEAMS
  TEAMS=$(api_get "projects/${PID}/teams")
  
  if [ "$(echo "$TEAMS" | jq 'length')" -eq 0 ]; then
    echo "No teams found."
    return
  fi
  
  echo "$TEAMS" | jq -r '.[] | 
    "[\(.id)] \(.name) - \(.rights // "unknown") rights" +
    "\n    Members (\(.members | length)):" +
    (if (.members | length) > 0 then
      "\n" + (.members | map("      - \(.username) (\(.name // "no name"))") | join("\n"))
    else
      " (no members)"
    end)
  '
}

cmd_invite_user() {
  local PROJECT=""
  local USER=""
  local RIGHTS="read"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project) PROJECT="$2"; shift 2 ;;
      --user) USER="$2"; shift 2 ;;
      --rights) RIGHTS="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$PROJECT" ] || [ -z "$USER" ]; then
    echo "Error: --project and --user are required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  # Rights mapping: 0=read, 1=read+write, 2=admin
  local RIGHTS_NUM
  case "$RIGHTS" in
    read) RIGHTS_NUM=0 ;;
    write|read-write) RIGHTS_NUM=1 ;;
    admin) RIGHTS_NUM=2 ;;
    *) 
      echo "Error: Invalid rights '$RIGHTS'. Use: read, write, or admin" >&2
      exit 1
      ;;
  esac
  
  # Find user ID from username - search in all teams
  local USER_ID=""
  local TEAMS
  TEAMS=$(api_get "teams")
  USER_ID=$(echo "$TEAMS" | jq -r --arg user "$USER" '
    [.[].members[] | select(.username == $user or .name == $user or (.id | tostring) == $user)] | .[0].id
  ')
  
  if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "Error: User '$USER' not found" >&2
    exit 1
  fi

  # Create share body with user ID
  local BODY
  BODY=$(jq -n \
    --argjson user_id "$USER_ID" \
    --argjson rights "$RIGHTS_NUM" \
    '{user_id: $user_id, right: $rights}')

  local RESPONSE
  RESPONSE=$(api_put "projects/${PID}/shares" "$BODY")

  if echo "$RESPONSE" | jq -e '.username' > /dev/null 2>&1; then
    local USERNAME
    USERNAME=$(echo "$RESPONSE" | jq -r '.username')
    local RIGHTS_NAME
    RIGHTS_NAME=$(echo "$RESPONSE" | jq -r '.rights // "unknown"')
    echo "Invited user '$USERNAME' to project '$PROJECT' with $RIGHTS_NAME rights"
  else
    echo "Error inviting user:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_assign_task() {
  local ID=""
  local USER=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --user) USER="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ] || [ -z "$USER" ]; then
    echo "Error: --id and --user are required" >&2
    exit 1
  fi

  # Get task info to find project
  local TASK_INFO
  TASK_INFO=$(api_get "tasks/${ID}")
  local PROJECT_ID
  PROJECT_ID=$(echo "$TASK_INFO" | jq -r '.project_id')
  
  # If project_id is null, try to find it from bucket_id
  if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "null" ]; then
    local BUCKET_ID
    BUCKET_ID=$(echo "$TASK_INFO" | jq -r '.bucket_id')
    if [ -n "$BUCKET_ID" ] && [ "$BUCKET_ID" != "null" ]; then
      # Get all projects and find which one has this bucket
      local PROJECTS
      PROJECTS=$(api_get "projects" | jq -r '.[].id')
      for PID in $PROJECTS; do
        local BUCKETS
        BUCKETS=$(api_get "projects/${PID}/buckets" 2>/dev/null)
        if echo "$BUCKETS" | jq -e --argjson bid "$BUCKET_ID" '.[] | select(.id == $bid)' > /dev/null 2>&1; then
          PROJECT_ID="$PID"
          break
        fi
      done
    fi
  fi
  
  if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "null" ]; then
    echo "Error: Cannot determine project for task ${ID}" >&2
    exit 1
  fi

  # Get users from project to find user ID
  local USERS
  USERS=$(api_get "projects/${PROJECT_ID}/users")
  
  local USER_ID
  USER_ID=$(echo "$USERS" | jq -r --arg user "$USER" '
    .[] | select(.username == $user or .name == $user or (.id | tostring) == $user) | .id
  ' | head -1)

  # If not found in project users, try project teams
  if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    local TEAMS
    TEAMS=$(api_get "projects/${PROJECT_ID}/teams")
    USER_ID=$(echo "$TEAMS" | jq -r --arg user "$USER" '
      [.[].members[] | select(.username == $user or .name == $user or (.id | tostring) == $user)] | .[0].id
    ')
  fi

  if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "Error: User '$USER' not found in project or project teams" >&2
    echo "Available users:" >&2
    echo "$USERS" | jq -r '.[] | "  - \(.username) (\(.name // "no name"))"' >&2
    exit 1
  fi

  # Assign user to task - Vikunja uses PUT to add an assignee
  local BODY
  BODY=$(jq -n --argjson user_id "$USER_ID" '{user_id: $user_id}')
  
  local RESPONSE
  RESPONSE=$(api_put "tasks/${ID}/assignees" "$BODY")

  if echo "$RESPONSE" | jq -e '.username' > /dev/null 2>&1; then
    local USERNAME
    USERNAME=$(echo "$RESPONSE" | jq -r '.username')
    local TASK_TITLE
    TASK_TITLE=$(echo "$TASK_INFO" | jq -r '.title')
    echo "Assigned task '$TASK_TITLE' (id: $ID) to user: $USERNAME"
  else
    # Check if it's an error about user already assigned
    if echo "$RESPONSE" | jq -e '.code == 4021' > /dev/null 2>&1; then
      local TASK_TITLE
      TASK_TITLE=$(echo "$TASK_INFO" | jq -r '.title')
      echo "User '$USER' is already assigned to task '$TASK_TITLE' (id: $ID)" >&2
      exit 0  # Not an error, just already assigned
    else
      echo "Error assigning task:" >&2
      echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
      exit 1
    fi
  fi
}

cmd_projects() {
  api_get "projects" | jq -r '.[] | "\(.title) (id: \(.id))" + (if .description != "" then "\n    \(.description)" else "" end)'
}

cmd_labels() {
  api_get "labels" | jq -r '
    if length == 0 then "No labels found."
    else
      .[] | "[\(.id)] \(.title)" + (if .description != "" then " - \(.description)" else "" end)
    end
  '
}

cmd_add_label() {
  local ID=""
  local LABEL=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --label) LABEL="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ] || [ -z "$LABEL" ]; then
    echo "Error: --id and --label are required" >&2
    exit 1
  fi

  # Get or create label
  local LABELS
  LABELS=$(api_get "labels")
  local LABEL_ID
  LABEL_ID=$(echo "$LABELS" | jq -r --arg label "$LABEL" '
    .[] | select(.title == $label) | .id
  ' | head -1)

  # Create label if it doesn't exist
  if [ -z "$LABEL_ID" ]; then
    local NEW_LABEL
    NEW_LABEL=$(jq -n --arg title "$LABEL" '{title: $title}')
    local RESPONSE
    RESPONSE=$(api_put "labels" "$NEW_LABEL")
    LABEL_ID=$(echo "$RESPONSE" | jq -r '.id')
  fi

  # Add label to task
  local BODY
  BODY=$(jq -n --argjson label_id "$LABEL_ID" '{label_id: $label_id}')
  
  local RESPONSE
  RESPONSE=$(api_put "tasks/${ID}/labels" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    echo "Added label '$LABEL' to task (id: $ID)"
  else
    echo "Error adding label:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_remove_label() {
  local ID=""
  local LABEL=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) ID="$2"; shift 2 ;;
      --label) LABEL="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$ID" ] || [ -z "$LABEL" ]; then
    echo "Error: --id and --label are required" >&2
    exit 1
  fi

  # Get label ID
  local LABELS
  LABELS=$(api_get "labels")
  local LABEL_ID
  LABEL_ID=$(echo "$LABELS" | jq -r --arg label "$LABEL" '
    .[] | select(.title == $label) | .id
  ' | head -1)

  if [ -z "$LABEL_ID" ]; then
    echo "Error: Label '$LABEL' not found" >&2
    exit 1
  fi

  # Remove label from task
  local RESPONSE
  RESPONSE=$(curl -s -X DELETE \
    -H "Authorization: Bearer ${VIKUNJA_TOKEN}" \
    -H "Content-Type: application/json" \
    "${VIKUNJA_URL}/api/v1/tasks/${ID}/labels/${LABEL_ID}")

  if echo "$RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    echo "Removed label '$LABEL' from task (id: $ID)"
  else
    echo "Error removing label:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_teams() {
  local TEAMS
  TEAMS=$(api_get "teams")
  
  if [ "$(echo "$TEAMS" | jq 'length')" -eq 0 ]; then
    echo "No teams found."
    return
  fi
  
  echo "$TEAMS" | jq -r '.[] | 
    "[\(.id)] \(.name)" + 
    (if .description != "" then " - \(.description)" else "" end) + 
    "\n    Members (\(.members | length)):" +
    (if (.members | length) > 0 then
      "\n" + (.members | map("      - \(.username) (\(.name // "no name"))") | join("\n"))
    else
      " (no members)"
    end)
  '
}

cmd_create_team() {
  local NAME=""
  local DESCRIPTION=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name) NAME="$2"; shift 2 ;;
      --description) DESCRIPTION="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$NAME" ]; then
    echo "Error: --name is required" >&2
    exit 1
  fi

  local BODY
  BODY=$(jq -n \
    --arg name "$NAME" \
    --arg desc "$DESCRIPTION" \
    '{name: $name, description: $desc}')

  local RESPONSE
  RESPONSE=$(api_put "teams" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local ID
    ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "Created team: $NAME (id: $ID)"
  else
    echo "Error creating team:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_share_project() {
  local PROJECT=""
  local TEAM=""
  local RIGHTS="read"
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project) PROJECT="$2"; shift 2 ;;
      --team) TEAM="$2"; shift 2 ;;
      --rights) RIGHTS="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$PROJECT" ] || [ -z "$TEAM" ]; then
    echo "Error: --project and --team are required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  # Get team ID by name
  local TEAMS
  TEAMS=$(api_get "teams")
  local TEAM_ID
  TEAM_ID=$(echo "$TEAMS" | jq -r --arg team "$TEAM" '
    .[] | select(.name == $team or (.id | tostring) == $team) | .id
  ' | head -1)

  if [ -z "$TEAM_ID" ]; then
    echo "Error: Team '$TEAM' not found" >&2
    echo "Available teams:" >&2
    echo "$TEAMS" | jq -r '.[] | "  - \(.name) (id: \(.id))"' >&2
    exit 1
  fi

  # Rights mapping: 0=read, 1=read+write, 2=admin
  local RIGHTS_NUM
  case "$RIGHTS" in
    read) RIGHTS_NUM=0 ;;
    write|read-write) RIGHTS_NUM=1 ;;
    admin) RIGHTS_NUM=2 ;;
    *) 
      echo "Error: Invalid rights '$RIGHTS'. Use: read, write, or admin" >&2
      exit 1
      ;;
  esac

  local BODY
  BODY=$(jq -n \
    --argjson team_id "$TEAM_ID" \
    --argjson rights "$RIGHTS_NUM" \
    '{team_id: $team_id, right: $rights}')

  local RESPONSE
  RESPONSE=$(api_put "projects/${PID}/teams" "$BODY")

  if echo "$RESPONSE" | jq -e '.team_id' > /dev/null 2>&1; then
    local TEAM_NAME
    TEAM_NAME=$(echo "$TEAMS" | jq -r --argjson tid "$TEAM_ID" '.[] | select(.id == $tid) | .name')
    echo "Shared project '$PROJECT' with team '$TEAM_NAME' (${RIGHTS} rights)"
  else
    echo "Error sharing project:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

create_default_stages() {
  local PROJECT_ID="$1"
  local PROJECT_TITLE="$2"
  
  echo "Creating default Kanban stages for $PROJECT_TITLE..."
  
  # Stage 1: Backlog (📋)
  local BACKLOG_BODY
  BACKLOG_BODY=$(jq -n '{title: "📋 Backlog", position: 0}')
  api_put "projects/${PROJECT_ID}/buckets" "$BACKLOG_BODY" > /dev/null
  
  # Stage 2: To Do (📝)
  local TODO_BODY
  TODO_BODY=$(jq -n '{title: "📝 To Do", position: 1}')
  api_put "projects/${PROJECT_ID}/buckets" "$TODO_BODY" > /dev/null
  
  # Stage 3: In Progress (🔄)
  local PROGRESS_BODY
  PROGRESS_BODY=$(jq -n '{title: "🔄 In Progress", position: 2}')
  api_put "projects/${PROJECT_ID}/buckets" "$PROGRESS_BODY" > /dev/null
  
  # Stage 4: Review (👀)
  local REVIEW_BODY
  REVIEW_BODY=$(jq -n '{title: "👀 Review", position: 3}')
  api_put "projects/${PROJECT_ID}/buckets" "$REVIEW_BODY" > /dev/null
  
  # Stage 5: Done (✅)
  local DONE_BODY
  DONE_BODY=$(jq -n '{title: "✅ Done", position: 4}')
  api_put "projects/${PROJECT_ID}/buckets" "$DONE_BODY" > /dev/null
  
  echo "  ✓ Created 5 default stages: Backlog, To Do, In Progress, Review, Done"
}

cmd_create_project() {
  local TITLE=""
  local DESCRIPTION=""
  local PARENT=""
  local NO_STAGES=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE="$2"; shift 2 ;;
      --description) DESCRIPTION="$2"; shift 2 ;;
      --parent) PARENT="$2"; shift 2 ;;
      --no-stages) NO_STAGES=true; shift ;;
      *) shift ;;
    esac
  done

  if [ -z "$TITLE" ]; then
    echo "Error: --title is required" >&2
    exit 1
  fi

  local BODY
  BODY=$(jq -n \
    --arg title "$TITLE" \
    --arg desc "$DESCRIPTION" \
    --arg parent "$PARENT" \
    '{title: $title, description: $desc} + (if $parent != "" then {parent_project_id: ($parent | tonumber)} else {} end)')

  local RESPONSE
  RESPONSE=$(api_put "projects" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local ID
    ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "Created project: $TITLE (id: $ID)"
    
    # Create default Kanban stages unless --no-stages is specified
    if [ "$NO_STAGES" = false ]; then
      create_default_stages "$ID" "$TITLE"
    fi
  else
    echo "Error creating project:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

cmd_notifications() {
  api_get "notifications" | jq -r '
    if length == 0 then "No notifications."
    else
      .[] | "\(.created | split("T")[0]) - \(.name // "Notification")\n  \(.notification.subject // .notification // "No details")\n"
    end
  '
}

cmd_buckets() {
  local PROJECT=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project) PROJECT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$PROJECT" ]; then
    echo "Error: --project is required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  api_get "projects/${PID}/buckets" | jq -r '
    if length == 0 then "No buckets found."
    else
      .[] | "[\(.id)] \(.title)" + (if .position != null then " (position: \(.position))" else "" end)
    end
  '
}

cmd_create_bucket() {
  local TITLE=""
  local PROJECT=""
  local POSITION=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title) TITLE="$2"; shift 2 ;;
      --project) PROJECT="$2"; shift 2 ;;
      --position) POSITION="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ -z "$TITLE" ] || [ -z "$PROJECT" ]; then
    echo "Error: --title and --project are required" >&2
    exit 1
  fi

  local PID
  PID=$(get_project_id "$PROJECT")
  if [ -z "$PID" ]; then
    echo "Error: Project '$PROJECT' not found" >&2
    exit 1
  fi

  local BODY
  if [ -n "$POSITION" ]; then
    BODY=$(jq -n --arg title "$TITLE" --argjson position "$POSITION" '{title: $title, position: $position}')
  else
    BODY=$(jq -n --arg title "$TITLE" '{title: $title}')
  fi

  local RESPONSE
  RESPONSE=$(api_put "projects/${PID}/buckets" "$BODY")

  if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    local ID
    ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "Created bucket: $TITLE (id: $ID) in project: $PROJECT"
  else
    echo "Error creating bucket:" >&2
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE" >&2
    exit 1
  fi
}

# --- Main ---
COMMAND="${1:-tasks}"
shift 2>/dev/null || true

case "$COMMAND" in
  tasks|list) cmd_tasks "$@" ;;
  search) cmd_search "$@" ;;
  overdue) cmd_overdue ;;
  due|upcoming) cmd_due "$@" ;;
  create-task|add) cmd_create_task "$@" ;;
  edit-task|edit|update) cmd_edit_task "$@" ;;
  delete-task|delete|remove) cmd_delete_task "$@" ;;
  complete|done) cmd_complete "$@" ;;
  move-task|move) cmd_move_task "$@" ;;
  assign-task|assign) cmd_assign_task "$@" ;;
  task|get) cmd_task "$@" ;;
  labels) cmd_labels ;;
  add-label) cmd_add_label "$@" ;;
  remove-label) cmd_remove_label "$@" ;;
  comments) cmd_comments "$@" ;;
  add-comment) cmd_add_comment "$@" ;;
  users) cmd_users "$@" ;;
  project-teams) cmd_project_teams "$@" ;;
  invite-user|invite|share) cmd_invite_user "$@" ;;
  teams) cmd_teams ;;
  create-team) cmd_create_team "$@" ;;
  share-project) cmd_share_project "$@" ;;
  projects) cmd_projects ;;
  create-project) cmd_create_project "$@" ;;
  buckets|stages) cmd_buckets "$@" ;;
  create-bucket|create-stage) cmd_create_bucket "$@" ;;
  notifications|notifs) cmd_notifications ;;
  *)
    echo "Usage: $0 {tasks|search|overdue|due|create-task|edit-task|delete-task|complete|move-task|assign-task|task|labels|add-label|remove-label|comments|add-comment|users|project-teams|invite-user|teams|create-team|share-project|projects|create-project|buckets|create-bucket|notifications}" >&2
    exit 1
    ;;
esac
