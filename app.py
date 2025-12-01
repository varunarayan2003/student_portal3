# app.py — Streamlit Student Portal (SQLite), no pandas/pyarrow needed
import streamlit as st
import sqlite3
import os
from typing import List, Tuple
import io
import csv

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "student_portal.db")

st.set_page_config(page_title="Student Portal", layout="centered")

# ---------- DB helpers ----------
def init_db():
    """Create DB and a simple table if it doesn't exist."""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO students (name, email) VALUES (?, ?);",
            ("Alice Example", "alice@example.com"),
        )
        conn.commit()
        conn.close()


@st.experimental_singleton
def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def fetch_students(limit: int = 200, search: str = "") -> List[Tuple]:
    q = "SELECT id, name, email FROM students"
    args = []
    if search:
        q += " WHERE name LIKE ? OR email LIKE ?"
        like = f"%{search}%"
        args.extend([like, like])
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    cur = conn.execute(q, tuple(args))
    return cur.fetchall()


def add_student(name: str, email: str) -> int:
    cur = conn.execute(
        "INSERT INTO students (name, email) VALUES (?, ?);",
        (name.strip(), email.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_student(student_id: int, name: str, email: str) -> None:
    conn.execute(
        "UPDATE students SET name = ?, email = ? WHERE id = ?;",
        (name.strip(), email.strip(), student_id),
    )
    conn.commit()


def delete_student(student_id: int) -> None:
    conn.execute("DELETE FROM students WHERE id = ?;", (student_id,))
    conn.commit()


def export_csv_bytes() -> bytes:
    cur = conn.execute(
        "SELECT id, name, email FROM students ORDER BY id DESC;"
    )
    rows = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "email"])
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


# ---------- Init ----------
init_db()
conn = get_conn()

# ---------- UI ----------
st.title("Student Portal — Streamlit (No pandas)")

menu = st.sidebar.radio(
    "Navigation", ["Dashboard", "Add Student", "Export / Backup", "About"]
)

if menu == "Dashboard":
    st.header("Dashboard")
    search = st.text_input("Search by name or email", "")
    limit = st.slider("Max rows to show", 10, 500, 200, step=10)

    rows = fetch_students(limit=limit, search=search)

    if not rows:
        st.info("No students found. Add some via 'Add Student'.")
    else:
        # convert rows to list of dicts for clean table display
        table_data = [
            {"ID": r[0], "Name": r[1], "Email": r[2]} for r in rows
        ]
        st.table(table_data)

        st.markdown("### Edit / Delete")
        ids = [r[0] for r in rows]
        selected = st.selectbox(
            "Select student by ID",
            options=[None] + ids,
            format_func=lambda x: "—" if x is None else str(x),
        )
        if selected is not None:
            r = next((r for r in rows if r[0] == selected), None)
            if r:
                sid, sname, semail = r
                with st.form("edit_form"):
                    new_name = st.text_input("Full name", value=sname)
                    new_email = st.text_input("Email", value=semail)
                    col_u, col_d = st.columns(2)
                    update_btn = col_u.form_submit_button("Update")
                    delete_btn = col_d.form_submit_button("Delete")

                    if update_btn:
                        if not new_name.strip() or not new_email.strip():
                            st.warning("Both name and email are required.")
                        else:
                            update_student(sid, new_name, new_email)
                            st.success("Student updated.")
                            st.experimental_rerun()

                    if delete_btn:
                        delete_student(sid)
                        st.success("Student deleted.")
                        st.experimental_rerun()

elif menu == "Add Student":
    st.header("Add Student")
    with st.form("add_student_form", clear_on_submit=True):
        name = st.text_input("Full name")
        email = st.text_input("Email address")
        submitted = st.form_submit_button("Add student")
        if submitted:
            if not name.strip() or not email.strip():
                st.warning("Please provide both name and email.")
            else:
                new_id = add_student(name, email)
                st.success(f"Added student with ID {new_id}")
                st.experimental_rerun()

elif menu == "Export / Backup":
    st.header("Export & Backup")
    st.write("Download the SQLite DB or a CSV export.")

    # DB file download
    with open(DB_PATH, "rb") as f:
        db_bytes = f.read()
    st.download_button(
        "Download student_portal.db",
        data=db_bytes,
        file_name="student_portal.db",
        mime="application/x-sqlite3",
    )

    # CSV download
    csv_bytes = export_csv_bytes()
    st.download_button(
        "Download students.csv",
        data=csv_bytes,
        file_name="students.csv",
        mime="text/csv",
    )

    # simple count
    cur = conn.execute("SELECT COUNT(*) FROM students;")
    count = cur.fetchone()[0]
    st.write(f"Total students: **{count}**")

elif menu == "About":
    st.header("About")
    st.write(
        "Simple Student Portal built with Streamlit + SQLite, without pandas/pyarrow."
    )

st.markdown("---")
st.write("Database file:", DB_PATH)
