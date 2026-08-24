---
name: klive-tasks
description: Use when the user wants to create, list, search, inspect, update, or delete klive-tasks tasks, projects, milestones, or sprints. Also use when the user asks about task stats, subtasks, progress, mandays, or wants to assign tasks to team members.
---

# klive-tasks

## Tool

```
python3 ~/tools/klive_tasks_api.py <subcommand> [args]
```

Env vars ใน `~/.zshrc`:
- `KLIVE_API_TOKEN` — API token จากหน้า Profile **(แนะนำ, ใช้ได้เลยไม่ต้อง login)**
- `KLIVE_TASKS_EMAIL` + `KLIVE_TASKS_PASSWORD` — fallback ถ้าไม่มี token
- `KLIVE_TASKS_API_URL` — default: `https://tasks.dohome.technology/api`

---

## Users

```bash
k-users                             # list all users (id, name, nickname, email)
k-users --search "name or email"    # filter by name / nickname / email
k-users --raw                       # raw JSON output
```

---

## Projects

```bash
k-projects                          # list all projects
k-projects --search "name"          # search by name
k-projects --status active          # filter: planning | active | on_hold | completed | cancelled
k-projects --raw
k-get-project --id <project_id>     # full detail (milestones, members, description)
k-get-project --id <project_id> --raw
```

---

## Products

CLI ไม่รองรับ `--product-id` — ใช้ Python inline:

```python
authed_request(config, 'GET', '/products/<product_id>')
authed_request(config, 'GET', '/tasks?product=<product_id>&page=1&limit=50')
```

query param คือ `?product=<id>` ไม่ใช่ `?productId=`

---

## Tasks — List & Search

```bash
k-list                              # list tasks (default 20)
k-list --search "keyword"
k-list --status todo                # backlog | todo | in_progress | in_review | done | cancelled
k-list --project-id <id>
k-list --assignee <user_id>
k-list --parent-id <task_id>        # list subtasks of a task
k-list --due-filter Overdue         # Today | This Week | This Month | Overdue | Next Week
k-list --due-start 2026-06-01 --due-end 2026-06-30
k-list --limit 50 --page 2
k-list --format table               # markdown (default) | table
k-list --raw                        # raw JSON
```

---

## Tasks — Get / Subtasks / Stats

```bash
k-get --id tsk-32d8f3b4             # full task detail (accepts friendly_id or raw id)
k-get --id tsk-32d8f3b4 --raw
k-subtasks --id tsk-32d8f3b4        # list subtasks of a task
k-stats                             # counts by status (all tasks)
k-stats --project-id <id>           # counts for a project
```

---

## Tasks — Create

```bash
k-create --title "Task title"
k-create --title "..." \
  --description "..." \
  --status todo \
  --priority high \
  --start-date 2026-06-01 \
  --start-time 09:00 \
  --due-date 2026-06-30 \
  --due-time 18:00 \
  --project-id <project_id> \
  --parent-id <parent_task_id> \
  --sprint-id <sprint_id> \
  --milestone-id <milestone_id> \
  --assigned-to "user_id:user:Display Name" \
  --manday 3 \
  --point 5 \
  --progress 0 \
  --notes "..."
```

Default status: `todo`

---

## Tasks — Update

```bash
k-update --id tsk-xxx --status done
k-update --id tsk-xxx --priority high --due-date 2026-07-01
k-update --id tsk-xxx --assigned-to "user_id:user:Name"
k-update --id tsk-xxx --progress 75
k-update --id tsk-xxx --manday 2 --point 3
k-update --id tsk-xxx --sprint-id <sprint_id>
k-update --id tsk-xxx --milestone-id <milestone_id>
k-update --id tsk-xxx --notes "..."
k-update --id tsk-xxx --start-time 09:00 --due-time 17:00
```

---

## Tasks — Delete

```bash
k-delete --id tsk-xxx               # soft delete
```

---

## Milestones

```bash
k-milestone-list  --project-id <id>
k-milestone-list  --project-id <id> --status active   # upcoming|active|done|overdue
k-milestone-list  --project-id <id> --raw

k-milestone-get   --project-id <id> --id <milestone_id>
k-milestone-get   --project-id <id> --id <milestone_id> --raw

k-milestone-create --project-id <id> --title "..." --start-date 2026-07-01 --due-date 2026-07-31
k-milestone-create --project-id <id> --title "..." --start-date 2026-07-01 --due-date 2026-07-31 \
  --description "..." \
  --owner-id <user_id> \
  --color "#3b82f6" \
  --display-order 0

k-milestone-update --project-id <id> --id <milestone_id> --status active
k-milestone-update --project-id <id> --id <milestone_id> --progress 75
k-milestone-update --project-id <id> --id <milestone_id> --title "..." --due-date 2026-08-01

k-milestone-recalc  --project-id <id> --id <milestone_id>   # auto-calc progress from tasks

k-milestone-delete  --project-id <id> --id <milestone_id>
```

Default create: `status=upcoming`, `progress=0`
`recalc` sets `status=done` automatically when progress reaches 100.

### Link task to milestone
```bash
k-update --id tsk-xxx --milestone-id <milestone_id>
```

---

## Field Reference

| Field | Values |
|---|---|
| status | backlog, todo, in_progress, in_review, done, cancelled |
| priority | low, medium, high, urgent |
| assigned-to | `id:type:name` e.g. `6983...b3d1:user:Roengrit` |
| date | YYYY-MM-DD |
| time | HH:mm |
| milestone status | upcoming, active, done, overdue |
| due-filter | Today, This Week, This Month, Overdue, Next Week |

---

## Rules

- Always use `friendly_id` (e.g. `tsk-32d8f3b4`) in user-facing output — script resolves to raw id automatically
- Show minimum: ID, Status, Priority, Due, Title in list output
- When user wants subtasks: use `k-subtasks` or `k-list --parent-id`
- When creating tasks in a project without project_id: run `k-projects` first
- When assigning to team member: look up their ID from memory [[team-members]] or run `k-users --search "name"`
- **Bulk operations** (update many tasks): use Python inline + `authed_request` — NOT zsh loop (Thai chars break in `eval`)
- **Products**: use Python inline + `authed_request` with `?product=<id>` (not `?productId=`)
- **Milestones**: prefer `recalculate` over manually setting `progress` — keeps status in sync
- Summarize result briefly after each command
