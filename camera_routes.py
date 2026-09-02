from flask import Blueprint, request, jsonify
import sqlite3
import uuid

bp = Blueprint('cameras', __name__)

@bp.route('/admin/cameras/add', methods=['POST'])
def add_camera():
    data = request.json
    cam_id = str(uuid.uuid4())[:8]
    
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    c.execute('''INSERT INTO cameras VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
              (cam_id, data['name'], data['lat'], data['lng'], 
               data.get('rtsp_url', ''), data.get('sector', '')))
    conn.commit()
    conn.close()
    
    return jsonify({'camera_id': cam_id, 'status': 'created'})

@bp.route('/admin/cameras/list', methods=['GET'])
def list_cameras():
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    cameras = c.execute('SELECT id, name, latitude, longitude, sector FROM cameras').fetchall()
    conn.close()
    
    return jsonify([{
        'id': cam[0],
        'name': cam[1],
        'lat': cam[2],
        'lng': cam[3],
        'sector': cam[4]
    } for cam in cameras])

@bp.route('/api/trajectory/search', methods=['GET'])
def search_plate():
    plate = request.args.get('plate')
    
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    points = c.execute('''
        SELECT tp.camera_id, tp.latitude, tp.longitude, tp.timestamp, cm.name
        FROM trajectory_points tp
        LEFT JOIN cameras cm ON tp.camera_id = cm.id
        WHERE tp.plate_text = ?
        ORDER BY tp.timestamp ASC
    ''', (plate,)).fetchall()
    
    conn.close()
    
    if not points:
        return jsonify({'plate': plate, 'trajectory': [], 'message': 'No sightings found'})
    
    features = []
    for point in points:
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [point[2], point[1]]},
            'properties': {'camera': point[4], 'time': point[3]}
        })
    
    return jsonify({
        'plate': plate,
        'trajectory': {
            'type': 'FeatureCollection',
            'features': features
        }
    })
