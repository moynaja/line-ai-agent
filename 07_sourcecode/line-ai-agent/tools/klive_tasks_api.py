#!/usr/bin/env python3
"""klive-tasks API helper — create, list, get, update tasks and projects."""
import argparse
import html
import html.parser
import json
import os
import pathlib
import textwrap
import sys
import time
import urllib.parse
import urllib.error
import urllib.request


DEFAULT_API_URL = "http://127.0.0.1:4000/api"
CACHE_DIR = pathlib.Path(
    os.environ.get(
        "KLIVE_TASKS_CACHE_DIR",
        str(pathlib.Path.home() / ".agent-task-skill" / "klive-tasks"),
    )
).expanduser()
CACHE_FILE = CACHE_DIR / "token.json"


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

class _HtmlTextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.ignored_tag_depth = 0

    def handle_data(self, data):
        if self.ignored_tag_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.ignored_tag_depth += 1

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self.ignored_tag_depth > 0:
            self.ignored_tag_depth -= 1

    def text(self):
        return " ".join(self.parts)


# ---------------------------------------------------------------------------
# Config / auth
# ---------------------------------------------------------------------------

def env_config():
    return {
        "api_url": os.environ.get("KLIVE_TASKS_API_URL", DEFAULT_API_URL).rstrip("/"),
        "email": os.environ.get("KLIVE_TASKS_EMAIL", "").strip(),
        "password": os.environ.get("KLIVE_TASKS_PASSWORD", ""),
    }


def http_json(method, url, data=None, headers=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload) if payload else None


def read_cached_token():
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        token = data.get("access_token", "").strip()
        return token or None
    except Exception:
        return None


def write_cached_token(token):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps({"access_token": token, "saved_at": int(time.time())}))


def sign_in(config):
    if not config["email"] or not config["password"]:
        raise SystemExit("KLIVE_TASKS_EMAIL and KLIVE_TASKS_PASSWORD are required")
    response = http_json(
        "POST",
        f'{config["api_url"]}/auth/signin',
        {"email": config["email"], "password": config["password"], "keep_logged_in": True},
    )
    token = (response or {}).get("access_token", "").strip()
    if not token:
        raise SystemExit("Sign-in succeeded but no access_token was returned")
    write_cached_token(token)
    return token


def auth_headers(config, force_refresh=False):
    static_token = os.environ.get("KLIVE_API_TOKEN", "").strip()
    if static_token and not force_refresh:
        return {"Authorization": f"Bearer {static_token}"}
    token = None if force_refresh else read_cached_token()
    if not token:
        token = sign_in(config)
    return {"Authorization": f"Bearer {token}"}


def authed_request(config, method, path, data=None):
    url = f'{config["api_url"]}{path}'
    try:
        return http_json(method, url, data=data, headers=auth_headers(config))
    except urllib.error.HTTPError as error:
        if error.code != 401:
            detail = error.read().decode("utf-8", errors="replace")
            raise SystemExit(f"HTTP {error.code}: {detail}")
    try:
        return http_json(method, url, data=data, headers=auth_headers(config, force_refresh=True))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {error.code}: {detail}")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def compact(value, width):
    text = str(value or "").strip()
    if not text:
        return "-"
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def markdown_escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip() or "-"


def plain_text_description(value):
    text = (value or "").strip()
    if not text:
        return ""
    if "<" in text and ">" in text:
        parser = _HtmlTextExtractor()
        try:
            parser.feed(text)
            text = parser.text()
        except Exception:
            pass
    text = html.unescape(text)
    return " ".join(text.split())


def description_preview(value, width=180):
    text = plain_text_description(value)
    if not text:
        return ""
    return textwrap.shorten(text, width=width, placeholder="…")


# ---------------------------------------------------------------------------
# Task resolution
# ---------------------------------------------------------------------------

def normalize_id(value):
    return str(value or "").strip()


def resolve_task(config, task_identifier):
    task_identifier = normalize_id(task_identifier)
    if not task_identifier:
        raise SystemExit("Task id is required")

    # Try direct lookup first
    try:
        return authed_request(config, "GET", f"/tasks/{task_identifier}")
    except SystemExit as error:
        if "HTTP 404:" not in str(error):
            raise

    # Fall back to search
    tasks = authed_request(
        config, "GET",
        f"/tasks?{urllib.parse.urlencode({'search': task_identifier})}",
    )
    for task in tasks or []:
        if str(task.get("id", "")).strip() == task_identifier:
            return task
        if str(task.get("friendly_id", "")).strip() == task_identifier:
            raw_id = str(task.get("id", "")).strip()
            if raw_id:
                return authed_request(config, "GET", f"/tasks/{raw_id}")

    raise SystemExit(f"Task not found: {task_identifier}")


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def print_task_table(tasks, limit):
    rows = tasks[:limit] if limit else tasks
    if not rows:
        print("No tasks found.")
        return
    header = f"{'ID':24}  {'STATUS':12}  {'PRIORITY':10}  {'DUE':12}  TITLE"
    print(header)
    print("-" * len(header))
    for task in rows:
        task_id = compact(task.get("friendly_id"), 24)
        status = compact(task.get("status"), 12)
        priority = compact(task.get("priority"), 10)
        due_date = compact(task.get("due_date"), 12)
        title = compact(task.get("title"), 80)
        print(f"{task_id:24}  {status:12}  {priority:10}  {due_date:12}  {title}")
        desc = description_preview(task.get("description"), width=110)
        if desc:
            print(f"  {desc}")
    print(f"\nShowing {len(rows)} of {len(tasks)} task(s).")


def print_task_markdown(tasks, limit):
    rows = tasks[:limit] if limit else tasks
    if not rows:
        print("No tasks found.")
        return
    print("| ID | Status | Priority | Due | Title |")
    print("| --- | --- | --- | --- | --- |")
    for task in rows:
        print(
            f"| {markdown_escape(task.get('friendly_id'))} | "
            f"{markdown_escape(task.get('status'))} | "
            f"{markdown_escape(task.get('priority'))} | "
            f"{markdown_escape(task.get('due_date'))} | "
            f"{markdown_escape(compact(task.get('title'), 80))} |"
        )
        desc = plain_text_description(task.get("description"))
        if desc:
            print(f"> {textwrap.shorten(desc, width=110, placeholder='…')}")
    print(f"\nShowing **{len(rows)}** of **{len(tasks)}** task(s).")


def print_task_card(task):
    title = markdown_escape(task.get("title"))
    friendly_id = markdown_escape(task.get("friendly_id"))
    raw_id = markdown_escape(task.get("id"))
    status = markdown_escape(task.get("status"))
    priority = markdown_escape(task.get("priority"))
    start_date = markdown_escape(task.get("start_date"))
    due_date = markdown_escape(task.get("due_date"))
    owner = task.get("owner") or {}
    assigned_to = task.get("assigned_to") or {}
    owner_name = markdown_escape(owner.get("name"))
    assigned_name = markdown_escape(assigned_to.get("name"))
    description = plain_text_description(task.get("description"))
    preview = description_preview(task.get("description"), width=220)
    progress = task.get("progress")
    manday = task.get("manday")
    point = task.get("point")
    parent_id = task.get("parent_task_id")
    sprint_id = task.get("sprint_id")
    milestone_id = task.get("milestone_id")
    project_id = task.get("project_id")

    print(f"# {title}")
    print()
    print(f"- **ID:** `{friendly_id}`")
    print(f"- **Raw ID:** `{raw_id}`")
    print(f"- **Status:** `{status}`")
    print(f"- **Priority:** `{priority}`")
    print(f"- **Start Date:** `{start_date}`")
    print(f"- **Due Date:** `{due_date}`")
    print(f"- **Owner:** {owner_name}")
    print(f"- **Assigned To:** {assigned_name}")
    if progress is not None:
        print(f"- **Progress:** `{progress}%`")
    if manday is not None:
        print(f"- **Manday:** `{manday}`")
    if point is not None:
        print(f"- **Points:** `{point}`")
    if project_id:
        print(f"- **Project ID:** `{project_id}`")
    if parent_id:
        print(f"- **Parent Task:** `{parent_id}`")
    if sprint_id:
        print(f"- **Sprint:** `{sprint_id}`")
    if milestone_id:
        print(f"- **Milestone:** `{milestone_id}`")
    if preview:
        print(f"- **Preview:** {markdown_escape(preview)}")

    blocked_by = task.get("blocked_by") or []
    attachments = task.get("attachments") or []

    print()
    print("## Details")
    print()
    print(description if description else "_No description_")

    print()
    print("## Metadata")
    print()
    print(f"- **Created At:** `{markdown_escape(task.get('created_at'))}`")
    print(f"- **Updated At:** `{markdown_escape(task.get('updated_at'))}`")
    print(f"- **All Day:** `{markdown_escape(task.get('is_all_day'))}`")
    print(f"- **Attachments:** `{len(attachments)}`")
    print(f"- **Blocked By:** `{len(blocked_by)}`")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_users(config, args):
    users = authed_request(config, "GET", "/users")
    if args.raw:
        json.dump(users, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    rows = users or []
    if not rows:
        print("No users found.")
        return
    if args.search:
        kw = args.search.lower()
        rows = [
            u for u in rows
            if kw in (u.get("first_name") or "").lower()
            or kw in (u.get("last_name") or "").lower()
            or kw in (u.get("nickname") or "").lower()
            or kw in (u.get("email") or "").lower()
        ]
    print("| ID | Name | Nickname | Email |")
    print("| --- | --- | --- | --- |")
    for u in rows:
        full_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        print(
            f"| {markdown_escape(u.get('id'))} | "
            f"{markdown_escape(full_name)} | "
            f"{markdown_escape(u.get('nickname'))} | "
            f"{markdown_escape(u.get('email'))} |"
        )
    print(f"\nShowing **{len(rows)}** user(s).")


def cmd_get_project(config, args):
    project = authed_request(config, "GET", f"/projects/{args.id}")
    if args.raw:
        json.dump(project, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    p = project or {}
    print(f"# {p.get('name', '-')}")
    print()
    print(f"- **ID:** `{markdown_escape(p.get('id'))}`")
    print(f"- **Friendly ID:** `{markdown_escape(p.get('friendly_id'))}`")
    print(f"- **Status:** `{markdown_escape(p.get('status'))}`")
    print(f"- **Priority:** `{markdown_escape(p.get('priority'))}`")
    print(f"- **Start Date:** `{markdown_escape(p.get('start_date'))}`")
    print(f"- **End Date:** `{markdown_escape(p.get('end_date'))}`")
    print(f"- **Budget:** `{markdown_escape(p.get('budget'))}`")
    members = p.get("member_ids") or []
    print(f"- **Members:** `{len(members)}`")
    milestones = p.get("milestones") or []
    if milestones:
        print()
        print("## Milestones")
        for m in milestones:
            print(f"- `{m.get('id')}` {m.get('name')} — {m.get('status')} (due: {m.get('due_date', '-')})")
    desc = plain_text_description(p.get("description"))
    if desc:
        print()
        print("## Description")
        print(desc)


def cmd_projects(config, args):
    query = {}
    if args.search:
        query["search"] = args.search
    if args.status:
        query["status"] = args.status
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    projects = authed_request(config, "GET", f"/projects{suffix}")
    if args.raw:
        json.dump(projects, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    rows = projects or []
    if not rows:
        print("No projects found.")
        return
    print("| ID | Friendly ID | Status | Name |")
    print("| --- | --- | --- | --- |")
    for p in rows:
        print(
            f"| {markdown_escape(p.get('id'))} | "
            f"{markdown_escape(p.get('friendly_id'))} | "
            f"{markdown_escape(p.get('status'))} | "
            f"{markdown_escape(compact(p.get('name'), 80))} |"
        )
    print(f"\nShowing **{len(rows)}** project(s).")


def cmd_list(config, args):
    query = {}
    if args.search:
        query["search"] = args.search
    if args.status:
        query["status"] = args.status
    if args.project_id:
        query["project_id"] = args.project_id
    if args.assignee:
        query["assignees"] = args.assignee
    if args.parent_id:
        query["parent_task_id"] = args.parent_id
    if args.due_filter:
        query["due_date_filter"] = args.due_filter
    if args.due_start:
        query["due_date_start"] = args.due_start
    if args.due_end:
        query["due_date_end"] = args.due_end
    if args.limit:
        query["limit"] = str(args.limit)
    if args.page:
        query["page"] = str(args.page)
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    tasks = authed_request(config, "GET", f"/tasks{suffix}")
    if args.raw:
        json.dump(tasks, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    if args.format == "table":
        print_task_table(tasks, args.limit)
        return
    print_task_markdown(tasks, args.limit)


def cmd_get(config, args):
    task = resolve_task(config, args.id)
    if args.raw:
        json.dump(task, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print_task_card(task)


def _parse_assigned_to(value):
    """Parse 'id:type:name' or JSON string into AssignedTo dict."""
    if not value:
        return None
    value = value.strip()
    if value.startswith("{"):
        return json.loads(value)
    parts = value.split(":", 2)
    if len(parts) == 3:
        return {"id": parts[0], "type": parts[1], "name": parts[2]}
    if len(parts) == 2:
        return {"id": parts[0], "type": "user", "name": parts[1]}
    return {"id": parts[0], "type": "user", "name": parts[0]}


def cmd_create(config, args):
    payload = {"title": args.title, "status": args.status}
    optional_str = [
        ("description", args.description),
        ("priority", args.priority),
        ("due_date", args.due_date),
        ("start_date", args.start_date),
        ("due_time", args.due_time),
        ("start_time", args.start_time),
        ("project_id", args.project_id),
        ("parent_task_id", args.parent_id),
        ("sprint_id", args.sprint_id),
        ("milestone_id", args.milestone_id),
        ("notes", args.notes),
    ]
    for key, val in optional_str:
        if val is not None:
            payload[key] = val
    if args.manday is not None:
        payload["manday"] = args.manday
    if args.point is not None:
        payload["point"] = args.point
    if args.progress is not None:
        payload["progress"] = args.progress
    if args.assigned_to:
        payload["assigned_to"] = _parse_assigned_to(args.assigned_to)
    task = authed_request(config, "POST", "/tasks", payload)
    json.dump(task, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_update(config, args):
    payload = {}
    optional_str = [
        ("title", args.title),
        ("description", args.description),
        ("status", args.status),
        ("priority", args.priority),
        ("due_date", args.due_date),
        ("start_date", args.start_date),
        ("due_time", args.due_time),
        ("start_time", args.start_time),
        ("notes", args.notes),
        ("sprint_id", args.sprint_id),
        ("milestone_id", args.milestone_id),
    ]
    for key, val in optional_str:
        if val is not None:
            payload[key] = val
    if args.manday is not None:
        payload["manday"] = args.manday
    if args.point is not None:
        payload["point"] = args.point
    if args.progress is not None:
        payload["progress"] = args.progress
    if args.assigned_to:
        payload["assigned_to"] = _parse_assigned_to(args.assigned_to)
    if not payload:
        raise SystemExit("Nothing to update")
    task = resolve_task(config, args.id)
    raw_id = normalize_id(task.get("id"))
    if not raw_id:
        raise SystemExit(f"Resolved task is missing raw id: {args.id}")
    result = authed_request(config, "PUT", f"/tasks/{raw_id}", payload)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_stats(config, args):
    query = {}
    if args.project_id:
        query["project_id"] = args.project_id
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    stats = authed_request(config, "GET", f"/tasks/stats{suffix}")
    json.dump(stats, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_subtasks(config, args):
    tasks = authed_request(
        config, "GET",
        f"/tasks?{urllib.parse.urlencode({'parent_task_id': args.id})}",
    )
    if args.raw:
        json.dump(tasks, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print_task_markdown(tasks, None)


def cmd_delete(config, args):
    task = resolve_task(config, args.id)
    raw_id = normalize_id(task.get("id"))
    authed_request(config, "DELETE", f"/tasks/{raw_id}")
    print(f"Deleted: {args.id}")


# ---------------------------------------------------------------------------
# Milestone commands
# ---------------------------------------------------------------------------

def print_milestone_table(milestones):
    rows = milestones or []
    if not rows:
        print("No milestones found.")
        return
    print("| ID | Status | Progress | Due | Title |")
    print("| --- | --- | --- | --- | --- |")
    for m in rows:
        progress = f"{m.get('progress', 0)}%"
        print(
            f"| {markdown_escape(m.get('id'))} | "
            f"{markdown_escape(m.get('status'))} | "
            f"{markdown_escape(progress)} | "
            f"{markdown_escape(m.get('due_date'))} | "
            f"{markdown_escape(compact(m.get('title'), 80))} |"
        )
    print(f"\nShowing **{len(rows)}** milestone(s).")


def cmd_milestone_list(config, args):
    query = {}
    if args.status:
        query["status"] = args.status
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    ms = authed_request(config, "GET", f"/projects/{args.project_id}/milestones{suffix}")
    if args.raw:
        json.dump(ms, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print_milestone_table(ms)


def cmd_milestone_get(config, args):
    m = authed_request(config, "GET", f"/projects/{args.project_id}/milestones/{args.id}")
    if args.raw:
        json.dump(m, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print(f"# {m.get('title', '-')}")
    print(f"- **ID:** `{markdown_escape(m.get('id'))}`")
    print(f"- **Status:** `{markdown_escape(m.get('status'))}`")
    print(f"- **Progress:** `{m.get('progress', 0)}%`")
    print(f"- **Start Date:** `{markdown_escape(m.get('start_date'))}`")
    print(f"- **Due Date:** `{markdown_escape(m.get('due_date'))}`")
    print(f"- **Tasks:** {m.get('done_task_count', 0)}/{m.get('task_count', 0)} done")
    if m.get('owner_id'):
        print(f"- **Owner:** `{markdown_escape(m.get('owner_id'))}`")
    if m.get('description'):
        print(f"- **Description:** {markdown_escape(m.get('description'))}")


def cmd_milestone_create(config, args):
    payload = {
        "title": args.title,
        "start_date": args.start_date,
        "due_date": args.due_date,
    }
    for key, val in [("description", args.description), ("owner_id", args.owner_id), ("color", args.color)]:
        if val is not None:
            payload[key] = val
    if args.display_order is not None:
        payload["display_order"] = args.display_order
    m = authed_request(config, "POST", f"/projects/{args.project_id}/milestones", payload)
    json.dump(m, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_milestone_update(config, args):
    payload = {}
    for key, val in [
        ("title", args.title), ("description", args.description),
        ("status", args.status), ("start_date", args.start_date),
        ("due_date", args.due_date), ("owner_id", args.owner_id), ("color", args.color),
    ]:
        if val is not None:
            payload[key] = val
    if args.progress is not None:
        payload["progress"] = args.progress
    if args.display_order is not None:
        payload["display_order"] = args.display_order
    if not payload:
        raise SystemExit("Nothing to update")
    m = authed_request(config, "PATCH", f"/projects/{args.project_id}/milestones/{args.id}", payload)
    json.dump(m, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_milestone_recalc(config, args):
    result = authed_request(config, "POST", f"/projects/{args.project_id}/milestones/{args.id}/recalculate")
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_milestone_delete(config, args):
    authed_request(config, "DELETE", f"/projects/{args.project_id}/milestones/{args.id}")
    print(f"Deleted milestone: {args.id}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_task_fields(parser, include_title=False, required_title=False):
    """Shared task field arguments for create and update."""
    if include_title:
        parser.add_argument("--title", required=required_title)
    parser.add_argument("--description")
    parser.add_argument("--status", help="backlog | todo | in_progress | in_review | done | cancelled")
    parser.add_argument("--priority", help="low | medium | high | urgent")
    parser.add_argument("--start-date", dest="start_date", metavar="YYYY-MM-DD")
    parser.add_argument("--due-date", dest="due_date", metavar="YYYY-MM-DD")
    parser.add_argument("--start-time", dest="start_time", metavar="HH:mm")
    parser.add_argument("--due-time", dest="due_time", metavar="HH:mm")
    parser.add_argument("--project-id", dest="project_id")
    parser.add_argument("--parent-id", dest="parent_id", metavar="TASK_ID")
    parser.add_argument("--sprint-id", dest="sprint_id")
    parser.add_argument("--milestone-id", dest="milestone_id")
    parser.add_argument("--assigned-to", dest="assigned_to",
                        help="Format: id:type:name  or  id:name  or  JSON")
    parser.add_argument("--manday", type=float)
    parser.add_argument("--point", type=float)
    parser.add_argument("--progress", type=int, metavar="0-100")
    parser.add_argument("--notes")


def build_parser():
    parser = argparse.ArgumentParser(description="klive-tasks API helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # k-users
    up2 = subparsers.add_parser("k-users", help="List users")
    up2.add_argument("--search", help="Filter by name, nickname, or email")
    up2.add_argument("--raw", action="store_true")
    up2.set_defaults(func=cmd_users)

    # k-projects
    pp = subparsers.add_parser("k-projects", help="List projects")
    pp.add_argument("--search")
    pp.add_argument("--status", help="planning | active | on_hold | completed | cancelled")
    pp.add_argument("--raw", action="store_true")
    pp.set_defaults(func=cmd_projects)

    # k-get-project
    gpp = subparsers.add_parser("k-get-project", help="Get project detail by id")
    gpp.add_argument("--id", required=True)
    gpp.add_argument("--raw", action="store_true")
    gpp.set_defaults(func=cmd_get_project)

    # k-list
    lp = subparsers.add_parser("k-list", help="List / search tasks")
    lp.add_argument("--search")
    lp.add_argument("--status")
    lp.add_argument("--project-id", dest="project_id")
    lp.add_argument("--assignee", metavar="USER_ID")
    lp.add_argument("--parent-id", dest="parent_id", metavar="TASK_ID")
    lp.add_argument("--due-filter", dest="due_filter",
                    help="Today | This Week | This Month | Overdue | Next Week")
    lp.add_argument("--due-start", dest="due_start", metavar="YYYY-MM-DD")
    lp.add_argument("--due-end", dest="due_end", metavar="YYYY-MM-DD")
    lp.add_argument("--limit", type=int, default=20)
    lp.add_argument("--page", type=int)
    lp.add_argument("--format", choices=("markdown", "table"), default="markdown")
    lp.add_argument("--raw", action="store_true")
    lp.set_defaults(func=cmd_list)

    # k-get
    gp = subparsers.add_parser("k-get", help="Get task detail by id or friendly id")
    gp.add_argument("--id", required=True)
    gp.add_argument("--raw", action="store_true")
    gp.set_defaults(func=cmd_get)

    # k-subtasks
    sp = subparsers.add_parser("k-subtasks", help="List subtasks of a parent task")
    sp.add_argument("--id", required=True, metavar="PARENT_ID")
    sp.add_argument("--raw", action="store_true")
    sp.set_defaults(func=cmd_subtasks)

    # k-create
    cp = subparsers.add_parser("k-create", help="Create a task")
    _add_task_fields(cp, include_title=True, required_title=True)
    cp.set_defaults(func=cmd_create, status="todo")

    # k-update
    up = subparsers.add_parser("k-update", help="Update a task")
    up.add_argument("--id", required=True)
    _add_task_fields(up, include_title=True)
    up.set_defaults(func=cmd_update)

    # k-delete
    dp = subparsers.add_parser("k-delete", help="Delete (soft) a task")
    dp.add_argument("--id", required=True)
    dp.set_defaults(func=cmd_delete)

    # k-stats
    stp = subparsers.add_parser("k-stats", help="Get task stats")
    stp.add_argument("--project-id", dest="project_id")
    stp.set_defaults(func=cmd_stats)

    # k-milestone-list
    ml = subparsers.add_parser("k-milestone-list", help="List milestones for a project")
    ml.add_argument("--project-id", dest="project_id", required=True)
    ml.add_argument("--status", help="upcoming | active | done | overdue")
    ml.add_argument("--raw", action="store_true")
    ml.set_defaults(func=cmd_milestone_list)

    # k-milestone-get
    mg = subparsers.add_parser("k-milestone-get", help="Get milestone detail")
    mg.add_argument("--project-id", dest="project_id", required=True)
    mg.add_argument("--id", required=True)
    mg.add_argument("--raw", action="store_true")
    mg.set_defaults(func=cmd_milestone_get)

    # k-milestone-create
    mc = subparsers.add_parser("k-milestone-create", help="Create a milestone")
    mc.add_argument("--project-id", dest="project_id", required=True)
    mc.add_argument("--title", required=True)
    mc.add_argument("--start-date", dest="start_date", required=True, metavar="YYYY-MM-DD")
    mc.add_argument("--due-date", dest="due_date", required=True, metavar="YYYY-MM-DD")
    mc.add_argument("--description")
    mc.add_argument("--owner-id", dest="owner_id")
    mc.add_argument("--color", metavar="#HEX")
    mc.add_argument("--display-order", dest="display_order", type=int)
    mc.set_defaults(func=cmd_milestone_create)

    # k-milestone-update
    mu = subparsers.add_parser("k-milestone-update", help="Update a milestone")
    mu.add_argument("--project-id", dest="project_id", required=True)
    mu.add_argument("--id", required=True)
    mu.add_argument("--title")
    mu.add_argument("--description")
    mu.add_argument("--status", help="upcoming | active | done | overdue")
    mu.add_argument("--start-date", dest="start_date", metavar="YYYY-MM-DD")
    mu.add_argument("--due-date", dest="due_date", metavar="YYYY-MM-DD")
    mu.add_argument("--progress", type=int, metavar="0-100")
    mu.add_argument("--owner-id", dest="owner_id")
    mu.add_argument("--color", metavar="#HEX")
    mu.add_argument("--display-order", dest="display_order", type=int)
    mu.set_defaults(func=cmd_milestone_update)

    # k-milestone-recalc
    mr = subparsers.add_parser("k-milestone-recalc", help="Recalculate progress from tasks")
    mr.add_argument("--project-id", dest="project_id", required=True)
    mr.add_argument("--id", required=True)
    mr.set_defaults(func=cmd_milestone_recalc)

    # k-milestone-delete
    md = subparsers.add_parser("k-milestone-delete", help="Delete a milestone")
    md.add_argument("--project-id", dest="project_id", required=True)
    md.add_argument("--id", required=True)
    md.set_defaults(func=cmd_milestone_delete)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    config = env_config()
    args.func(config, args)


if __name__ == "__main__":
    main()
