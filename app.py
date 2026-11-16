import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import date

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_db_connection():
    conn = sqlite3.connect("project.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_id = session["user_id"]
    today = date.today().isoformat()

    if request.method == "POST":
        skill_name = request.form.get("name")
        description = request.form.get("description")

        if not skill_name:
            skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (user_id,)).fetchall()
            habits = conn.execute("""
                SELECT habits.*, skills.name AS skill_name
                FROM habits
                JOIN skills ON habits.skill_id = skills.id
                WHERE habits.user_id = ?
            """, (user_id,)).fetchall()
            conn.close()
            return render_template("index.html", skills=skills, habits=habits, error="Skill name cannot be blank")

        conn.execute(
            "INSERT INTO skills (user_id, name, description) VALUES (?, ?, ?)",
            (user_id, skill_name, description)
        )
        conn.commit()
        conn.close()
        return redirect("/")

    skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (user_id,)).fetchall()

    habits = conn.execute("""
        SELECT habits.*, skills.name AS skill_name,
               EXISTS(
                   SELECT 1 FROM habit_logs
                   WHERE habit_logs.habit_id = habits.id
                   AND habit_logs.completed_date = ?
               ) AS completed_today
        FROM habits
        JOIN skills ON habits.skill_id = skills.id
        WHERE habits.user_id = ?
    """, (today, user_id)).fetchall()

    conn.close()
    return render_template("index.html", skills=skills, habits=habits)

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return render_template("login.html", error="Must provide username")
        elif not password:
            return render_template("login.html", error="Must provide password")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["hash"], password):
            return render_template("login.html", error="Invalid username and/or password")

        session["user_id"] = user["id"]
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return render_template("register.html", error="Must provide username")
        elif not password:
            return render_template("register.html", error="Must provide password")
        elif password != confirmation:
            return render_template("register.html", error="Passwords must match")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists")

        conn.close()
        return redirect("/login")

    else:
        return render_template("register.html")

@app.route("/habits", methods=["GET", "POST"])
def habits():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form.get("title")
        skill_id = request.form.get("skill_id")
        xp_reward = request.form.get("xp_reward", type=int)
        frequency = request.form.get("frequency", "daily")

        if not title or not skill_id or not xp_reward:
            skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (user_id,)).fetchall()
            conn.close()
            return render_template("habits.html", skills=skills, error="Please fill out all required fields.")

        conn.execute(
            "INSERT INTO habits (user_id, skill_id, title, frequency, xp_reward) VALUES (?, ?, ?, ?, ?)",
            (user_id, skill_id, title, frequency, xp_reward)
        )
        conn.commit()
        conn.close()
        return redirect("/")

    skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return render_template("habits.html", skills=skills)

@app.route("/complete/<int:habit_id>", methods=["POST"])
def complete_habit(habit_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_id = session["user_id"]
    today = date.today().isoformat()

    habit = conn.execute(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, user_id)
    ).fetchone()

    if not habit:
        conn.close()
        return redirect("/")

    already_done = conn.execute(
        "SELECT id FROM habit_logs WHERE habit_id = ? AND completed_date = ?",
        (habit_id, today)
    ).fetchone()

    if not already_done:
        conn.execute(
            "INSERT INTO habit_logs (habit_id, user_id, completed_date) VALUES (?, ?, ?)",
            (habit_id, user_id, today)
        )
        conn.execute(
            "UPDATE habits SET streak = streak + 1 WHERE id = ?",
            (habit_id,)
        )

        skill = conn.execute("SELECT * FROM skills WHERE id = ?", (habit["skill_id"],)).fetchone()
        new_xp = skill["current_xp"] + habit["xp_reward"]
        level = skill["level"]
        xp_to_next = skill["xp_to_next_level"]

        while new_xp >= xp_to_next:
            new_xp -= xp_to_next
            level += 1
            xp_to_next = int(xp_to_next * 1.5)

        conn.execute(
            "UPDATE skills SET current_xp = ?, level = ?, xp_to_next_level = ? WHERE id = ?",
            (new_xp, level, xp_to_next, skill["id"])
        )
        conn.commit()

    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
