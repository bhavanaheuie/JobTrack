from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DATABASE = "jobtrack.db"

app.secret_key = "jobtrack-secret-key-2026"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            applied_date TEXT NOT NULL
        )
    """)

    columns = conn.execute(
        "PRAGMA table_info(jobs)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "user_id" not in column_names:

        conn.execute(
            "ALTER TABLE jobs ADD COLUMN user_id INTEGER"
        )

    conn.commit()
    conn.close()


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return function(*args, **kwargs)

    return wrapper


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:

            conn.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            return "Email already registered!"

        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if user:

            stored_password = user["password"]

            if stored_password.startswith(("pbkdf2:", "scrypt:")):

                password_correct = check_password_hash(
                    stored_password,
                    password
                )

            else:

                password_correct = stored_password == password

                if password_correct:

                    new_password = generate_password_hash(password)

                    conn.execute(
                        """
                        UPDATE users
                        SET password = ?
                        WHERE id = ?
                        """,
                        (new_password, user["id"])
                    )

                    conn.commit()

            if password_correct:

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]

                conn.close()

                return redirect("/dashboard")

        conn.close()

        return "Invalid email or password"

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    conn = get_db_connection()

    total_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    applied_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
        AND LOWER(status) = 'applied'
        """,
        (user_id,)
    ).fetchone()[0]

    interview_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
        AND LOWER(status) = 'interview'
        """,
        (user_id,)
    ).fetchone()[0]

    selected_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
        AND LOWER(status) = 'selected'
        """,
        (user_id,)
    ).fetchone()[0]

    rejected_jobs = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        WHERE user_id = ?
        AND LOWER(status) = 'rejected'
        """,
        (user_id,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        total_jobs=total_jobs,
        applied_jobs=applied_jobs,
        interview_jobs=interview_jobs,
        selected_jobs=selected_jobs,
        rejected_jobs=rejected_jobs
    )


@app.route("/jobtrack")
@login_required
def jobtrack():

    search = request.args.get("search", "").strip()

    user_id = session["user_id"]

    conn = get_db_connection()

    if search:

        jobs = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE user_id = ?
            AND (
                company LIKE ?
                OR role LIKE ?
                OR status LIKE ?
            )
            ORDER BY id DESC
            """,
            (
                user_id,
                "%" + search + "%",
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        jobs = conn.execute(
            """
            SELECT *
            FROM jobs
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

    conn.close()

    return render_template(
        "jobtrack.html",
        jobs=jobs,
        search=search
    )


@app.route("/add_job", methods=["POST"])
@login_required
def add_job():

    company = request.form["company"].strip()
    role = request.form["role"].strip()
    status = request.form["status"]
    applied_date = request.form["applied_date"]

    user_id = session["user_id"]

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO jobs
        (company, role, status, applied_date, user_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            company,
            role,
            status,
            applied_date,
            user_id
        )
    )

    conn.commit()
    conn.close()

    return redirect("/jobtrack")


@app.route("/edit_job/<int:job_id>", methods=["GET", "POST"])
@login_required
def edit_job(job_id):

    user_id = session["user_id"]

    conn = get_db_connection()

    job = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        AND user_id = ?
        """,
        (job_id, user_id)
    ).fetchone()

    if job is None:

        conn.close()

        return "Job not found or access denied"

    if request.method == "POST":

        company = request.form["company"].strip()
        role = request.form["role"].strip()
        status = request.form["status"]
        applied_date = request.form["applied_date"]

        conn.execute(
            """
            UPDATE jobs
            SET company = ?,
                role = ?,
                status = ?,
                applied_date = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                company,
                role,
                status,
                applied_date,
                job_id,
                user_id
            )
        )

        conn.commit()
        conn.close()

        return redirect("/jobtrack")

    conn.close()

    return render_template(
        "edit_job.html",
        job=job
    )


@app.route("/delete_job/<int:job_id>")
@login_required
def delete_job(job_id):

    user_id = session["user_id"]

    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM jobs
        WHERE id = ?
        AND user_id = ?
        """,
        (job_id, user_id)
    )

    conn.commit()
    conn.close()

    return redirect("/jobtrack")


if __name__ == "__main__":

    create_tables()

    app.run(debug=True)
