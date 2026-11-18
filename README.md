# ⚔️ SkillTracker RPG

#### 🔗 Live Demo: https://YOUR-PROJECT.vercel.app
#### 🎥 Video Demo: https://youtu.be/woaKTKbUK2o

> **How to try it:** open the live link, click **Register**, create an account, then add a skill tree (for example "Programming"), add a habit to it, and press **Complete** to earn XP.

## Description

SkillTracker RPG is a full-stack, gamified habit tracker and my CS50x final project. A normal to-do list rarely keeps people motivated for long, so this app borrows mechanics from role-playing games: skill trees, experience points (XP), levels, and daily streaks. You define the areas of your life you want to improve (Programming, Fitness, Language Learning, Mindfulness), attach habits ("quests") to them, and watch each skill level up as you complete those habits. The goal is to make personal growth visible and fun.

## Features

- **Accounts:** register and log in with a username and password. Every user only sees and edits their own data.
- **Skill trees:** each starts at Level 1 with 0/100 XP, a name and an optional description.
- **Quests (habits):** linked to one skill tree, with a frequency (daily or weekly) and a difficulty: Easy +15 XP, Medium +25 XP, Hard +50 XP, Epic +100 XP.
- **Completing a quest:** records the completion, updates the streak and adds XP to the parent skill.
- **Leveling:** when XP reaches the threshold, the skill levels up, leftover XP carries over, and the next threshold grows by 1.5x (100, 150, 225, ...).
- **Real streaks:** a streak grows only when you complete a habit on consecutive days (or consecutive weeks for weekly habits). If you miss a period, it shows 0 and restarts at 1 on the next completion.
- **Feedback:** success and level-up notifications, a "today: X / Y quests" counter, and live progress bars.
- **Management:** delete habits or whole skill trees (with a confirmation prompt).

## Technologies used

| Area | What I used |
|---|---|
| Language | Python 3 |
| Web framework | **Flask** (routing, sessions, flash messages, error handlers) |
| Templates | **Jinja2** with template inheritance (`layout.html`) |
| Front end | **Bootstrap 5.3** (dark theme, grid, cards, progress bars, alerts, navbar) via CDN, plus custom CSS |
| Database | **SQLite** (local development) and **PostgreSQL** (production, e.g. Neon) |
| DB drivers | `sqlite3` (standard library) and `psycopg2-binary` |
| Password security | **Werkzeug** `generate_password_hash` / `check_password_hash` (salted hashes) |
| Standard library | `os`, `re`, `hmac`, `secrets`, `datetime` |
| Hosting | **Vercel** (zero-config Flask deployment) |
| Version control | Git and GitHub |

## File structure and what each file does

- **`app.py`** is the main application. It contains the routes `/`, `/register`, `/login`, `/logout`, `/habits`, `/complete/<id>`, `/habits/<id>/delete` and `/skills/<id>/delete`. It also holds the CSRF check, the security headers, the error handlers, and the gamification engine (streak and XP calculation).
- **`db.py`** is the database layer. A small `DB` class gives the same `execute`, `one`, `all`, `commit` methods for both SQLite and PostgreSQL, converting `?` placeholders to `%s` for Postgres. `init_db()` creates the four tables automatically and migrates older databases.
- **`templates/layout.html`** is the master template: navbar (links change depending on login state), flash messages, error banner, footer.
- **`templates/index.html`** is the hero dashboard: skill cards with XP bars, the quest list, and the "create skill tree" form.
- **`templates/habits.html`** is the form for creating a habit with a dynamically filled skill dropdown.
- **`templates/login.html`, `register.html`** are the authentication pages.
- **`templates/error.html`** is a friendly page for 400 and 404 errors.
- **`public/css/styles.css`** has custom styling (gradient background, hover animations, animated progress bars).
- **`requirements.txt`** lists the dependencies: Flask, Werkzeug, psycopg2-binary.
- **`.env.example`** shows the environment variables needed.

## Database design

Four normalized tables:

1. **users**: `id`, `username` (unique), `hash`, `created_at`.
2. **skills**: `id`, `user_id`, `name`, `description`, `level`, `current_xp`, `xp_to_next_level`.
3. **habits**: `id`, `user_id`, `skill_id`, `title`, `frequency`, `xp_reward`, `streak`, `last_completed`.
4. **habit_logs**: `id`, `habit_id`, `user_id`, `completed_date`.

Foreign keys use `ON DELETE CASCADE`, so deleting a skill removes its habits and logs. A **unique index** on `(habit_id, completed_date)` guarantees a habit cannot be completed twice in the same day, even if the button is double-clicked or used in two tabs.

## Design decisions and security

- **Parameterized SQL everywhere** to prevent SQL injection.
- **Signed cookie sessions** instead of server-side files, because Vercel's filesystem is read-only and temporary. The secret key comes from the `SECRET_KEY` environment variable, and the cookie is `HttpOnly`, `SameSite=Lax` and `Secure` in production.
- **CSRF protection:** every POST form carries a random token that is compared with the session token using `hmac.compare_digest`.
- **Ownership checks:** every query filters by `user_id`, and a habit can only be attached to a skill that belongs to the same user.
- **Input validation:** username 3-30 characters (letters, digits, `_`), password at least 8 characters, length limits on titles and descriptions, and XP values restricted to the allowed set.
- **Security headers:** `X-Content-Type-Options`, `X-Frame-Options`, and `Cache-Control: no-store` for dynamic pages.
- **Logout via POST** so it cannot be triggered by a simple link.
- **Why two databases?** SQLite is simple for local development, but data would be lost on Vercel, so production uses PostgreSQL through `DATABASE_URL`.

## How the gamification engine works

When you press **Complete**, the server:
1. Finds the habit for the current user and checks it is not already done for the current day (or week).
2. Calculates the new streak: previous streak + 1 if the last completion was exactly one period ago, otherwise 1.
3. Inserts a log row and updates `streak` and `last_completed`.
4. Adds the XP reward to the skill, then loops `while xp >= threshold`, subtracting the threshold, increasing the level and multiplying the threshold by 1.5.
5. Saves everything in one transaction and shows a notification.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Without `DATABASE_URL` the app creates a local `project.db` automatically.

## Deploy on Vercel

1. Push the project to GitHub.
2. Import the repository at vercel.com/new (Flask is detected automatically from `app.py`).
3. Connect a free **Neon** Postgres database from the Vercel Marketplace; this sets `DATABASE_URL`.
4. Add `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`).
5. Redeploy. Tables are created on the first request.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FYOUR_USERNAME%2FYOUR_REPO&env=SECRET_KEY,DATABASE_URL)

## Possible future improvements

- Achievements and badges, a weekly progress chart, and reminders.
- Editing existing habits and skills.
- Password reset by email and a leaderboard between friends.
