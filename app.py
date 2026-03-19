from flask import Flask, render_template, request, redirect, session
import sqlite3, datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("database.db")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        status TEXT,
        priority TEXT,
        created_at TEXT,
        deadline TEXT,
        assigned_to TEXT,
        project TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()
conn = sqlite3.connect("database.db")

try:
    conn.execute("ALTER TABLE tickets ADD COLUMN project TEXT")
except:
    pass

conn.commit()
conn.close()
# ---------------- GLOBAL NOTIFICATION ----------------
@app.context_processor
def inject_notif():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    notif = cur.fetchone()[0]

    return dict(notif=notif)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        # 🔥 DB use hi nahi karenge
        session["user"] = user

        return redirect("/dashboard")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    open_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Closed'")
    closed_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE assigned_to IS NOT NULL")
    assigned = cur.fetchone()[0]

    # overdue
    cur.execute("SELECT deadline, status FROM tickets")
    data = cur.fetchall()

    overdue = 0
    now = datetime.datetime.now()

    for d in data:
        if d[0]:
            try:
                dl = datetime.datetime.fromisoformat(d[0])
                if now > dl and d[1] != "Closed":
                    overdue += 1
            except:
                pass

    return render_template("dashboard.html",
        total=total,
        open_t=open_t,
        closed_t=closed_t,
        assigned=assigned,
        overdue=overdue
    )

# ---------------- TICKETS (SEARCH + FILTER) ----------------
@app.route("/tickets")
def tickets():
    q = request.args.get("q")
    status = request.args.get("status")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if q:
        cur.execute("""
        SELECT * FROM tickets 
        WHERE LOWER(title) LIKE LOWER(?) 
        OR LOWER(description) LIKE LOWER(?)
        """, ('%' + q + '%', '%' + q + '%'))

    elif status:
        cur.execute("SELECT * FROM tickets WHERE status=?", (status,))

    else:
        cur.execute("SELECT * FROM tickets")

    data = cur.fetchall()

    return render_template("tickets.html", tickets=data)

# ---------------- CREATE ----------------
@app.route("/create", methods=["GET","POST"])
def create():
    if request.method == "POST":
        title = request.form["title"]
        desc = request.form["description"]
        project = request.form.get("project")

        now = datetime.datetime.now()
        deadline = now + datetime.timedelta(hours=4)

        conn = sqlite3.connect("database.db")
        conn.execute("""
        INSERT INTO tickets(title, description, status, created_at, deadline, project)
        VALUES(?,?, 'Open',?,?,?)
        """, (title, desc, str(now), str(deadline), project))

        conn.commit()
        return redirect("/tickets")

    return render_template("create.html")

# ---------------- ASSIGN ----------------
@app.route("/assign/<int:id>", methods=["POST"])
def assign(id):
    agent = request.form["agent"]

    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE tickets SET assigned_to=? WHERE id=?", (agent,id))
    conn.commit()

    return redirect("/tickets")

# ---------------- STATUS ----------------
@app.route("/status/<int:id>", methods=["POST"])
def status(id):
    status = request.form["status"]

    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE tickets SET status=? WHERE id=?", (status,id))
    conn.commit()

    return redirect("/tickets")

# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        desc = request.form["description"]

        conn.execute("UPDATE tickets SET title=?, description=? WHERE id=?", (title, desc, id))
        conn.commit()

        return redirect("/tickets")

    cur.execute("SELECT * FROM tickets WHERE id=?", (id,))
    t = cur.fetchone()

    return render_template("edit.html", t=t)

# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("database.db")
    conn.execute("DELETE FROM tickets WHERE id=?", (id,))
    conn.commit()

    return redirect("/tickets")

# ---------------- PROBLEMS ----------------
@app.route("/problems")
def problems():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE status='Open'")
    data = cur.fetchall()

    return render_template("problems.html", tickets=data)

# ---------------- CHANGES ----------------
@app.route("/changes")
def changes():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE status='Closed'")
    data = cur.fetchall()

    return render_template("changes.html", tickets=data)

# ---------------- ASSETS ----------------
@app.route("/assets")
def assets():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE assigned_to IS NOT NULL")
    data = cur.fetchall()

    return render_template("assets.html", tickets=data)

# ---------------- PROJECT LIST ----------------
@app.route("/projects")
def projects():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT project, COUNT(*) 
    FROM tickets 
    GROUP BY project
    """)

    data = cur.fetchall()

    return render_template("projects.html", projects=data)

# ---------------- PROJECT DETAIL ----------------
@app.route("/project/<name>")
def project_detail(name):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE project=?", (name,))
    data = cur.fetchall()

    return render_template("project_detail.html", tickets=data, project=name)

# ---------------- SETTINGS ----------------
@app.route("/settings", methods=["GET","POST"])
def settings():
    if request.method == "POST":
        username = request.form["username"]

        conn = sqlite3.connect("database.db")
        conn.execute("UPDATE users SET username=? WHERE username=?", 
                     (username, session["user"]))
        conn.commit()

        session["user"] = username

    return render_template("settings.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()