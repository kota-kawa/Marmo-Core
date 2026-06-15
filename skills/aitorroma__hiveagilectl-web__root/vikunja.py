#!/usr/bin/env python3
"""
Vikunja Python CLI - Better handling of multiline descriptions
"""

import argparse
import json
import subprocess
import sys
import re
import os
from pathlib import Path

def load_credentials():
    """Load credentials from credentials.json and set environment variables"""
    # Try ~/.nimworker first, then current directory
    creds_paths = [
        Path.home() / '.nimworker' / 'credentials.json',
        Path(__file__).parent / 'credentials.json'
    ]
    
    for creds_file in creds_paths:
        if creds_file.exists():
            with open(creds_file) as f:
                creds = json.load(f)
            
            os.environ['VIKUNJA_URL'] = creds.get('vikunja_url', '')
            os.environ['VIKUNJA_TOKEN'] = creds.get('vikunja_token', '')
            os.environ['VIKUNJA_TZ'] = creds.get('timezone', 'Europe/Rome')
            os.environ['VIKUNJA_PROJECT_PERSONAL'] = creds.get('projects', {}).get('personal', 'PERSONAL')
            os.environ['VIKUNJA_PROJECT_WORK'] = creds.get('projects', {}).get('work', 'WORK')
            return
    
    print("Error: credentials.json not found", file=sys.stderr)
    print(f"Expected at: {creds_paths[0]} or {creds_paths[1]}", file=sys.stderr)
    sys.exit(1)

def text_to_html(text):
    """Convert plain text with structure to HTML"""
    if not text:
        return text
    
    # If already contains HTML tags, return as-is
    if '<' in text and '>' in text:
        return text
    
    lines = text.split('\n')
    html_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Empty line -> paragraph break
        if not stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
            continue
        
        # Detect headers (ALL CAPS followed by colon)
        if re.match(r'^[A-ZÁÉÍÓÚÑ\s]+:', stripped):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<strong>{stripped}</strong><br>')
            continue
        
        # Detect list items (starts with - or number.)
        if re.match(r'^[-•]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Remove the bullet/number
            item_text = re.sub(r'^[-•]\s+', '', stripped)
            item_text = re.sub(r'^\d+\.\s+', '', item_text)
            html_lines.append(f'<li>{item_text}</li>')
            continue
        
        # Regular line
        if in_list:
            html_lines.append('</ul>')
            in_list = False
        html_lines.append(f'{stripped}<br>')
    
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)

def create_task(project, title, description=None, due=None, priority=None, bucket=None, format_html=True):
    """Create a task using the vikunja.sh script"""
    # Load credentials first
    load_credentials()
    
    # Use vikunja.sh directly
    script_path = Path(__file__).parent / 'skill' / 'scripts' / 'vikunja.sh'
    if not script_path.exists():
        script_path = Path.home() / '.nimworker' / 'scripts' / 'vikunja.sh'
    
    cmd = [str(script_path), 'create-task', '--project', project, '--title', title]
    
    if description:
        if format_html:
            description = text_to_html(description)
        cmd.extend(['--description', description])
    if due:
        cmd.extend(['--due', due])
    if priority:
        cmd.extend(['--priority', str(priority)])
    if bucket:
        cmd.extend(['--bucket', bucket])
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

def run_vikunja_command(command, *args):
    """Run any vikunja.sh command"""
    load_credentials()
    
    script_path = Path(__file__).parent / 'skill' / 'scripts' / 'vikunja.sh'
    if not script_path.exists():
        script_path = Path.home() / '.nimworker' / 'scripts' / 'vikunja.sh'
    
    cmd = [str(script_path), command] + list(args)
    # Explicitly pass environment to subprocess
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
    
    # Print both stdout and stderr
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    
    sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(
        description='Vikunja task manager (Python wrapper)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  create-task    Create a new task (with auto-format)
  edit-task      Edit existing task
  delete-task    Delete a task
  tasks          List tasks
  search         Search tasks across all projects
  overdue        Show overdue tasks
  due            Show tasks due soon
  complete       Mark task as complete
  move-task      Move task to different stage
  assign-task    Assign task to user
  task           Get task details
  labels         List all labels
  add-label      Add label to task
  remove-label   Remove label from task
  comments       List task comments
  add-comment    Add comment to task
  users          List project users
  project-teams  List project teams
  invite-user    Invite user to project
  teams          List available teams
  create-team    Create new team
  share-project  Share project with team
  projects       List projects
  buckets        List Kanban stages
  
Examples:
  %(prog)s create-task --project WORK --title "Task" --description "..." --priority 4
  %(prog)s edit-task --id 123 --title "New title" --priority 5
  %(prog)s delete-task --id 123
  %(prog)s search --query "bug"
  %(prog)s tasks --project WORK --count 10
  %(prog)s add-label --id 123 --label "urgent"
  %(prog)s add-comment --id 123 --comment "Working on this"
  %(prog)s move-task --id 123 --bucket "In Progress"
  %(prog)s assign-task --id 123 --user "john"
  %(prog)s invite-user --project WORK --user "maria@example.com" --rights write
        """
    )
    
    # Subcommand
    parser.add_argument('command', nargs='?', default='create-task',
                       choices=['create-task', 'tasks', 'search', 'overdue', 'due', 'complete', 
                               'edit-task', 'delete-task', 'move-task', 'assign-task', 'task', 
                               'labels', 'add-label', 'remove-label', 'comments', 'add-comment',
                               'users', 'project-teams', 'invite-user', 'teams', 'create-team',
                               'share-project', 'projects', 'buckets', 'create-project'],
                       help='Command to execute')
    
    # create-task arguments
    parser.add_argument('--project', help='Project name (WORK, PERSONAL)')
    parser.add_argument('--title', help='Task title')
    parser.add_argument('--name', help='Team or entity name')
    parser.add_argument('--description', help='Task description (supports multiline)')
    parser.add_argument('--description-file', help='Read description from file')
    parser.add_argument('--due', help='Due date (YYYY-MM-DD)')
    parser.add_argument('--priority', type=int, choices=[1,2,3,4,5], help='Priority (1-5)')
    parser.add_argument('--bucket', '--stage', dest='bucket', help='Kanban stage/bucket')
    parser.add_argument('--no-format', action='store_true', help='Do not auto-format description to HTML')
    
    # Other command arguments
    parser.add_argument('--id', help='Task ID')
    parser.add_argument('--user', help='Username or email')
    parser.add_argument('--team', help='Team name')
    parser.add_argument('--label', help='Label name')
    parser.add_argument('--comment', help='Comment text')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--rights', choices=['read', 'write', 'admin'], default='read', help='Access rights for invite-user or share-project')
    parser.add_argument('--count', type=int, help='Number of items to show')
    parser.add_argument('--hours', type=int, help='Hours for due command')
    parser.add_argument('--search', help='Search text')
    parser.add_argument('--filter', help='Filter expression')
    parser.add_argument('--assign', '--assignee', dest='assign', help='Filter tasks by assignee username')
    parser.add_argument('--sort', help='Sort field')
    parser.add_argument('--order', choices=['asc', 'desc'], help='Sort order')
    
    args = parser.parse_args()
    
    # Handle create-task command
    if args.command == 'create-task':
        if not args.project or not args.title:
            parser.error('create-task requires --project and --title')
        
        description = args.description
        if args.description_file:
            with open(args.description_file, 'r') as f:
                description = f.read()
        
        create_task(
            project=args.project,
            title=args.title,
            description=description,
            due=args.due,
            priority=args.priority,
            bucket=args.bucket,
            format_html=not args.no_format
        )
    
    # Handle other commands - pass through to vikunja.sh
    else:
        cmd_args = []
        
        if args.command == 'tasks':
            if args.project:
                cmd_args.extend(['--project', args.project])
            if args.count:
                cmd_args.extend(['--count', str(args.count)])
            if args.search:
                cmd_args.extend(['--search', args.search])
            if args.filter:
                cmd_args.extend(['--filter', args.filter])
            if args.assign:
                cmd_args.extend(['--assign', args.assign])
            if args.sort:
                cmd_args.extend(['--sort', args.sort])
            if args.order:
                cmd_args.extend(['--order', args.order])
        
        elif args.command == 'overdue':
            if args.project:
                cmd_args.extend(['--project', args.project])
        
        elif args.command == 'due':
            if args.hours:
                cmd_args.extend(['--hours', str(args.hours)])
            if args.project:
                cmd_args.extend(['--project', args.project])
        
        elif args.command == 'search':
            if not args.query:
                parser.error('search requires --query')
            cmd_args.extend(['--query', args.query])
        
        elif args.command == 'complete':
            if not args.id:
                parser.error('complete requires --id')
            cmd_args.extend(['--id', args.id])
        
        elif args.command == 'edit-task':
            if not args.id:
                parser.error('edit-task requires --id')
            cmd_args.extend(['--id', args.id])
            if args.title:
                cmd_args.extend(['--title', args.title])
            if args.description:
                cmd_args.extend(['--description', args.description])
            if args.due:
                cmd_args.extend(['--due', args.due])
            if args.priority:
                cmd_args.extend(['--priority', str(args.priority)])
        
        elif args.command == 'delete-task':
            if not args.id:
                parser.error('delete-task requires --id')
            cmd_args.extend(['--id', args.id])
        
        elif args.command == 'move-task':
            if not args.id or not args.bucket:
                parser.error('move-task requires --id and --bucket')
            cmd_args.extend(['--id', args.id, '--bucket', args.bucket])
            if args.project:
                cmd_args.extend(['--project', args.project])
        
        elif args.command == 'assign-task':
            if not args.id or not args.user:
                parser.error('assign-task requires --id and --user')
            cmd_args.extend(['--id', args.id, '--user', args.user])
        
        elif args.command == 'users':
            if not args.project:
                parser.error('users requires --project')
            cmd_args.extend(['--project', args.project])
        
        elif args.command == 'project-teams':
            if not args.project:
                parser.error('project-teams requires --project')
            cmd_args.extend(['--project', args.project])
        
        elif args.command == 'invite-user':
            if not args.project or not args.user:
                parser.error('invite-user requires --project and --user')
            cmd_args.extend(['--project', args.project, '--user', args.user])
            if args.rights:
                cmd_args.extend(['--rights', args.rights])
        
        elif args.command == 'task':
            if not args.id:
                parser.error('task requires --id')
            cmd_args.extend(['--id', args.id])
        
        elif args.command == 'add-label':
            if not args.id or not args.label:
                parser.error('add-label requires --id and --label')
            cmd_args.extend(['--id', args.id, '--label', args.label])
        
        elif args.command == 'remove-label':
            if not args.id or not args.label:
                parser.error('remove-label requires --id and --label')
            cmd_args.extend(['--id', args.id, '--label', args.label])
        
        elif args.command == 'comments':
            if not args.id:
                parser.error('comments requires --id')
            cmd_args.extend(['--id', args.id])
        
        elif args.command == 'add-comment':
            if not args.id or not args.comment:
                parser.error('add-comment requires --id and --comment')
            cmd_args.extend(['--id', args.id, '--comment', args.comment])
        
        elif args.command == 'buckets':
            if not args.project:
                parser.error('buckets requires --project')
            cmd_args.extend(['--project', args.project])
        
        elif args.command == 'create-team':
            if not args.name:
                parser.error('create-team requires --name')
            cmd_args.extend(['--name', args.name])
            if args.description:
                cmd_args.extend(['--description', args.description])
        
        elif args.command == 'share-project':
            if not args.project or not args.team:
                parser.error('share-project requires --project and --team')
            cmd_args.extend(['--project', args.project, '--team', args.team])
            if args.rights:
                cmd_args.extend(['--rights', args.rights])
        
        run_vikunja_command(args.command, *cmd_args)

if __name__ == '__main__':
    main()
