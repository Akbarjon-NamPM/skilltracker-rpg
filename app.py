import hmac
import os
import re
import secrets
from datetime import date, timedelta

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session)
from werkzeug.security import check_password_hash, generate_password_hash

from db import DB, IntegrityError, init_db

ON_VERCEL = bool(os.environ.get("VERCEL"))
REPO_URL = os.environ.get("REPO_URL", "")  # e.g. https://github.com/you/skilltracker-rpg

# "public" is served by Vercel's CDN; static_url_path="" makes it work locally too.
app = Flask(__name__, static_folder="public", static_url_path="")

secret = os.environ.get("SECRET_KEY")
if not secret:
    if ON_VERCEL:
        raise RuntimeError("Set the SECRET_KEY environment variable in Vercel.")
    secret = "dev-only-" + secrets.token_hex(16)
app.config.update(
    SECRET_KEY=secret,
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=ON_VERCEL,
)

XP_CHOICES = {15, 25, 50, 100}
FREQUENCIES = {"daily", "weekly"}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")

_ready = False


# ---------- infrastructure ----------

def get_db():
    if "db" not in g:
        g.db = DB()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def setup_and_csrf():
    global _ready
    if not _ready:
        init_db()
        _ready = True
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        good = session.get("csrf_token", "")
        if not good or not hmac.compare_digest(sent, good):
            abort(400, "Invalid or missing CSRF token. Refresh the page and try again.")


@app.context_processor
def inject_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return {"csrf_token": session["csrf_token"], "repo_url": REPO_URL}


@app.after_request
def add_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", message=e.description), 400


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", message="Page not found."), 404


def login_required():
    return "user_id" not in session


# ---------- helpers ----------

def week_start(d):
    return d - timedelta(days=d.weekday())


def is_done(habit, today):
    last = habit["last_completed"]
    if not last:
        return False
    cutoff = week_start(today) if habit["frequency"] == "weekly" else today
    return last >= cutoff.isoformat()


def periods_since(habit, today):
    """How many days (daily) or weeks (weekly) since the last completion."""
    last = date.fromisoformat(habit["last_completed"])
    if habit["frequency"] == "weekly":
        return (week_start(today) - week_start(last)).days // 7
    return (today - last).days


def next_streak(habit, today):
    if not habit["last_completed"]:
        return 1
    return (habit["streak"] or 0) + 1 if periods_since(habit, today) == 1 else 1


def load_dashboard(db, user_id):
    today = date.today()
    skills = db.all("SELECT * FROM skills WHERE user_id = ? ORDER BY id", (user_id,))
    habits = db.all("""
        SELECT habits.*, skills.name AS skill_name
        FROM habits JOIN skills ON habits.skill_id = skills.id
        WHERE habits.user_id = ? ORDER BY habits.id""", (user_id,))
    for h in habits:
        h["completed_today"] = is_done(h, today)
        # a streak that has been missed shows as 0 until the next completion
        alive = h["last_completed"] and periods_since(h, today) <= 1
        h["streak_now"] = (h["streak"] or 0) if alive else 0
    for s in skills:
        s["pct"] = min(100, s["current_xp"] / s["xp_to_next_level"] * 100)
    return skills, habits


# ---------- auth ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirmation = request.form.get("confirmation") or ""

        if not USERNAME_RE.match(username):
            return render_template("register.html", error="Username: 3-30 letters, digits or _")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters")
        if password != confirmation:
            return render_template("register.html", error="Passwords must match")

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                       (username, generate_password_hash(password)))
            db.commit()
        except IntegrityError:
            db.rollback()
            return render_template("register.html", error="Username already exists")

        flash("Account created. Log in to begin your quest!", "success")
        return redirect("/login")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            return render_template("login.html", error="Must provide username and password")

        user = get_db().one("SELECT * FROM users WHERE username = ?", (username,))
        if user is None or not check_password_hash(user["hash"], password):
            return render_template("login.html", error="Invalid username and/or password")

        session.clear()
        session["user_id"] = user["id"]
        return redirect("/")
    if "user_id" in session:
        return redirect("/")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")


# ---------- dashboard ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if login_required():
        return redirect("/login")
    db = get_db()
    user_id = session["user_id"]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not name:
            flash("Skill name cannot be blank.", "danger")
        elif len(name) > 50 or len(description) > 200:
            flash("Name max 50 chars, description max 200.", "danger")
        else:
            db.execute("INSERT INTO skills (user_id, name, description) VALUES (?, ?, ?)",
                       (user_id, name, description or None))
            db.commit()
            flash(f"Skill tree '{name}' created!", "success")
        return redirect("/")

    skills, habits = load_dashboard(db, user_id)
    done = sum(1 for h in habits if h["completed_today"])
    return render_template("index.html", skills=skills, habits=habits,
                           done=done, total=len(habits))


# ---------- habits ----------

@app.route("/habits", methods=["GET", "POST"])
def habits():
    if login_required():
        return redirect("/login")
    db = get_db()
    user_id = session["user_id"]
    skills = db.all("SELECT * FROM skills WHERE user_id = ? ORDER BY id", (user_id,))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        skill_id = request.form.get("skill_id", type=int)
        xp_reward = request.form.get("xp_reward", type=int)
        frequency = request.form.get("frequency", "daily")

        owned = any(s["id"] == skill_id for s in skills)
        if not title or len(title) > 100 or not owned \
                or xp_reward not in XP_CHOICES or frequency not in FREQUENCIES:
            return render_template("habits.html", skills=skills,
                                   error="Please fill out all fields correctly.")

        db.execute("""INSERT INTO habits (user_id, skill_id, title, frequency, xp_reward)
                      VALUES (?, ?, ?, ?, ?)""",
                   (user_id, skill_id, title, frequency, xp_reward))
        db.commit()
        flash("Quest added!", "success")
        return redirect("/")

    return render_template("habits.html", skills=skills)


@app.route("/complete/<int:habit_id>", methods=["POST"])
def complete_habit(habit_id):
    if login_required():
        return redirect("/login")
    db = get_db()
    user_id = session["user_id"]
    today = date.today()

    habit = db.one("SELECT * FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
    if not habit:
        abort(404)
    if is_done(habit, today):
        return redirect("/")

    streak = next_streak(habit, today)
    try:
        db.execute("INSERT INTO habit_logs (habit_id, user_id, completed_date) VALUES (?, ?, ?)",
                   (habit_id, user_id, today.isoformat()))
    except IntegrityError:  # double click / second tab
        db.rollback()
        return redirect("/")

    db.execute("UPDATE habits SET streak = ?, last_completed = ? WHERE id = ?",
               (streak, today.isoformat(), habit_id))

    skill = db.one("SELECT * FROM skills WHERE id = ? AND user_id = ?",
                   (habit["skill_id"], user_id))
    xp, level, need = skill["current_xp"] + habit["xp_reward"], skill["level"], skill["xp_to_next_level"]
    leveled = False
    while xp >= need:
        xp -= need
        level += 1
        need = int(need * 1.5)
        leveled = True
    db.execute("UPDATE skills SET current_xp = ?, level = ?, xp_to_next_level = ? WHERE id = ?",
               (xp, level, need, skill["id"]))
    db.commit()

    if leveled:
        flash(f"LEVEL UP! {skill['name']} is now level {level}!", "warning")
    else:
        flash(f"+{habit['xp_reward']} XP to {skill['name']}", "success")
    return redirect("/")


@app.route("/habits/<int:habit_id>/delete", methods=["POST"])
def delete_habit(habit_id):
    if login_required():
        return redirect("/login")
    db = get_db()
    db.execute("DELETE FROM habit_logs WHERE habit_id = ? AND user_id = ?",
               (habit_id, session["user_id"]))
    db.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, session["user_id"]))
    db.commit()
    flash("Quest deleted.", "secondary")
    return redirect("/")


@app.route("/skills/<int:skill_id>/delete", methods=["POST"])
def delete_skill(skill_id):
    if login_required():
        return redirect("/login")
    db = get_db()
    uid = session["user_id"]
    db.execute("""DELETE FROM habit_logs WHERE habit_id IN
                  (SELECT id FROM habits WHERE skill_id = ? AND user_id = ?)""", (skill_id, uid))
    db.execute("DELETE FROM habits WHERE skill_id = ? AND user_id = ?", (skill_id, uid))
    db.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, uid))
    db.commit()
    flash("Skill tree deleted.", "secondary")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
