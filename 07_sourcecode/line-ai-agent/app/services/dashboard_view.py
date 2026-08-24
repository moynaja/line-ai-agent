"""
Turns the raw dict from klive_service.get_project_dashboard() into a clean,
already-computed JSON structure for the full-screen web dashboard
(liff/project/index.html, served via /api/project-dashboard/{id}).

Deliberately reuses flex_builder's status label/color tables and a few of
its private (underscore-prefixed) computation helpers — _fmt_date,
_effective_milestone_progress, _days_to_next_milestone, _person_name —
rather than re-implementing them here. Those functions are about the *data*
(what "on track" means, how a stale "progress" field gets papered over,
what a date string should look like) not about LINE's Flex box format, so
the web page needs the exact same numbers the Flex dashboard card shows.
Duplicating that logic in a second place would just be a second place for
the two views to quietly disagree.
"""
import flex_builder as fb


def _project_summary(project, milestones, tasks, overdue):
    friendly_id = fb._s(project.get("friendly_id") or project.get("id"))
    name = fb._s(project.get("name"))
    status = project.get("status") or ""
    status_label = fb.PROJECT_STATUS_TH.get(status, status or "-")
    status_color = fb.PROJECT_STATUS_COLOR.get(status, fb.MUTED_COLOR)

    task_count = project.get("task_count")
    if task_count is None:
        task_count = len(tasks)
    done_task_count = project.get("done_task_count")
    if done_task_count is None:
        done_task_count = sum(1 for t in tasks if t.get("status") == "done")
    overall_progress = round(100 * done_task_count / task_count) if task_count else 0

    on_track = len(overdue) == 0
    badge_text = "✅ ตรงตามแผน" if on_track else f"⚠️ มีงานเลยกำหนด {len(overdue)} รายการ"

    next_milestone_text = None
    next_ms = fb._days_to_next_milestone(milestones)
    if next_ms:
        days, m = next_ms
        ms_name = fb._s(m.get("name") or m.get("title"))
        if days < 0:
            next_milestone_text = f"🎯 {ms_name} เลยกำหนดมาแล้ว {abs(days)} วัน"
        elif days == 0:
            next_milestone_text = f"🎯 {ms_name} ครบกำหนดวันนี้"
        else:
            next_milestone_text = f"🎯 {ms_name} อีก {days} วัน"

    return {
        "friendly_id": friendly_id,
        "name": name,
        "status_label": status_label,
        "status_color": status_color,
        "start_date": fb._fmt_date(project.get("start_date")),
        "end_date": fb._fmt_date(project.get("end_date")),
        "member_count": len(project.get("member_ids") or []),
        "description": fb._s(project.get("description"), ""),
        "overall_progress": overall_progress,
        "on_track": on_track,
        "badge_text": badge_text,
        "next_milestone_text": next_milestone_text,
    }


def _status_breakdown(stats):
    if not isinstance(stats, dict):
        return []
    out = []
    for status in fb._STATUS_ORDER:
        count = int(stats.get(status) or 0)
        if count > 0:
            out.append({
                "status": status,
                "label": fb.TASK_STATUS_TH.get(status, status),
                "color": fb.TASK_STATUS_COLOR.get(status, fb.MUTED_COLOR),
                "count": count,
            })
    return out


def _workload(tasks, resolve_user, top_n=8):
    """Same grouping as flex_builder._member_workload_rows, but returns
    plain data instead of Flex boxes (that function renders straight to a
    capped top_n=5 list of Flex row dicts, which isn't reusable JSON —
    only the grouping logic is shared, via the same bucket/sort approach)."""
    buckets = {}
    for t in tasks or []:
        status = t.get("status") or ""
        if status == "cancelled":
            continue
        assigned = t.get("assigned_to")
        if not assigned:
            continue
        if isinstance(assigned, dict):
            uid = assigned.get("id")
            embedded_name = assigned.get("name") or assigned.get("nickname")
        else:
            uid = assigned
            embedded_name = None
        if not uid:
            continue
        b = buckets.setdefault(uid, {"done": 0, "active": 0, "pending": 0, "name": None})
        if embedded_name and not b["name"]:
            b["name"] = embedded_name
        if status == "done":
            b["done"] += 1
        elif status in ("in_progress", "in_review"):
            b["active"] += 1
        elif status in ("backlog", "todo"):
            b["pending"] += 1

    entries = []
    for uid, b in buckets.items():
        total = b["done"] + b["active"] + b["pending"]
        if total <= 0:
            continue
        name = b["name"] or (resolve_user(uid) if resolve_user else None) or uid
        pct = round(100 * b["done"] / total) if total else 0
        entries.append({
            "name": fb._s(name), "done": b["done"], "active": b["active"],
            "pending": b["pending"], "total": total, "pct": pct,
        })
    entries.sort(key=lambda e: e["total"], reverse=True)
    return entries[:top_n]


def _milestone_list(milestones):
    out = []
    for m in milestones:
        status = m.get("status") or ""
        out.append({
            "name": fb._s(m.get("name") or m.get("title")),
            "status_label": fb.MILESTONE_STATUS_TH.get(status, status or "-"),
            "color": fb.MILESTONE_STATUS_COLOR.get(status, fb.MUTED_COLOR),
            "progress": fb._effective_milestone_progress(m),
            "due_date": fb._fmt_date(m.get("due_date")),
        })
    return out


def _task_list(tasks, resolve_user):
    out = []
    for t in tasks:
        status = t.get("status") or ""
        out.append({
            "title": fb._s(t.get("title")),
            "due_date": fb._fmt_date(t.get("due_date")),
            "status_label": fb.TASK_STATUS_TH.get(status, status or "-"),
            "color": fb.TASK_STATUS_COLOR.get(status, fb.MUTED_COLOR),
            "assignee": fb._person_name(t.get("assigned_to"), resolve_user),
        })
    return out


def build_dashboard_view(dashboard: dict, resolve_user=None) -> dict:
    """dashboard is the dict returned by klive_service.get_project_dashboard()
    (project, milestones, tasks, stats, overdue, due_this_week). Returns a
    plain-JSON-serializable dict ready to hand straight to the frontend —
    every date already formatted, every status already translated/colored,
    nothing left for liff/project/index.html to compute beyond templating."""
    project = dashboard.get("project") or {}
    milestones = dashboard.get("milestones") or []
    tasks = dashboard.get("tasks") or []
    stats = dashboard.get("stats") or {}
    overdue = dashboard.get("overdue") or []
    due_this_week = dashboard.get("due_this_week") or []

    task_count = project.get("task_count")
    if task_count is None:
        task_count = len(tasks)
    done_task_count = project.get("done_task_count")
    if done_task_count is None:
        done_task_count = sum(1 for t in tasks if t.get("status") == "done")

    return {
        "project": _project_summary(project, milestones, tasks, overdue),
        "stats": {
            "task_total": int(task_count or 0),
            "task_done": int(done_task_count or 0),
            "milestone_total": len(milestones),
            "milestone_done": sum(1 for m in milestones if m.get("status") == "done"),
            "pending": int((stats.get("backlog") or 0) + (stats.get("todo") or 0)),
            "overdue_count": len(overdue),
        },
        "status_breakdown": _status_breakdown(stats),
        "workload": _workload(tasks, resolve_user),
        "milestones": _milestone_list(milestones),
        "overdue_tasks": _task_list(overdue, resolve_user),
        "due_this_week_tasks": _task_list(due_this_week, resolve_user),
    }
