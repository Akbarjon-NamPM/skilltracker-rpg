# SkillTracker RPG

#### Video Demo:  <(https://youtu.be/woaKTKbUK2o)>

#### Description:
* SkillTracker RPG is a full-stack, gamified habit tracker and self improvement web app. It's my Cs50x final project and it's designed to take the drudgery of a standard to do list and turn it into a proper role playing game. The fundamental problem with to do lists is that they simply don't provide the kind of long term motivation that you need. Skilltracker RPG tackles that by taking the standard RPG mechanics (skill trees, XP, level up thresholds, daily streaks etc) and applying them to your personal goals, your daily tasks and your self care. The idea is to turn your personal development into a visible, tangible progression.

---

### Core Features & User Workflow
On the application new users sign up for a personal account and returning users log in to access their personal hero dashboard. All user data is isolated via session authentication so their individual goals and progress are all kept safe.

Once logged in, the user experience revolves around three main actions:
1. Building your own custom skill trees. You define the core pillars of your self improvement journey (e.g. Programming, Fitness, Language Learning, Mindfulness etc). Each new skill tree you create starts at Level 1 with 0/100 XP.
2. Creating difficulty weighted quests: via the habit creation interface you can link up your regular daily or weekly habits to a specific parent skill tree. Each habit is then awarded XP according to its difficulty level: Easy (+15 XP), Medium (+25 XP), Hard (+50 XP) or Epic (+100 XP).
3. Completing Quests & Leveling Up: From the main dashboard the user clicks "Complete" on the task they've finished. The backend then records the completion immediately, bumps up the consecutive streak counter for that habit and adds the XP earned to the parent skill tree's progress bar. The skill will level up automatically as soon as the total XP reaches or exceeds the current threshold, any XP in excess of the threshold will be carried forward and the requirement for the next level will be scaled up accordingly.

---

### Application Architecture & File Breakdown
The project is structured following a modular Python Flask architecture backed by SQLite for relational data storage and Bootstrap 5 for a responsive, dark-themed user interface:

* app.py: The main Python backend app (Flask) that does all the work. Handles the auth routes (/login, /register, /logout), does the session checks, serves up the dashboard, allows for the creation of new skill trees and new habits and runs the gamification engine inside of /complete/<int:habit_id>. Uses parameterised SQL queries throughout to avoid any SQL injection.
* schema.sql: The Sqlite relational database schema. Four normalised tables are defined: users (one row per user, containing a unique username and a salted password hash), skills (one row per user skill tree, containing the user's current level, current XP and next level XP), habits (one row per individual quest, linked via foreign keys to users and skills), and habit_logs (one row per day the user completes a habit, used to enforce the daily limit and track activity).
* requirements.txt: Lists the Python dependencies required for the project environment (Flask, Flask-Session and Werkzeug).
* templates/layout.html : The master Jinja2 layout template which includes the global nav bar, the Bootstrap 5 CSS and JS frameworks, the nav links which are conditionally displayed depending on whether the user is logged in or not, the error banner and the content blocks.
* templates/index.html: The main hero dashboard view. Uses Jinja2 loops and maths filters to display the active skill trees, the dynamic XP progress bars and completion percentages. Lists out the daily quests with the appropriate styling (text-decoration-line-through and disabled buttons) for those that have already been completed for the day.
* templates/login.html & templates/register.html: Clean login/register interfaces, with server side validation and passwords hashed via werkzeug.security.
* templates/habits.html: A form to create a new habit, with a dropdown of target skill trees to choose from (populated dynamically), and the ability to set XP difficulty weights and frequencies.

---

### Setup & Installation
To run SkillTracker RPG locally in a development environment:
1. Clone or navigate into the `project` directory and install dependencies:
   ```bash
   pip install -r requirements.txt
  
