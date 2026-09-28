# Plans

Detailed planning and reasoning live here. [`TODO.md`](../../TODO.md) stays a **checklist**.

## Why not in TODO

- TODO is for status: what is open, what is done, what to do next.
- A plan is for thinking: product intent, rejected alternatives, risks, task order.
- Mixing them makes the roadmap unreadable and freezes old reasoning next to live tasks.

## Convention

| Location | Contains |
|---|---|
| `TODO.md` | One-line task + link to its plan. Mark done here. |
| `docs/plan/<name>.md` | What / Why / Risks / Alignment, decisions, atomic tasks |
| `docs/decisions.md` | DEC-xxx after a decision is **implemented** |
| `docs/*.md` (contracts) | Stable APIs, not working notes |

## Rules

- One plan file per non-trivial workstream (e.g. `sprint1-grouping.md`).
- Status line at the top: `Draft` → `Accepted` → `In progress` → `Done`.
- Atomic tasks in the plan are the implementation order (one commit each).
- When the work ships, keep the plan (history). Do not paste it back into TODO.
- Do not put secrets, real photo paths, or personal data in plans.

## Plan First (see AGENTS.md)

For any non-trivial change: write or update the plan, link it from TODO, wait for acknowledgment, then implement one atomic task.
