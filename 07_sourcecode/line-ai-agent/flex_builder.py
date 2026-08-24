"""
Builds LINE Flex Message payloads (plain dicts) from klive-tasks JSON data
(tasks, projects, milestones, stats). Pure formatting only — no network or
subprocess calls happen in this module. Pass a `resolve_user` callback in if
you want raw user-id fields turned into display names; otherwise ids are
shown as-is.

Every public build_* function returns a dict: {"alt_text": str, "contents": <flex dict>}
ready to be handed to `FlexContainer.from_dict(result["contents"])` and wrapped
in a `FlexMessage(alt_text=..., contents=container)`.
"""
from app import config

MAX_CAROUSEL_ITEMS = 12  # LINE hard limit per carousel

TASK_STATUS_TH = {
    "backlog": "รอคิว",
    "todo": "ต้องทำ",
    "in_progress": "กำลังทำ",
    "in_review": "รอตรวจ",
    "done": "เสร็จแล้ว",
    "cancelled": "ยกเลิก",
}
TASK_STATUS_COLOR = {
    "backlog": "#9CA3AF",
    "todo": "#3B82F6",
    "in_progress": "#F59E0B",
    "in_review": "#8B5CF6",
    "done": "#10B981",
    "cancelled": "#EF4444",
}
PRIORITY_TH = {"low": "ต่ำ", "medium": "ปานกลาง", "high": "สูง", "urgent": "ด่วนมาก"}
PRIORITY_COLOR = {"low": "#9CA3AF", "medium": "#3B82F6", "high": "#F59E0B", "urgent": "#EF4444"}

# Projects use their own (differently-cased, "Critical" instead of "urgent")
# priority vocabulary compared to tasks — real data checked: "High",
# "Medium", "Low", "Critical", or "". Matched case-insensitively.
PROJECT_PRIORITY_TH = {"low": "ต่ำ", "medium": "ปานกลาง", "high": "สูง", "critical": "วิกฤต"}

PROJECT_STATUS_TH = {
    "planning": "วางแผน",
    "active": "กำลังดำเนินการ",
    "on_hold": "พักไว้",
    "completed": "เสร็จสิ้น",
    "cancelled": "ยกเลิก",
}
PROJECT_STATUS_COLOR = {
    "planning": "#6B7280",
    "active": "#10B981",
    "on_hold": "#F59E0B",
    "completed": "#3B82F6",
    "cancelled": "#EF4444",
}

MILESTONE_STATUS_TH = {"upcoming": "กำลังจะถึง", "active": "กำลังดำเนินการ", "done": "เสร็จแล้ว", "overdue": "เลยกำหนด"}
MILESTONE_STATUS_COLOR = {"upcoming": "#6B7280", "active": "#F59E0B", "done": "#10B981", "overdue": "#EF4444"}

BRAND_COLOR = "#06C755"
DOHOME_ORANGE = "#E8763D"
MUTED_COLOR = "#9CA3AF"
STATS_HEADER_COLOR = "#374151"

# Served by app/main.py's `/assets` static mount (see assets/dohome_badge.png).
# Override with PUBLIC_BASE_URL if this service ever moves off the default
# Render URL.
LOGO_URL = f"{config.PUBLIC_BASE_URL}/assets/dohome_badge.png"


def _s(value, fallback="-"):
    text = str(value).strip() if value is not None else ""
    return text if text else fallback


def _fmt_date(value):
    """2026-06-30 -> 30/06/2026. Falls back to the raw string on any other shape."""
    text = _s(value, "")
    if not text:
        return "-"
    parts = text.split("T")[0].split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        y, m, d = parts
        return f"{d}/{m}/{y}"
    return text


def _person_name(value, resolve_user=None):
    """Accepts an embedded {"name": ...} object, a bare user-id string, or None."""
    if not value:
        return "ยังไม่ระบุ"
    if isinstance(value, dict):
        name = value.get("name") or value.get("nickname")
        if name:
            return name
        user_id = value.get("id")
        if user_id and resolve_user:
            return resolve_user(user_id) or "ยังไม่ระบุ"
        return "ยังไม่ระบุ"
    if isinstance(value, str):
        if resolve_user:
            return resolve_user(value) or value
        return value
    return "ยังไม่ระบุ"


def _row(label, value_text, value_color=None, bold=False):
    value_span = {"type": "text", "text": _s(value_text), "size": "xs", "flex": 3, "wrap": True}
    if value_color:
        value_span["color"] = value_color
    if bold:
        value_span["weight"] = "bold"
    return {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type": "text", "text": label, "size": "xs", "color": MUTED_COLOR, "flex": 2},
            value_span,
        ],
    }


def _logo_icon(size="22px"):
    return {"type": "image", "url": LOGO_URL, "size": size, "aspectRatio": "1:1", "aspectMode": "fit", "flex": 0}


def _header_progress_bar(progress):
    """Light-on-dark progress bar meant to sit inside a colored header band."""
    try:
        progress = max(0, min(100, int(progress)))
    except (TypeError, ValueError):
        progress = 0
    track = []
    if progress > 0:
        track.append({"type": "box", "layout": "vertical", "flex": progress, "backgroundColor": "#FFFFFF", "contents": []})
    if progress < 100:
        track.append({"type": "box", "layout": "vertical", "flex": max(1, 100 - progress), "backgroundColor": "#E5E7EB", "contents": []})
    return {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "spacing": "xs",
        "contents": [
            {"type": "box", "layout": "horizontal", "height": "6px", "cornerRadius": "3px", "contents": track},
            {"type": "text", "text": f"{progress}%", "size": "xxs", "color": "#FFFFFF", "align": "end"},
        ],
    }


def _progress_bar(progress, color=BRAND_COLOR):
    """Regular dark-on-light progress bar, for use in the (white) body."""
    try:
        progress = max(0, min(100, int(progress)))
    except (TypeError, ValueError):
        progress = 0
    track = []
    if progress > 0:
        track.append({"type": "box", "layout": "vertical", "flex": progress, "backgroundColor": color, "contents": []})
    if progress < 100:
        track.append({"type": "box", "layout": "vertical", "flex": max(1, 100 - progress), "backgroundColor": "#E5E7EB", "contents": []})
    return {
        "type": "box",
        "layout": "vertical",
        "margin": "sm",
        "spacing": "xs",
        "contents": [
            {"type": "box", "layout": "horizontal", "height": "6px", "cornerRadius": "3px", "contents": track},
            {"type": "text", "text": f"{progress}%", "size": "xxs", "color": MUTED_COLOR, "align": "end"},
        ],
    }


def _colored_header(color, eyebrow, title_text, corner_text=None, progress=None):
    """A full-width colored band used as the bubble header — eyebrow (small,
    top line, e.g. friendly_id) + the Dohome badge on the right, then the big
    status/title line, an optional progress bar, and an optional corner_text
    line (e.g. priority) under everything."""
    top_row = {
        "type": "box",
        "layout": "horizontal",
        "alignItems": "center",
        "contents": [
            {"type": "text", "text": eyebrow, "size": "xs", "color": "#FFFFFF", "flex": 1, "wrap": True},
            _logo_icon(),
        ],
    }
    contents = [
        top_row,
        {"type": "text", "text": title_text, "size": "lg", "weight": "bold", "color": "#FFFFFF", "margin": "md", "wrap": True},
    ]
    if corner_text:
        # Accept either a single string (all existing callers) or a list of
        # strings rendered as separate lines (used by the PM dashboard header
        # to stack an on-track/off-track badge above a next-milestone line —
        # LINE Flex "text" doesn't reliably wrap embedded "\n" the way plain
        # text does, so multiple lines need to be separate text components).
        lines = corner_text if isinstance(corner_text, list) else [corner_text]
        for line in lines:
            contents.append({"type": "text", "text": line, "size": "xs", "color": "#FFFFFF", "margin": "xs", "wrap": True})
    if progress is not None:
        contents.append(_header_progress_bar(progress))

    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": color,
        "paddingAll": "16px",
        "contents": contents,
    }


def _bubble(header_box, body_contents, size="kilo", footer_button=None):
    """footer_button accepts either a single Flex action dict (existing
    callers) or a list of action dicts, rendered as one secondary button per
    action stacked vertically — e.g. build_project_bubble's "ดูรายละเอียด
    เพิ่มเติม" postback button plus the "ดูเว็บเต็มจอ" uri button underneath."""
    bubble = {
        "type": "bubble",
        "size": size,
        "header": header_box,
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "paddingAll": "16px", "contents": body_contents},
    }
    if footer_button:
        actions = footer_button if isinstance(footer_button, list) else [footer_button]
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "spacing": "sm",
            "contents": [
                {"type": "button", "style": "secondary", "height": "sm", "action": action}
                for action in actions
            ],
        }
    return bubble


def build_task_bubble(task, resolve_user=None, detailed=False):
    friendly_id = _s(task.get("friendly_id") or task.get("id"))
    title = _s(task.get("title"))
    status = task.get("status") or ""
    priority = task.get("priority") or ""
    due = _fmt_date(task.get("due_date"))
    assignee = _person_name(task.get("assigned_to"), resolve_user)
    progress = task.get("progress")

    status_label = TASK_STATUS_TH.get(status, status or "-")
    color = TASK_STATUS_COLOR.get(status, MUTED_COLOR)
    priority_label = f"ความสำคัญ: {PRIORITY_TH.get(priority, priority or '-')}" if priority else None

    header = _colored_header(color, friendly_id, status_label, corner_text=priority_label, progress=progress)

    body = [
        {"type": "text", "text": title, "weight": "bold", "size": "md", "wrap": True},
        {"type": "separator", "margin": "sm"},
        _row("ผู้รับผิดชอบ", assignee),
        _row("กำหนดส่ง", due),
    ]

    if detailed:
        manday = task.get("manday")
        point = task.get("point")
        preview = _s(task.get("description"), "")
        if manday is not None:
            body.append(_row("Manday", str(manday)))
        if point is not None:
            body.append(_row("Points", str(point)))
        if preview:
            body.append({"type": "separator", "margin": "md"})
            body.append({"type": "text", "text": preview[:200], "size": "xs", "wrap": True, "margin": "md", "color": "#555555"})

    return _bubble(header, body)


def build_project_bubble(project, detailed=False, show_detail_button=False):
    friendly_id = _s(project.get("friendly_id") or project.get("id"))
    name = _s(project.get("name"))
    status = project.get("status") or ""
    start = _fmt_date(project.get("start_date"))
    end = _fmt_date(project.get("end_date"))
    members = project.get("member_ids") or []

    status_label = PROJECT_STATUS_TH.get(status, status or "-")
    color = PROJECT_STATUS_COLOR.get(status, MUTED_COLOR)

    header = _colored_header(color, friendly_id, status_label)

    task_count = project.get("task_count")
    done_task_count = project.get("done_task_count")

    # When a live "milestones" list is embedded (list_my_managed_projects
    # merges one in per project), derive the count shown here from that list
    # instead of the project object's own milestone_count/done_milestone_count
    # fields — those come from a separate, occasionally-stale stored summary
    # (same class of staleness already confirmed for a milestone's own
    # "progress" field; see _effective_milestone_progress), and disagreeing
    # with the milestone mini-cards rendered a few lines below from the same
    # list would be a confusing, avoidable mismatch. Only fall back to the
    # stored fields when no milestones list was fetched at all (e.g. the
    # k-get-project/Gemini path, which doesn't merge one in).
    milestones_list = project.get("milestones") or []
    if milestones_list:
        milestone_count = len(milestones_list)
        done_milestone_count = sum(1 for m in milestones_list if m.get("status") == "done")
    else:
        milestone_count = project.get("milestone_count")
        done_milestone_count = project.get("done_milestone_count")

    body = [
        {"type": "text", "text": name, "weight": "bold", "size": "md", "wrap": True},
        {"type": "separator", "margin": "sm"},
        _row("เริ่ม", start),
        _row("สิ้นสุด", end),
        _row("สมาชิก", f"{len(members)} คน"),
    ]
    # task_count/milestone_count are always present on a project object (even
    # when the detailed "milestones" list below is empty) — surfacing them
    # here gives an at-a-glance completion ratio matching what k-projects
    # --raw actually returns, per the real data checked against the user.
    if task_count is not None:
        body.append(_row("งาน", f"{done_task_count or 0}/{task_count}"))
    if milestone_count is not None:
        body.append(_row("Milestone", f"{done_milestone_count or 0}/{milestone_count}"))

    if detailed:
        if milestones_list:
            body.append({"type": "separator", "margin": "md"})
            body.append({"type": "text", "text": f"MILESTONES ({len(milestones_list)})", "size": "xs", "weight": "bold", "margin": "md", "color": MUTED_COLOR})
            for m in milestones_list[:6]:
                body.append(_milestone_mini_card(m))
            if len(milestones_list) > 6:
                body.append({"type": "text", "text": f"และอีก {len(milestones_list) - 6} รายการ...", "size": "xxs", "color": MUTED_COLOR, "margin": "sm"})
        desc = _s(project.get("description"), "")
        if desc:
            body.append({"type": "separator", "margin": "md"})
            body.append({"type": "text", "text": desc[:200], "size": "xs", "wrap": True, "margin": "md", "color": "#555555"})

    footer_buttons = []
    project_id = project.get("id")
    if show_detail_button and project_id:
        footer_buttons.append({
            "type": "postback",
            "label": "ดูรายละเอียดเพิ่มเติม",
            "data": f"view=project&id={project_id}",
            "displayText": f"รายละเอียด {friendly_id}",
        })
        # Full-screen web version of the same dashboard (see
        # liff/project/index.html + app/main.py's /api/project-dashboard
        # route) — opened as a LIFF app in "Full" size so it renders without
        # LINE's chrome, meant for presenting on a phone/tablet screen rather
        # than reading inline in the chat. Only added once LIFF_PROJECT_ID is
        # actually configured, so an unconfigured deployment doesn't ship a
        # dead button.
        if config.LIFF_PROJECT_ID:
            # The slash between {liffId} and "?" is load-bearing: per LINE's
            # own docs (Opening a LIFF app > Create a primary redirect URL),
            # only a *path* appended after {liffId} counts as "additional
            # information" that gets threaded through the liff.state redirect
            # dance and restored onto the final URL. A bare "?query" glued
            # directly onto {liffId} with no "/" isn't recognized as that
            # pattern at all and was silently dropped — confirmed via real
            # testing (button opened the page with project_id missing
            # entirely, not just delayed/re-encoded).
            footer_buttons.append({
                "type": "uri",
                "label": "ดูเว็บเต็มจอ",
                "uri": f"https://liff.line.me/{config.LIFF_PROJECT_ID}/?project_id={project_id}",
            })

    return _bubble(header, body, footer_button=footer_buttons or None)


def _effective_milestone_progress(milestone):
    """dh-task's stored "progress" field on a milestone is frequently stale
    (real data checked: milestones with 3/5 tasks done still had
    "progress": 0) — it's a value someone has to explicitly recalculate
    (`k-milestone-recalc`), not something the API keeps in sync with task
    completion automatically. task_count/done_task_count, on the other hand,
    are live-derived from real tasks, so prefer computing the percentage
    from those when a task_count is present; fall back to the stored
    "progress" field only when there's nothing to derive from (task_count is
    0/None, e.g. a milestone with no tasks linked to it yet)."""
    task_count = milestone.get("task_count")
    if task_count:
        try:
            return round(100 * (milestone.get("done_task_count") or 0) / task_count)
        except (TypeError, ZeroDivisionError):
            pass
    return milestone.get("progress")


def _milestone_mini_card(milestone):
    """A small, self-contained milestone summary meant to sit inside a
    project bubble's body — title + colored status pill on one line, then a
    thin progress bar and due date underneath. Plain dict/box only (no
    nested bubble), since Flex bubbles can't nest inside each other."""
    title = _s(milestone.get("name") or milestone.get("title"), "-")
    status = milestone.get("status") or ""
    status_label = MILESTONE_STATUS_TH.get(status, status or "-")
    color = MILESTONE_STATUS_COLOR.get(status, MUTED_COLOR)
    due = _fmt_date(milestone.get("due_date"))
    progress = _effective_milestone_progress(milestone)

    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": title, "size": "sm", "weight": "bold", "flex": 3, "wrap": True},
                {"type": "text", "text": status_label, "size": "xxs", "weight": "bold", "color": color, "align": "end", "flex": 1},
            ],
        },
    ]
    if progress is not None:
        contents.append(_progress_bar(progress, color=color))
    contents.append({"type": "text", "text": f"กำหนดเสร็จ: {due}", "size": "xxs", "color": MUTED_COLOR, "margin": "xs"})

    return {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "paddingAll": "8px",
        "backgroundColor": "#F9FAFB",
        "cornerRadius": "8px",
        "contents": contents,
    }


def build_milestone_bubble(milestone, resolve_user=None, detailed=False):
    title = _s(milestone.get("title"))
    status = milestone.get("status") or ""
    due = _fmt_date(milestone.get("due_date"))
    progress = _effective_milestone_progress(milestone) or 0
    done_count = milestone.get("done_task_count")
    task_count = milestone.get("task_count")

    status_label = MILESTONE_STATUS_TH.get(status, status or "-")
    color = MILESTONE_STATUS_COLOR.get(status, MUTED_COLOR)
    tasks_line = f"งานที่เสร็จ: {done_count or 0}/{task_count}" if task_count is not None else None

    header = _colored_header(color, "MILESTONE", status_label, corner_text=tasks_line, progress=progress)

    body = [
        {"type": "text", "text": title, "weight": "bold", "size": "md", "wrap": True},
        {"type": "separator", "margin": "sm"},
        _row("กำหนดเสร็จ", due),
    ]

    if detailed:
        owner_id = milestone.get("owner_id")
        if owner_id:
            body.append(_row("ผู้ดูแล", _person_name(owner_id, resolve_user)))
        desc = _s(milestone.get("description"), "")
        if desc:
            body.append({"type": "separator", "margin": "md"})
            body.append({"type": "text", "text": desc[:200], "size": "xs", "wrap": True, "margin": "md", "color": "#555555"})

    return _bubble(header, body)


def _stat_card(label, value, color=STATS_HEADER_COLOR):
    return {
        "type": "box",
        "layout": "vertical",
        "flex": 1,
        "paddingAll": "8px",
        "backgroundColor": "#F9FAFB",
        "cornerRadius": "8px",
        "spacing": "xs",
        "contents": [
            {"type": "text", "text": str(value), "size": "lg", "weight": "bold", "color": color, "align": "center"},
            {"type": "text", "text": label, "size": "xxs", "color": MUTED_COLOR, "align": "center", "wrap": True},
        ],
    }


def _stat_cards_grid(cards):
    """cards: list of (label, value, color) tuples, laid out 2-per-row (Flex
    boxes have no wrap layout, so a fixed 2-column grid is built manually)."""
    rows = []
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [_stat_card(label, value, color) for (label, value, color) in pair],
        })
    return {"type": "box", "layout": "vertical", "spacing": "sm", "margin": "md", "contents": rows}


_STATUS_ORDER = ("backlog", "todo", "in_progress", "in_review", "done", "cancelled")


def _status_breakdown_bar(stats):
    """Segmented bar (each status's share of total tasks) + a legend, built
    from the k-stats dict. Returns None if there's nothing to show."""
    if not isinstance(stats, dict):
        return None
    counts = [(status, int(stats.get(status) or 0)) for status in _STATUS_ORDER]
    total = sum(c for _, c in counts)
    if total <= 0:
        return None

    track = [
        {"type": "box", "layout": "vertical", "flex": count, "backgroundColor": TASK_STATUS_COLOR.get(status, MUTED_COLOR), "contents": []}
        for status, count in counts if count > 0
    ]
    bar = {"type": "box", "layout": "horizontal", "height": "10px", "cornerRadius": "5px", "contents": track}

    legend_items = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "xs",
            "alignItems": "center",
            "contents": [
                {"type": "box", "layout": "vertical", "width": "8px", "height": "8px", "cornerRadius": "4px", "backgroundColor": TASK_STATUS_COLOR.get(status, MUTED_COLOR), "contents": []},
                {"type": "text", "text": f"{TASK_STATUS_TH.get(status, status)} {count}", "size": "xxs", "color": MUTED_COLOR, "wrap": True},
            ],
        }
        for status, count in counts if count > 0
    ]
    legend_rows = [
        {"type": "box", "layout": "horizontal", "spacing": "md", "margin": "xs", "contents": legend_items[i:i + 3]}
        for i in range(0, len(legend_items), 3)
    ]
    return {"type": "box", "layout": "vertical", "spacing": "xs", "margin": "md", "contents": [bar] + legend_rows}


def _member_workload_rows(tasks, resolve_user=None, top_n=5):
    """Groups tasks by assignee (dict with id/name, bare id string, or
    unassigned — excluded) into done/active(in_progress+in_review)/
    pending(backlog+todo), skipping cancelled tasks, sorted by total desc,
    capped at top_n."""
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
        entries.append((name, b["done"], b["active"], b["pending"], total))
    entries.sort(key=lambda e: e[4], reverse=True)

    rows = []
    for name, done, active, pending, total in entries[:top_n]:
        pct = round(100 * done / total) if total else 0
        rows.append({
            "type": "box",
            "layout": "vertical",
            "margin": "sm",
            "spacing": "xs",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": _s(name), "size": "xs", "flex": 3, "wrap": True},
                        {"type": "text", "text": f"เสร็จ {done} • กำลังทำ {active} • รอ {pending}", "size": "xxs", "color": MUTED_COLOR, "align": "end", "flex": 4, "wrap": True},
                    ],
                },
                _progress_bar(pct, color=BRAND_COLOR),
            ],
        })
    return rows


def _upcoming_task_row(task):
    title = _s(task.get("title"))
    due = _fmt_date(task.get("due_date"))
    status = task.get("status") or ""
    color = TASK_STATUS_COLOR.get(status, MUTED_COLOR)
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "spacing": "sm",
        "contents": [
            {"type": "box", "layout": "vertical", "width": "6px", "backgroundColor": color, "cornerRadius": "2px", "contents": []},
            {"type": "text", "text": title, "size": "xs", "flex": 4, "wrap": True},
            {"type": "text", "text": due, "size": "xxs", "color": MUTED_COLOR, "align": "end", "flex": 2},
        ],
    }


def _days_to_next_milestone(milestones):
    """Earliest due_date among not-yet-done milestones. Returns (days, milestone)
    where days can be negative (already overdue) or None if there's nothing
    upcoming to report."""
    from datetime import date, datetime

    upcoming = []
    for m in milestones or []:
        if (m.get("status") or "") == "done":
            continue
        due = m.get("due_date")
        if not due:
            continue
        try:
            due_date = datetime.fromisoformat(str(due).split("T")[0]).date()
        except ValueError:
            continue
        upcoming.append((due_date, m))
    if not upcoming:
        return None
    upcoming.sort(key=lambda pair: pair[0])
    due_date, m = upcoming[0]
    return (due_date - date.today()).days, m


def build_project_dashboard_bubble(dashboard, resolve_user=None):
    """The richer "PM Dashboard" view reached via a project card's Detail
    button — modeled after dh-task's own web Overview tab. `dashboard` is
    the dict returned by klive_service.get_project_dashboard(): project,
    milestones, tasks, stats, overdue, due_this_week.

    Note on the on-track/off-track badge: dh-task's web UI shows its own
    "Off Track" verdict, but that's a subjective computed label with no raw
    API field backing it in anything klive_tasks_api.py exposes — rather
    than guess at replicating an algorithm we can't see, this badge is an
    honest, simpler proxy (any overdue tasks = at risk)."""
    project = dashboard.get("project") or {}
    milestones = dashboard.get("milestones") or []
    tasks = dashboard.get("tasks") or []
    stats = dashboard.get("stats") or {}
    overdue = dashboard.get("overdue") or []
    due_this_week = dashboard.get("due_this_week") or []

    friendly_id = _s(project.get("friendly_id") or project.get("id"))
    name = _s(project.get("name"))
    status = project.get("status") or ""
    status_label = PROJECT_STATUS_TH.get(status, status or "-")
    color = PROJECT_STATUS_COLOR.get(status, MUTED_COLOR)

    task_count = project.get("task_count")
    if task_count is None:
        task_count = len(tasks)
    done_task_count = project.get("done_task_count")
    if done_task_count is None:
        done_task_count = sum(1 for t in tasks if t.get("status") == "done")
    overall_progress = round(100 * done_task_count / task_count) if task_count else 0

    # Unlike task_count/done_task_count above (where the live `tasks` list is
    # capped at _DASHBOARD_TASK_LIMIT and so can legitimately undercount a
    # very large project, making the project dict's own stored count the
    # better source), k-milestone-list has no --limit/pagination at all — it
    # always returns every milestone for the project. So `milestones` here is
    # the complete, live list, while project.get("milestone_count") /
    # done_milestone_count come from a *different* endpoint (k-get-project)
    # whose counters are a separately-stored, occasionally-stale summary
    # (same stale-counter pattern already confirmed for a milestone's own
    # "progress" field — see _effective_milestone_progress). Deriving from
    # the live list directly is what actually matches what's rendered below
    # in the Milestone Progress section, so prefer that over the project
    # dict's field to avoid the two numbers disagreeing.
    milestone_count = len(milestones)
    done_milestone_count = sum(1 for m in milestones if m.get("status") == "done")

    on_track = len(overdue) == 0
    badge_text = "✅ ตรงตามแผน" if on_track else f"⚠️ มีงานเลยกำหนด {len(overdue)} รายการ"
    corner_lines = [badge_text]
    next_ms = _days_to_next_milestone(milestones)
    if next_ms:
        days, m = next_ms
        ms_name = _s(m.get("name") or m.get("title"))
        if days < 0:
            corner_lines.append(f"🎯 {ms_name} เลยกำหนดมาแล้ว {abs(days)} วัน")
        elif days == 0:
            corner_lines.append(f"🎯 {ms_name} ครบกำหนดวันนี้")
        else:
            corner_lines.append(f"🎯 {ms_name} อีก {days} วัน")

    header = _colored_header(color, f"{friendly_id} • {status_label}", name, corner_text=corner_lines, progress=overall_progress)

    body = [
        {"type": "text", "text": "ภาพรวมโปรเจกต์", "size": "xs", "weight": "bold", "color": MUTED_COLOR},
        _stat_cards_grid([
            ("งานทั้งหมด", f"{done_task_count}/{task_count}", STATS_HEADER_COLOR),
            ("Milestone", f"{done_milestone_count}/{milestone_count}", STATS_HEADER_COLOR),
            ("รอดำเนินการ", str(int((stats.get("backlog") or 0) + (stats.get("todo") or 0))), "#3B82F6"),
            ("เลยกำหนด", str(len(overdue)), "#EF4444" if overdue else BRAND_COLOR),
        ]),
    ]

    breakdown = _status_breakdown_bar(stats)
    if breakdown:
        body.append({"type": "separator", "margin": "lg"})
        body.append({"type": "text", "text": "สถานะงาน", "size": "xs", "weight": "bold", "color": MUTED_COLOR, "margin": "lg"})
        body.append(breakdown)

    workload_rows = _member_workload_rows(tasks, resolve_user)
    body.append({"type": "separator", "margin": "lg"})
    body.append({"type": "text", "text": "ภาระงานทีม (Top 5)", "size": "xs", "weight": "bold", "color": MUTED_COLOR, "margin": "lg"})
    if workload_rows:
        body.extend(workload_rows)
    else:
        body.append({"type": "text", "text": "ยังไม่มีงานที่มอบหมาย", "size": "xs", "color": MUTED_COLOR, "margin": "sm"})

    body.append({"type": "separator", "margin": "lg"})
    body.append({"type": "text", "text": f"ความคืบหน้า Milestone ({len(milestones)})", "size": "xs", "weight": "bold", "color": MUTED_COLOR, "margin": "lg"})
    if milestones:
        for m in milestones[:5]:
            body.append(_milestone_mini_card(m))
        if len(milestones) > 5:
            body.append({"type": "text", "text": f"และอีก {len(milestones) - 5} รายการ...", "size": "xxs", "color": MUTED_COLOR, "margin": "sm"})
    else:
        body.append({"type": "text", "text": "ยังไม่มี Milestone", "size": "xs", "color": MUTED_COLOR, "margin": "sm"})

    body.append({"type": "separator", "margin": "lg"})
    body.append({"type": "text", "text": "งานที่ครบกำหนดสัปดาห์นี้", "size": "xs", "weight": "bold", "color": MUTED_COLOR, "margin": "lg"})
    if due_this_week:
        for t in due_this_week[:5]:
            body.append(_upcoming_task_row(t))
        if len(due_this_week) > 5:
            body.append({"type": "text", "text": f"และอีก {len(due_this_week) - 5} รายการ...", "size": "xxs", "color": MUTED_COLOR, "margin": "sm"})
    else:
        body.append({"type": "text", "text": "ไม่มีงานที่ครบกำหนดในสัปดาห์นี้", "size": "xs", "color": MUTED_COLOR, "margin": "sm"})

    return _bubble(header, body, size="giga")


def build_project_dashboard_message(dashboard, resolve_user=None):
    project = dashboard.get("project") or {}
    name = _s(project.get("name"))
    return _wrap(f"Dashboard: {name}", build_project_dashboard_bubble(dashboard, resolve_user))


def build_stats_bubble(stats):
    header = _colored_header(STATS_HEADER_COLOR, "DH-TASK", "สรุปสถานะงาน")

    body = []
    total = 0
    if isinstance(stats, dict):
        for status, count in stats.items():
            if isinstance(count, (int, float)):
                total += count
                body.append(_row(TASK_STATUS_TH.get(status, status), str(int(count)), TASK_STATUS_COLOR.get(status, MUTED_COLOR), bold=True))
    body.append({"type": "separator", "margin": "md"})
    body.append(_row("รวมทั้งหมด", f"{int(total)} งาน", BRAND_COLOR, bold=True))
    return _bubble(header, body)


def build_carousel(bubbles):
    return {"type": "carousel", "contents": bubbles[:MAX_CAROUSEL_ITEMS]}


def _wrap(alt_text, contents):
    return {"alt_text": alt_text[:400], "contents": contents}


def build_flex_for(kind, data, resolve_user=None):
    """
    Dispatch table: `kind` is the klive-tasks subcommand name (e.g. "k-list").
    Returns {"alt_text": str, "contents": <flex bubble/carousel dict>} or None
    if there's nothing sensible to render (empty list, wrong shape, etc.).
    """
    if kind in ("k-list", "k-subtasks"):
        tasks = data if isinstance(data, list) else []
        if not tasks:
            return None
        bubbles = [build_task_bubble(t, resolve_user) for t in tasks]
        contents = build_carousel(bubbles) if len(bubbles) > 1 else bubbles[0]
        return _wrap(f"รายการงาน {len(tasks)} รายการ", contents)

    if kind == "k-get":
        if not isinstance(data, dict):
            return None
        return _wrap(f"งาน: {_s(data.get('title'))}", build_task_bubble(data, resolve_user, detailed=True))

    if kind == "k-projects":
        projects = data if isinstance(data, list) else []
        if not projects:
            return None
        # detailed=True so each project card also shows its milestones —
        # harmless if the list endpoint doesn't embed a "milestones" field
        # per project (build_project_bubble only renders that section when
        # the field is actually present). show_detail_button=True adds a
        # footer button per card that triggers the fuller PM dashboard view
        # (see build_project_dashboard_bubble) — makes sense for a list of
        # projects, not for the already-detailed single k-get-project view.
        bubbles = [build_project_bubble(p, detailed=True, show_detail_button=True) for p in projects]
        contents = build_carousel(bubbles) if len(bubbles) > 1 else bubbles[0]
        return _wrap(f"รายการโปรเจกต์ {len(projects)} รายการ", contents)

    if kind == "k-get-project":
        if not isinstance(data, dict):
            return None
        return _wrap(f"โปรเจกต์: {_s(data.get('name'))}", build_project_bubble(data, detailed=True))

    if kind == "k-milestone-list":
        milestones = data if isinstance(data, list) else []
        if not milestones:
            return None
        bubbles = [build_milestone_bubble(m, resolve_user) for m in milestones]
        contents = build_carousel(bubbles) if len(bubbles) > 1 else bubbles[0]
        return _wrap(f"รายการ Milestone {len(milestones)} รายการ", contents)

    if kind == "k-milestone-get":
        if not isinstance(data, dict):
            return None
        return _wrap(f"Milestone: {_s(data.get('title'))}", build_milestone_bubble(data, resolve_user, detailed=True))

    if kind == "k-stats":
        if not isinstance(data, dict):
            return None
        return _wrap("สรุปสถิติงาน", build_stats_bubble(data))

    return None
