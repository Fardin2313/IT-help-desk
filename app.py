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
        username TEXT UNIQUE,
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

@app.context_processor
def inject_notif():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    notif = cur.fetchone()[0]

    return dict(notif=notif)
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        data = cur.fetchone()

        if data:
            session["user"] = data[1]
            session["role"] = data[3]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid credentials ❌")

    return render_template("login.html")
@app.route("/dashboard")
def dashboard():
    if not check_login():
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    open_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Closed'")
    closed_t = cur.fetchone()[0]

    return render_template("dashboard.html",
        total=total,
        open_t=open_t,
        closed_t=closed_t
    )
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        role = request.form["role"]

        # ❌ admin block
        if role == "admin":
            return "Admin creation not allowed ❌"

        conn = sqlite3.connect("database.db")
        conn.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                     (user, pwd, role))
        conn.commit()

        return redirect("/")

    return render_template("register.html")

# ---------------- AUTH CHECK ----------------
def check_login():
    if "user" not in session:
        return False
    return True
@app.route("/tickets")
def tickets():
    if not check_login():
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    if session["role"] == "admin":
        cur.execute("SELECT * FROM tickets")

    elif session["role"] == "agent":
        cur.execute("SELECT * FROM tickets WHERE assigned_to=?", (session["user"],))

    else:
        cur.execute("SELECT * FROM tickets WHERE assigned_to=?", (session["user"],))

    data = cur.fetchall()

    return render_template("tickets.html", tickets=data)
@app.route("/create", methods=["GET","POST"])
def create():
    if not check_login():
        return redirect("/")

    if request.method == "POST":
        title = request.form["title"]
        desc = request.form["description"]
        project = request.form.get("project")

        now = datetime.datetime.now()
        deadline = now + datetime.timedelta(hours=4)

        conn = sqlite3.connect("database.db")
        conn.execute("""
        INSERT INTO tickets(title,description,status,created_at,deadline,project)
        VALUES(?,?, 'Open',?,?,?)
        """, (title, desc, str(now), str(deadline), project))

        conn.commit()
        return redirect("/tickets")

    return render_template("create.html")

@app.route("/assign/<int:id>", methods=["POST"])
def assign(id):
    agent = request.form["agent"]

    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE tickets SET assigned_to=? WHERE id=?", (agent,id))
    conn.commit()

    return redirect("/tickets")

@app.route("/status/<int:id>", methods=["POST"])
def status(id):
    if not check_login():
        return redirect("/")
    status = request.form["status"]

    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE tickets SET status=? WHERE id=?", (status,id))
    conn.commit()

    return redirect("/tickets")

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


@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("database.db")
    conn.execute("DELETE FROM tickets WHERE id=?", (id,))
    conn.commit()

    return redirect("/tickets")

@app.route("/problems")
def problems():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE status='Open'")
    data = cur.fetchall()

    return render_template("problems.html", tickets=data)
@app.route("/reports")
def reports():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    open_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Closed'")
    closed_t = cur.fetchone()[0]

    return render_template("reports.html",
                           total=total,
                           open_t=open_t,
                           closed_t=closed_t)

@app.route("/changes")
def changes():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE status='Closed'")
    data = cur.fetchall()

    return render_template("changes.html", tickets=data)

@app.route("/assets")
def assets():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE assigned_to IS NOT NULL")
    data = cur.fetchall()

    return render_template("assets.html", tickets=data)


@app.route("/projects")
def projects():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        CASE 
            WHEN project IS NULL OR project = '' THEN 'No Project'
            ELSE project 
        END,
        COUNT(*)
    FROM tickets
    GROUP BY project
    """)

    data = cur.fetchall()

    return render_template("projects.html", projects=data)


@app.route("/project/<name>")
def project_detail(name):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE project=?", (name,))
    data = cur.fetchall()

    return render_template("project_detail.html", tickets=data, project=name)

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
@app.route("/users")
def users():
    if session.get("role") != "admin":
        return "Access Denied ❌"

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT id, username, role FROM users")
    data = cur.fetchall()

    return render_template("users.html", users=data)
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)