import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')
DB_PATH = "fixify_shop.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, category TEXT, name TEXT, phone1 TEXT, device TEXT,
            imei TEXT, password TEXT, problem TEXT,
            estimate REAL, advance REAL, extra_cost REAL, discount REAL,
            created_date TEXT, status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    if request.method == 'POST':
        data = request.json
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        next_num = cursor.fetchone()[0] + 1
        next_id = f"FIX{next_num:04d}"
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute('''INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'Pending')''',
                       (next_id, data.get('category'), data.get('name'), data.get('phone1'), data.get('device'),
                        data.get('imei',''), data.get('password',''), data.get('problem'),
                        float(data.get('estimate', 0)), float(data.get('advance', 0)), today_str))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": next_id})
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, name, phone1, device, estimate, advance, extra_cost, discount, created_date, status FROM jobs")
    jobs = []
    for r in cursor.fetchall():
        jobs.append({
            "id": r[0], "category": r[1], "name": r[2], "phone1": r[3], "device": r[4],
            "estimate": r[5], "advance": r[6], "extra_cost": r[7] or 0, "discount": r[8] or 0,
            "date": r[9], "status": r[10]
        })
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (data.get('status'), data.get('id')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET extra_cost = ?, discount = ? WHERE id = ?", 
                   (float(data.get('extra_cost', 0)), float(data.get('discount', 0)), data.get('id')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
