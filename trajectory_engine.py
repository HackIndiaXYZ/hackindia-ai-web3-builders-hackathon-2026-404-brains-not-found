import sqlite3
from datetime import datetime, timedelta
import uuid
from geopy.distance import geodesic

def match_plates_across_cameras(time_window_sec=600, max_distance_km=2.0):
    """
    Match same plate detected at different cameras within time window
    and distance threshold
    """
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    detections = c.execute('''
        SELECT v.plate, v.video, v.timestamp, c.latitude, c.longitude
        FROM violations v
        LEFT JOIN cameras c ON (v.video = c.id OR v.video = c.name)
        WHERE c.latitude IS NOT NULL
        AND v.timestamp > datetime('now', '-7 days')
        ORDER BY v.plate, v.timestamp ASC
    ''').fetchall()
    
    # Also fetch from trajectory_points if any
    tp_detections = c.execute('''
        SELECT tp.plate_text, tp.camera_id, tp.timestamp, COALESCE(tp.latitude, c.latitude), COALESCE(tp.longitude, c.longitude)
        FROM trajectory_points tp
        LEFT JOIN cameras c ON tp.camera_id = c.id
        WHERE (tp.latitude IS NOT NULL OR c.latitude IS NOT NULL)
        AND tp.timestamp > datetime('now', '-7 days')
        ORDER BY tp.plate_text, tp.timestamp ASC
    ''').fetchall()
    
    all_detections = list(detections) + [
        (p, cid, ts, lat, lng) for (p, cid, ts, lat, lng) in tp_detections if lat is not None and lng is not None
    ]
    
    plate_detections = {}
    for plate, camera_id, timestamp, lat, lng in all_detections:
        if not plate or plate == "UNKNOWN":
            continue
        if plate not in plate_detections:
            plate_detections[plate] = []
        plate_detections[plate].append({
            'camera_id': camera_id,
            'timestamp': timestamp,
            'lat': lat,
            'lng': lng
        })
    
    trajectory_count = 0
    for plate, detections_list in plate_detections.items():
        for i, detection1 in enumerate(detections_list[:-1]):
            detection2 = detections_list[i + 1]
            
            dist = geodesic(
                (detection1['lat'], detection1['lng']),
                (detection2['lat'], detection2['lng'])
            ).km
            
            time1 = datetime.fromisoformat(detection1['timestamp'])
            time2 = datetime.fromisoformat(detection2['timestamp'])
            time_gap = (time2 - time1).total_seconds()
            
            if dist < max_distance_km and time_gap < time_window_sec:
                traj_id = str(uuid.uuid4())[:8]
                
                c.execute('''INSERT INTO trajectories VALUES 
                    (?, ?, ?, ?, ?, ?, ?)''',
                    (traj_id, plate, 
                     detection1['camera_id'], detection1['timestamp'],
                     detection2['camera_id'], detection2['timestamp'],
                     dist))
                
                c.execute('''INSERT INTO trajectory_points VALUES 
                    (NULL, ?, ?, ?, ?, ?, ?)''',
                    (traj_id, detection1['camera_id'], plate, 
                     detection1['lat'], detection1['lng'], detection1['timestamp']))
                
                c.execute('''INSERT INTO trajectory_points VALUES 
                    (NULL, ?, ?, ?, ?, ?, ?)''',
                    (traj_id, detection2['camera_id'], plate,
                     detection2['lat'], detection2['lng'], detection2['timestamp']))
                
                trajectory_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"Created {trajectory_count} trajectories")
    return trajectory_count

def compute_heatmap(grid_size_m=500):
    """
    Create traffic density heatmap by dividing city into grid cells
    """
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    violations = c.execute('''
        SELECT v.timestamp, c.latitude, c.longitude
        FROM violations v
        LEFT JOIN cameras c ON (v.video = c.id OR v.video = c.name)
        WHERE c.latitude IS NOT NULL
        AND v.timestamp > datetime('now', '-1 day')
    ''').fetchall()
    
    tp_points = c.execute('''
        SELECT tp.timestamp, COALESCE(tp.latitude, c.latitude), COALESCE(tp.longitude, c.longitude)
        FROM trajectory_points tp
        LEFT JOIN cameras c ON tp.camera_id = c.id
        WHERE (tp.latitude IS NOT NULL OR c.latitude IS NOT NULL)
        AND tp.timestamp > datetime('now', '-1 day')
    ''').fetchall()
    
    all_points = list(violations) + [
        (ts, lat, lng) for (ts, lat, lng) in tp_points if lat is not None and lng is not None
    ]
    
    grid_deg = grid_size_m / 111000
    
    heatmap = {}
    for timestamp, lat, lng in all_points:
        grid_lat = round(lat / grid_deg) * grid_deg
        grid_lng = round(lng / grid_deg) * grid_deg
        key = (grid_lat, grid_lng)
        
        if key not in heatmap:
            heatmap[key] = 0
        heatmap[key] += 1
    
    c.execute("DELETE FROM heatmap_cells")
    for (grid_lat, grid_lng), count in heatmap.items():
        c.execute('''INSERT INTO heatmap_cells VALUES 
            (NULL, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (grid_lat, grid_lng, count))
    
    conn.commit()
    conn.close()
    
    print(f"Heatmap: {len(heatmap)} cells computed")
    return heatmap
