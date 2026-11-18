# ⚔️ SkillTracker RPG

A gamified habit tracker: create skill trees, attach habits (quests) to them, complete them to earn XP, keep streaks and level up. CS50x final project, built with Flask.

**Video Demo:** https://youtu.be/woaKTKbUK2o

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FYOUR_USERNAME%2FYOUR_REPO&env=SECRET_KEY,DATABASE_URL&envDescription=SECRET_KEY%3A%20any%20long%20random%20string.%20DATABASE_URL%3A%20Postgres%20connection%20string%20(e.g.%20Neon).)

> Replace `YOUR_USERNAME/YOUR_REPO` in the button link with your GitHub repo.

## Features
- Register / log in (hashed passwords, signed cookie sessions, CSRF protection)
- Skill trees with levels, XP bars and scaling level thresholds (x1.5 each level)
- Daily and weekly habits with Easy / Medium / Hard / Epic XP rewards (+15 / +25 / +50 / +100)
- Real streaks: they continue when you complete on consecutive days (or weeks) and reset when you miss one
- Level-up and XP notifications, daily progress counter
- Delete habits and skill trees
- Each user only ever sees and changes their own data

## Project structure
| File | Purpose |
|---|---|
| `app.py` | Flask routes, auth, CSRF, streak + XP engine |
| `db.py` | Database layer: Postgres when `DATABASE_URL` is set, SQLite locally; creates/migrates tables automatically |
| `templates/` | Jinja2 pages (Bootstrap 5 dark theme) |
| `public/css/styles.css` | Custom styles (served by Vercel's CDN) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variables you need to set |

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. Without `DATABASE_URL` it uses a local `project.db` (SQLite, auto-created).

## Deploy on Vercel
Vercel detects Flask automatically (`app.py` exposes `app`), no config file needed.

1. Push this folder to GitHub.
2. Click the **Deploy with Vercel** button above (or import the repo at vercel.com/new).
3. Add a free Postgres database: Vercel project → **Storage / Marketplace → Neon** → connect it. This sets `DATABASE_URL` for you.
4. Add environment variable `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`).
5. Optional: set `REPO_URL` to your GitHub URL to show a "Deploy your own on Vercel" link (opens in a new tab) in the app footer.
6. Redeploy. Tables are created on first request.

Why Postgres? Vercel's filesystem is read-only/ephemeral, so SQLite and file-based sessions lose data there.
