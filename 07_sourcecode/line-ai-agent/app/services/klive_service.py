"""
Wraps the bundled klive_tasks_api.py CLI (the official dh-task client) as a
subprocess, plus a couple of small caches so we never have to show raw IDs
to the user and can resolve "myself" to a real dh-task account.
"""
import os
import json
import time

from app import config

# Subcommands whose text output the klive-tasks CLI can render as raw JSON
# via `--raw`. We always force this flag on for these so we get structured
# data back — both for Gemini to reason over and for building Flex Messages.
RAW_CAPABLE_SUBCOMMANDS = {
    "k-users", "k-projects", "k-get-project", "k-list", "k-get",
    "k-subtasks", "k-milestone-list", "k-milestone-get",
}


def run_klive(command_args: list[str]) -> str:
    """Low-level: runs klive_tasks_api.py as a subprocess and returns raw stdout/error text."""
    import subprocess

    env = os.environ.copy()
    env["KLIVE_API_URL"] = config.KLIVE_API_URL
    env["KLIVE_TASKS_API_URL"] = config.KLIVE_TASKS_API_URL
    env["KLIVE_API_TOKEN"] = config.KLIVE_API_TOKEN

    # Bundled inside the repo (tools/klive_tasks_api.py) so this also works
    # on a cloud host where ~/tools/ doesn't exist. Falls back to ~/tools/
    # for backward compatibility with older local setups.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bundled_path = os.path.join(repo_root, "tools", "klive_tasks_api.py")
    legacy_path = os.path.expanduser("~/tools/klive_tasks_api.py")
    script_path = bundled_path if os.path.exists(bundled_path) else legacy_path
    if not os.path.exists(script_path):
        return "Error: klive_tasks_api.py script not found (checked tools/ and ~/tools/)."

    cmd = ["python3", script_path] + command_args
    try:
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        return f"Error executing command: {result.stderr or result.stdout}"
    except Exception as e:
        return f"Exception occurred while running command: {str(e)}"


# --- Name resolution cache (so we never have to show a raw user id) ---
_USER_CACHE = {"map": {}, "ts": 0.0}
_USER_CACHE_TTL_SECONDS = 600


def resolve_user_name(user_id: str) -> str:
    """Turns a bare user id into 'First Last' using a cached k-users --raw lookup.
    Falls back to the raw id if the user can't be found or the lookup fails."""
    if not user_id:
        return "ยังไม่ระบุ"
    now = time.time()
    if now - _USER_CACHE["ts"] > _USER_CACHE_TTL_SECONDS:
        try:
            raw = run_klive(["k-users", "--raw"])
            users = json.loads(raw)
            name_map = {}
            for u in users or []:
                full_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                name_map[str(u.get("id"))] = full_name or u.get("nickname") or str(u.get("id"))
            _USER_CACHE["map"] = name_map
            _USER_CACHE["ts"] = now
        except Exception as e:
            print(f"⚠️ Could not refresh user cache: {e}")
    return _USER_CACHE["map"].get(str(user_id), user_id)


# --- Self-identity resolution ---
# When the LINE user refers to themselves ("ของฉัน", "ผม", "ฉัน", "ตัวเอง"),
# we resolve that to this specific dh-task account rather than letting
# Gemini guess a user_id.
_SELF_CACHE = {"id": None, "ts": 0.0}
_SELF_CACHE_TTL_SECONDS = 3600


def resolve_self_user_id() -> str | None:
    now = time.time()
    if _SELF_CACHE["id"] and now - _SELF_CACHE["ts"] < _SELF_CACHE_TTL_SECONDS:
        return _SELF_CACHE["id"]
    try:
        # Deliberately NOT passing --search here. tools/klive_tasks_api.py's
        # cmd_users() checks `if args.raw: dump everything; return` BEFORE it
        # ever applies the --search filter — so "k-users --search X --raw"
        # silently ignores --search entirely and returns the FULL unfiltered
        # user list, and `users[0]` ends up being whichever user happens to
        # be first in that list, not the one matching SELF_EMAIL. This was a
        # real, confirmed bug: self-identity was silently resolving to the
        # wrong dh-task account, so both "my tasks" (--assignee) and "my
        # projects" (PM_ROLE_ID) queries were checking against someone
        # else's user_id the entire time. Filtering by email ourselves here
        # avoids depending on that upstream CLI behavior at all.
        raw = run_klive(["k-users", "--raw"])
        users = json.loads(raw)
        target_email = (config.SELF_EMAIL or "").strip().lower()
        match = next(
            (u for u in users if (u.get("email") or "").strip().lower() == target_email),
            None,
        ) if target_email else None
        if match:
            _SELF_CACHE["id"] = str(match.get("id"))
            _SELF_CACHE["ts"] = now
        else:
            print(f"⚠️ No dh-task user found with email {config.SELF_EMAIL!r} among {len(users)} users")
    except Exception as e:
        print(f"⚠️ Could not resolve self user id ({config.SELF_EMAIL}): {e}")
    return _SELF_CACHE["id"]


# --- PM-project filter ---
# A dh-task project's `member_roles` field is {user_id: [role_id, ...]} — the
# bundled CLI/SKILL.md has no reference endpoint that maps role_id -> role
# name, so PM_ROLE_ID below was reverse-engineered from real production data:
# fetched via the temporary /debug/klive-raw endpoint, this role_id appeared
# alongside the resolved self_user_id in exactly 7 projects, matching the
# user's own independently-stated fact of being PM on 7 projects. Further
# corroborated by k-users showing the self account's last_name is literally
# "PM" in dh-task. Not yet double-checked against a dedicated roles-reference
# endpoint (none exists in the documented CLI), but the cross-check above
# gives high confidence.
PM_ROLE_ID = "698e8b929c2fe89eb6722fea"


def list_my_managed_projects() -> list[dict]:
    """Projects where the self-identity account (config.SELF_EMAIL) holds the
    PM role per member_roles. Also merges each project's milestones in
    (fetched separately via k-milestone-list) since k-projects --raw always
    returns "milestones": [] even when milestone_count is nonzero — the list
    endpoint just doesn't embed them, so flex_builder has nothing to render
    unless we fetch and attach them here first."""
    self_id = resolve_self_user_id()
    print(f"🔍 list_my_managed_projects: resolved self_id={self_id!r} (SELF_EMAIL={config.SELF_EMAIL!r})")
    if not self_id:
        return []

    raw = run_klive(["k-projects", "--raw"])
    try:
        projects = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"⚠️ Could not parse k-projects --raw output ({e}); raw preview: {raw[:200]!r}")
        return []
    if not isinstance(projects, list):
        print(f"⚠️ k-projects --raw returned a non-list ({type(projects)}), preview: {str(projects)[:200]!r}")
        return []
    print(f"🔍 list_my_managed_projects: fetched {len(projects)} total projects")

    mine = [
        p for p in projects
        if isinstance(p, dict) and PM_ROLE_ID in (p.get("member_roles") or {}).get(self_id, [])
    ]
    print(f"🔍 list_my_managed_projects: {len(mine)} matched PM_ROLE_ID for self_id={self_id!r}")

    # Fetch each matched project's milestones concurrently rather than one
    # subprocess call after another — with several PM projects this could
    # otherwise add up to enough latency to risk the LINE reply token
    # expiring before the reply is ever sent.
    import concurrent.futures

    def _fetch_milestones(project_id: str):
        try:
            m_raw = run_klive(["k-milestone-list", "--project-id", project_id, "--raw"])
            milestones = json.loads(m_raw)
            return milestones if isinstance(milestones, list) else None
        except Exception as e:
            print(f"⚠️ Could not fetch milestones for project {project_id!r}: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(mine))) as pool:
        futures = {
            pool.submit(_fetch_milestones, p["id"]): p
            for p in mine if p.get("id")
        }
        for future in concurrent.futures.as_completed(futures):
            milestones = future.result()
            if milestones is not None:
                futures[future]["milestones"] = milestones

    return mine


# --- PM dashboard (single project) ---
# Feeds flex_builder.build_project_dashboard_bubble — a richer "Detail" view
# modeled after dh-task's own web Overview tab, reached by tapping the
# "ดูรายละเอียดเพิ่มเติม" footer button on a project card.
_DASHBOARD_TASK_LIMIT = 200  # generous cap for member-workload/status tallying; dh-task doesn't document a hard max


def get_project_dashboard(project_id: str) -> dict | None:
    """Fetches everything one project's dashboard needs in one shot, running
    the independent subprocess calls concurrently (this is 5 separate calls
    to tools/klive_tasks_api.py, each a real network round trip — sequential
    would risk the LINE reply token expiring, same reasoning as the
    concurrent milestone fetch in list_my_managed_projects).

    Returns None if the project itself can't be fetched (bad id); the other
    four pieces (milestones/tasks/stats/overdue/due-this-week) degrade to
    empty individually on failure rather than failing the whole dashboard."""
    import concurrent.futures

    def _get_project():
        raw = run_klive(["k-get-project", "--id", project_id, "--raw"])
        data = json.loads(raw)
        return data if isinstance(data, dict) else None

    def _get_milestones():
        raw = run_klive(["k-milestone-list", "--project-id", project_id, "--raw"])
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _get_tasks():
        raw = run_klive(["k-list", "--project-id", project_id, "--limit", str(_DASHBOARD_TASK_LIMIT), "--raw"])
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _get_stats():
        # k-stats' argparse subparser (tools/klive_tasks_api.py) never adds a
        # --raw flag at all — cmd_stats() always dumps raw JSON unconditionally,
        # unlike k-list/k-projects/etc. Passing --raw here makes argparse
        # reject the whole command ("unrecognized arguments"), which run_klive
        # then reports back as a plain "Error executing command: ..." string —
        # non-JSON, so json.loads() blows up with a generic "Expecting value"
        # error that silently degrades to an empty stats dict via the
        # try/except below. Confirmed via real Render logs: this was firing
        # on every dashboard fetch, always right when the status-breakdown
        # section came up empty.
        raw = run_klive(["k-stats", "--project-id", project_id])
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _get_overdue():
        raw = run_klive(["k-list", "--project-id", project_id, "--due-filter", "Overdue", "--limit", str(_DASHBOARD_TASK_LIMIT), "--raw"])
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _get_due_this_week():
        raw = run_klive(["k-list", "--project-id", project_id, "--due-filter", "This Week", "--limit", str(_DASHBOARD_TASK_LIMIT), "--raw"])
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    fetchers = {
        "project": _get_project,
        "milestones": _get_milestones,
        "tasks": _get_tasks,
        "stats": _get_stats,
        "overdue": _get_overdue,
        "due_this_week": _get_due_this_week,
    }
    defaults = {"milestones": [], "tasks": [], "stats": {}, "overdue": [], "due_this_week": []}
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fetchers)) as pool:
        futures = {pool.submit(fn): key for key, fn in fetchers.items()}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"⚠️ get_project_dashboard: fetching {key!r} failed for project {project_id!r}: {e}")
                results[key] = defaults.get(key)

    if not results.get("project"):
        print(f"⚠️ get_project_dashboard: could not fetch project {project_id!r}, aborting dashboard")
        return None
    return results
