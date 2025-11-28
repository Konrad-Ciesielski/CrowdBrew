import sqlite3
import json
import os
from datetime import datetime

# Unification of the database saving path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_NAME = os.path.join(DATA_DIR, 'crowdbrew.db')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Initializes the database tables if they do not exist."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        # 1. Events Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            name TEXT,
            location TEXT,
            description TEXT,
            UNIQUE(date, name)
        )
        """)

        # 2. Menu Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            item_name TEXT,
            item_description TEXT,
            item_type TEXT,
            created_at TEXT,
            FOREIGN KEY(event_id) REFERENCES Events(id),
            UNIQUE(event_id, item_name)
        )
        """)

        # 3. Posts Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(event_id) REFERENCES Events(id),
            UNIQUE(event_id, content)
        )
        """)
        conn.commit()


def add_event(date, name, location, description):
    """Adds a new event only if a similar one doesn't exist for that date."""
    
    def normalize(text):
        return text.lower().strip().strip('.').strip()
    
    normalized_new_name = normalize(name)

    with get_connection() as conn:
        cur = conn.cursor()
        
        #1. Retrieving all events for this specific date
        cur.execute("SELECT id, name FROM Events WHERE date = ?", (date,))
        existing_events = cur.fetchall()
        
        # 2. Check if a similar event already exists
        for db_id, db_name in existing_events:
            normalized_db_name = normalize(db_name)

            if normalized_new_name in normalized_db_name or normalized_db_name in normalized_new_name:
                print(f"   (i) Duplicate detected: '{name}' fits to '{db_name}' (ID: {db_id})")
                return db_id
         
        # 3. Adding an entry if no duplicates are detected
        try:
            print(f"   (+) Adding a new event: '{name}'")
            cur.execute(
                'INSERT OR IGNORE INTO Events (date, name, location, description) VALUES (?, ?, ?, ?)',
                (date, name, location, description)
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Fallback in case of perfect duplicate caught by SQL
            cur.execute('SELECT id FROM Events WHERE date = ? AND name = ?', (date, name))
            result = cur.fetchone()
            return result[0] if result else None


def add_marketing_bundle(event_id, json_data):
    """Parses JSON output from the agent and saves menu items and posts."""
    if not event_id:
        return
    
    # Checking if this event already has a post/menu assigned
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM Posts WHERE event_id = ?", (event_id,))
        if cur.fetchone():
            print(f"   🛑 Event ID {event_id} has already generated menu and post. Saving skipped.")
            return

    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            print(f"Error parsing JSON data for event_id {event_id}")
            return
    else:
        data = json_data

    current_date_str = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        cur = conn.cursor()
        
        # 1. Save Post
        post_content = data.get("facebook_post", "")
        if post_content:
            cur.execute(
                'INSERT OR IGNORE INTO Posts (event_id, content, created_at) VALUES (?, ?, ?)',
                (event_id, post_content, current_date_str)
            )
        
        # 2. Save Menu Items
        items = data.get("menu_items", [])
        for item in items:
            cur.execute(
                'INSERT OR IGNORE INTO Menu (event_id, item_name, item_description, item_type, created_at) VALUES (?, ?, ?, ?, ?)',
                (
                    event_id, 
                    item.get("name", ""), 
                    item.get("desc", ""), 
                    item.get("type", "other"),
                    current_date_str
                )
            )
        conn.commit()