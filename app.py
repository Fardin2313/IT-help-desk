from flask import Flask, render_template, request, redirect, session
import psycopg2, os, datetime, bcrypt

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---------------- INIT DB ----------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets(
        id SERIAL PRIMARY KEY,
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

# ---------------- GLOBAL NOTIFICATION ----------------
@app.context_processor
def inject_notif():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    notif = cur.fetchone()[0]

    conn.close()
    return dict(notif=notif)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=%s", (user,))
        data = cur.fetchone()

        # user exist
        if data:
            db_pwd = data[2]

            if bcrypt.checkpw(pwd.encode(), db_pwd.encode()):
                session["user"] = data[1]
                session["role"] = data[3]
                conn.close()
                return redirect("/dashboard")

        # user not exist → create
        hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(%s,%s,%s)",
            (user, hashed, "admin")
        )

        conn.commit()

        session["user"] = user
        session["role"] = "admin"

        conn.close()
        return redirect("/dashboard")

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tickets")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    open_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE status='Closed'")
    closed_t = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM tickets WHERE assigned_to IS NOT NULL")
    assigned = cur.fetchone()[0]

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

    conn.close()

    return render_template("dashboard.html",
        total=total,
        open_t=open_t,
        closed_t=closed_t,
        assigned=assigned,
        overdue=overdue
    )

# ---------------- TICKETS ----------------
@app.route("/tickets")
def tickets():
    q = request.args.get("q")

    conn = get_conn()
    cur = conn.cursor()

    if q:
        cur.execute("""
        SELECT * FROM tickets 
        WHERE LOWER(title) LIKE LOWER(%s)
        OR LOWER(description) LIKE LOWER(%s)
        """, ('%' + q + '%', '%' + q + '%'))
    else:
        cur.execute("SELECT * FROM tickets")

    data = cur.fetchall()
    conn.close()

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

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO tickets(title,description,status,created_at,deadline,project)
        VALUES(%s,%s,'Open',%s,%s,%s)
        """, (title, desc, str(now), str(deadline), project))

        conn.commit()
        conn.close()

        return redirect("/tickets")

    return render_template("create.html")

# ---------------- ASSIGN ----------------
@app.route("/assign/<int:id>", methods=["POST"])
def assign(id):
    agent = request.form["agent"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE tickets SET assigned_to=%s WHERE id=%s", (agent, id))

    conn.commit()
    conn.close()

    return redirect("/tickets")

# ---------------- STATUS ----------------
@app.route("/status/<int:id>", methods=["POST"])
def status(id):
    status = request.form["status"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE tickets SET status=%s WHERE id=%s", (status, id))

    conn.commit()
    conn.close()

    return redirect("/tickets")

# ---------------- PROJECTS ----------------
@app.route("/projects")
def projects():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT project, COUNT(*) 
    FROM tickets 
    GROUP BY project
    """)

    data = cur.fetchall()
    conn.close()

    return render_template("projects.html", projects=data)

# ---------------- PROJECT DETAIL ----------------
@app.route("/project/<name>")
def project_detail(name):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tickets WHERE project=%s", (name,))
    data = cur.fetchall()

    conn.close()

    return render_template("project_detail.html", tickets=data, project=name)
@app.route("/users")
def users():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, username, role FROM users")
    data = cur.fetchall()

    conn.close()

    return render_template("users.html", users=data)
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()