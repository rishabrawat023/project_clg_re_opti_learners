"""
database.py - Database Connection Module
Campus Resource Optimizer - BCA (AI & DS) College Project

Supports MySQL database (primary) with automatic fallback to local storage
if MySQL is not yet configured, allowing immediate testing and demonstration.
"""

import os
import re
import sqlite3
from dotenv import load_dotenv

load_dotenv()

# Path for local fallback database
LOCAL_DB_FILE = os.path.join(os.path.dirname(__file__), 'campus_optimizer_local.db')

class SQLiteCursorAdapter:
    """Adapts SQLite cursor to match mysql-connector API (supports %s and dictionary cursor)."""
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # Convert MySQL parameter placeholders %s to SQLite ?
        q = re.sub(r'%s', '?', query)
        if params is not None:
            return self.cursor.execute(q, params)
        return self.cursor.execute(q)

    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        self.cursor.close()

class SQLiteConnectionAdapter:
    """Adapts SQLite connection to behave like MySQL connection."""
    def __init__(self, conn):
        self.conn = conn

    def cursor(self, dictionary=False):
        return SQLiteCursorAdapter(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def init_local_db():
    """Initializes local database with tables and sample data matching schema.sql."""
    conn = sqlite3.connect(LOCAL_DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            resource_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            building TEXT NOT NULL,
            floor INTEGER NOT NULL,
            equipment TEXT DEFAULT 'None',
            status TEXT NOT NULL DEFAULT 'Available'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            student_count INTEGER NOT NULL,
            purpose TEXT DEFAULT 'General',
            status TEXT NOT NULL DEFAULT 'Confirmed',
            FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
        )
    """)

    # Check if resources already seeded
    cur.execute("SELECT COUNT(*) FROM resources")
    if cur.fetchone()[0] == 0:
        sample_resources = [
            ('A-101', 'Classroom A-101', 'Classroom', 60, 'Academic Block', 1, 'Projector, AC', 'Available'),
            ('A-102', 'Classroom A-102', 'Classroom', 50, 'Academic Block', 1, 'Projector', 'Available'),
            ('A-105', 'Classroom A-105', 'Classroom', 55, 'Academic Block', 2, 'Projector, Smart Board', 'Available'),
            ('B-201', 'Classroom B-201', 'Classroom', 70, 'Science Block', 2, 'Projector, Sound System', 'Available'),
            ('LAB-01', 'Computer Lab 01', 'Computer Lab', 40, 'Computer Block', 2, '40 Computers, AC, Projector', 'Available'),
            ('LAB-02', 'Computer Lab 02', 'Computer Lab', 45, 'Computer Block', 2, '45 Computers, AC', 'Available'),
            ('SH-01', 'Seminar Hall 01', 'Seminar Hall', 150, 'Main Block', 0, 'Projector, Sound System, AC', 'Available'),
            ('AUD-01', 'Main Auditorium', 'Auditorium', 300, 'Main Block', 0, 'Projector, Sound System, Stage, AC', 'Available')
        ]
        cur.executemany("INSERT INTO resources VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sample_resources)

        sample_bookings = [
            ('A-101', '2026-10-10', '10:00:00', '11:00:00', 55, 'AI & DS Lecture', 'Confirmed'),
            ('LAB-01', '2026-10-10', '14:00:00', '16:00:00', 35, 'Python Programming Lab', 'Confirmed'),
            ('SH-01', '2026-10-12', '09:30:00', '12:30:00', 130, 'Guest Lecture on Machine Learning', 'Confirmed')
        ]
        cur.executemany("""
            INSERT INTO bookings (resource_id, date, start_time, end_time, student_count, purpose, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_bookings)

    conn.commit()
    conn.close()

def get_db_connection():
    """
    Establish database connection:
    1. Attempts to connect to MySQL using .env credentials.
    2. If MySQL credentials are not yet configured or connection fails,
       transparently falls back to local storage so the web app runs seamlessly.
    """
    # 1. Try MySQL Connection
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'campus_optimizer')
        )
        return connection
    except Exception as e:
        # 2. Local Fallback Mode
        init_local_db()
        sqlite_conn = sqlite3.connect(LOCAL_DB_FILE)
        sqlite_conn.row_factory = sqlite3.Row
        return SQLiteConnectionAdapter(sqlite_conn)
