import sqlite3

conn = sqlite3.connect("jobtrack.db")

print("Total jobs:", conn.execute(
    "SELECT COUNT(*) FROM jobs"
).fetchone()[0])

print("Applied:", conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE status = 'Applied'"
).fetchone()[0])

print("Interview:", conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE status = 'Interview'"
).fetchone()[0])

print("Selected:", conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE status = 'Selected'"
).fetchone()[0])

print("Rejected:", conn.execute(
    "SELECT COUNT(*) FROM jobs WHERE status = 'Rejected'"
).fetchone()[0])

conn.close()
