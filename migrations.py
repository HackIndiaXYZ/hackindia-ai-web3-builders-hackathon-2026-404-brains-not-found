import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'violations.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Table 1: Cameras with GPS coordinates
c.execute('''CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    latitude REAL,
    longitude REAL,
    rtsp_url TEXT,
    sector TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Table 2: Trajectories - link same plate across cameras
c.execute('''CREATE TABLE IF NOT EXISTS trajectories (
    id TEXT PRIMARY KEY,
    plate_text TEXT,
    camera_start_id TEXT,
    time_start TIMESTAMP,
    camera_end_id TEXT,
    time_end TIMESTAMP,
    distance_km REAL,
    FOREIGN KEY(camera_start_id) REFERENCES cameras(id),
    FOREIGN KEY(camera_end_id) REFERENCES cameras(id)
)''')

# Table 3: Trajectory Points - each detection along journey
c.execute('''CREATE TABLE IF NOT EXISTS trajectory_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trajectory_id TEXT,
    camera_id TEXT,
    plate_text TEXT,
    latitude REAL,
    longitude REAL,
    timestamp TIMESTAMP,
    FOREIGN KEY(trajectory_id) REFERENCES trajectories(id),
    FOREIGN KEY(camera_id) REFERENCES cameras(id)
)''')

# Table 4: Blacklist
c.execute('''CREATE TABLE IF NOT EXISTS blacklist (
    plate_text TEXT PRIMARY KEY,
    reason TEXT,
    severity TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

# Table 5: Heatmap cells
c.execute('''CREATE TABLE IF NOT EXISTS heatmap_cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_lat REAL,
    grid_lng REAL,
    vehicle_count INTEGER,
    timestamp_hour TIMESTAMP
)''')

conn.commit()
conn.close()
print("Database tables created successfully")
