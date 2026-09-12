import sqlite3
from notifications import send_email

def check_blacklist(plate_text):
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    blacklist_entry = c.execute(
        'SELECT reason, severity FROM blacklist WHERE plate_text = ?', 
        (plate_text,)
    ).fetchone()
    
    conn.close()
    
    if blacklist_entry:
        reason, severity = blacklist_entry
        print("BLACKLIST HIT: " + plate_text + " - " + reason)
        
        send_email(
            'admin@vehicletrack.com',
            'BLACKLIST ALERT: ' + plate_text,
            'Plate: ' + plate_text + '\nReason: ' + reason + '\nSeverity: ' + severity
        )
        return True
    
    return False

def add_to_blacklist(plate_text, reason, severity='high'):
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO blacklist VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
              (plate_text, reason, severity))
    conn.commit()
    conn.close()
    print("Added " + plate_text + " to blacklist")

def check_repeat_offender(plate_text):
    conn = sqlite3.connect('violations.db')
    c = conn.cursor()
    
    count = c.execute('''
        SELECT COUNT(*) FROM violations 
        WHERE plate = ? 
        AND timestamp > datetime('now', '-7 days')
    ''', (plate_text,)).fetchone()[0]
    
    conn.close()
    
    if count >= 3:
        print("REPEAT OFFENDER: " + plate_text + " caught " + str(count) + " times this week")
        send_email(
            'admin@vehicletrack.com',
            'REPEAT OFFENDER: ' + plate_text,
            'This vehicle has ' + str(count) + ' violations in 7 days.'
        )
        return True
    
    return False

def trigger_on_violation_detection(plate_text, violation_type):
    if check_blacklist(plate_text):
        return
    check_repeat_offender(plate_text)
