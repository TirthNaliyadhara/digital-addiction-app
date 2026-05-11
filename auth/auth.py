import sqlite3
import hashlib
import os
import streamlit as st
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'User',
        email TEXT,
        created_at TEXT,
        full_name TEXT
    )''')
    # Seed admin
    admin_hash = hash_password("admin123")
    try:
        c.execute("INSERT INTO users (username, password_hash, role, email, full_name, created_at) VALUES (?,?,?,?,?,?)",
                  ("admin", admin_hash, "Admin", "admin@system.ai", "System Admin", datetime.now().isoformat()))
    except:
        pass
    # Seed parent
    parent_hash = hash_password("parent123")
    try:
        c.execute("INSERT INTO users (username, password_hash, role, email, full_name, created_at) VALUES (?,?,?,?,?,?)",
                  ("parent", parent_hash, "Parent", "parent@system.ai", "Demo Parent", datetime.now().isoformat()))
    except:
        pass
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def signup_user(username, password, role, email, full_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, role, email, full_name, created_at) VALUES (?,?,?,?,?,?)",
                  (username, hash_password(password), role, email, full_name, datetime.now().isoformat()))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    if user:
        return True, {"id": user[0], "username": user[1], "role": user[3], "email": user[4], "full_name": user[6]}
    return False, None

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, role, email, full_name, created_at FROM users")
    users = c.fetchall()
    conn.close()
    return users

def logout():
    for key in ['logged_in', 'user_info']:
        if key in st.session_state:
            del st.session_state[key]
