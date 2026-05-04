# ⏱️ Octa Working Hours System

Track working hours per proposal and project across your team.

---

## Setup

### 1. Supabase — Run SQL
SQL Editor → paste `setup_database.sql` → Run

**Requires** `octa_users` and `proposals` tables to already exist
(from the Octa Proposals app — same Supabase project).

### 2. GitHub — New repository
```bash
git init && git add . && git commit -m "feat: Octa Working Hours v1.0"
git remote add origin https://github.com/YOUR_ORG/octa-hours.git
git push -u origin main
```

### 3. Streamlit Cloud — New app
- Main file: `app.py`
- Secrets:
```toml
[supabase]
url = "https://your-project-ref.supabase.co"
key = "your-service-role-key"
```

---

## File Structure
```
octa_hours/
├── app.py                  # Landing page
├── config.py               # Constants (hours/day, hours/week, colours)
├── requirements.txt
├── setup_database.sql      # Creates work_logs + projects tables
├── .streamlit/
│   └── secrets.toml.example
├── modules/
│   ├── auth.py             # Shared auth (same octa_users table)
│   ├── database.py         # work_logs, proposals, projects queries
│   └── ui_helpers.py       # Dark theme CSS + sidebar
└── pages/
    ├── login.py            # Sign in / Register / Reset password
    ├── dashboard.py        # User: hours per proposal, totals, charts
    ├── add_hours.py        # Log + edit working hours
    └── admin.py            # Approve hours, team stats
```

---

## Key Constants (config.py)
| Constant | Value | Meaning |
|---|---|---|
| `HOURS_PER_DAY` | 7.5 | Working hours per day |
| `HOURS_PER_WEEK` | 37.5 | Working hours per week |

---

## Shared Tables (read-only from Octa Proposals)
| Table | Used for |
|---|---|
| `octa_users` | Login, registration, team grouping by organisation |
| `proposals` | Acronym dropdown when logging hours |

## New Tables (created by setup_database.sql)
| Table | Purpose |
|---|---|
| `work_logs` | All working hour entries |
| `projects` | Future: project-level time tracking |

---

## Access Control
- `apps_access` must include `"octa_hours"` for a user to log in
- Add this in the Octa Proposals Admin Panel when approving users
- Admins see all team members from the same `organisation`

---

## Adding app access for a user
In **Supabase → Table Editor → octa_users**, update:
```json
["octa_proposals", "octa_hours"]
```
Or use the Admin Panel in either app.
