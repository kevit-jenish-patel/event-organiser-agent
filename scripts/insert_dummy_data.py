import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List

from dotenv import load_dotenv

load_dotenv()

DB_PATH = "test.db"  # update if needed

EVENT_STATUSES = ["open", "full", "closed", "completed", "cancelled"]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Pune", "Ahmedabad", "Kolkata"
]

EVENT_TYPES = [
    "Music Festival", "Tech Conference", "Startup Meetup",
    "Art Exhibition", "Food Carnival", "Workshop",
    "Comedy Show", "Networking Event"
]


# -------------------------
# DB CONNECTION
# -------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# -------------------------
# GENERATE USERS
# -------------------------
def generate_users(n: int) -> List[tuple]:
    users = []
    for i in range(1, n + 1):
        name = f"User {i}"
        email = f"user{i}@example.com"
        password = "password123"
        users.append((name, email, password))
    return users


# -------------------------
# GENERATE EVENTS
# -------------------------
def generate_events(n: int, user_ids: List[int]) -> List[tuple]:
    events = []

    for _ in range(n):
        name = random.choice(EVENT_TYPES)
        description = f"This is a {name.lower()} event."

        # Generate future dates (within next 60 days)
        future_days = random.randint(1, 60)
        date = datetime.now(timezone.utc) + timedelta(days=future_days)
        date_str = date.strftime("%Y-%m-%dT%H:%M:%SZ")

        location = random.choice(CITIES)
        organiser_id = random.choice(user_ids)
        status = random.choice(EVENT_STATUSES)

        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        updated_at = None

        events.append((
            name,
            description,
            date_str,
            location,
            organiser_id,
            status,
            created_at,
            updated_at
        ))

    return events


# -------------------------
# INSERT DATA
# -------------------------
def insert_users(conn, users: List[tuple]):
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO users (name, email, password)
        VALUES (?, ?, ?)
        """,
        users
    )
    conn.commit()


def insert_events(conn, events: List[tuple]):
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO events (name, description, date, location,
                            organiser_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        events
    )
    conn.commit()


# -------------------------
# MAIN SCRIPT
# -------------------------
def main():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users
        (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT        NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT        NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events
        (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            description  TEXT    NOT NULL,
            date         TEXT    NOT NULL,
            location     TEXT    NOT NULL,
            organiser_id INTEGER NOT NULL,
            status       TEXT DEFAULT 'OPEN',
            created_at   TEXT    NOT NULL,
            updated_at   TEXT,
            FOREIGN KEY (organiser_id) REFERENCES users (id)
        );
        """
    )
    conn.commit()

    # Generate data
    users = generate_users(10)
    insert_users(conn, users)

    # Fetch inserted user IDs
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]

    events = generate_events(50, user_ids)
    insert_events(conn, events)

    print("✅ Dummy data inserted successfully!")

    conn.close()


if __name__ == "__main__":
    main()
