import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')
DB_PATH = "fixify_shop.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Direct matching matrix configuration fields
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*), SUM(estimate + extra_cost - discount) FROM jobs GROUP BY status")
    rows = cursor.fetchall()
    
    stats = {"Total": 0, "Pending": 0, "Ready": 0, "Delivered": 0, "Sales": 0.0}
    for row in rows:
        status, count, total_net = row
        if status in ["Pending", "Repairing", "Testing"]:
            stats["Pending"] += count
        elif status == "Ready":
            stats["Ready"] = count
        elif status == "Delivered":
            stats["Delivered"] = count
            stats["Sales"] = total_net or 0.0
        stats["Total"] += count
            
    conn.close()
    return jsonify(stats)

@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        cursor.execute("SELECT COUNT(*) FROM jobs")
        next_num = cursor.fetchone()[0] + 1
        next_id = f"FIX{next_num:04d}"
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        est = float(data.get('estimate', 0))
        adv = float(data.get('advance', 0))
        
        cursor.execute('''INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'Pending')''', 
                       (next_id, data.get('category','MOBILE'), data['name'], data['phone1'], data['device'],
                        data.get('imei',''), data.get('password',''), data['problem'], est, adv, today_str))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": next_id})
        
    cursor.execute("SELECT id, category, name, phone1, device, imei, password, problem, estimate, advance, extra_cost, discount, created_date, status FROM jobs")
    jobs = []
    for r in cursor.fetchall():
        jobs.append({
            "id": r[0], "category": r[1], "name": r[2], "phone": r[3], "device": r[4],
            "imei": r[5], "password": r[6], "problem": r[7], "cost": r[8], "advance": r[9],
            "extra_cost": r[10], "discount": r[11], "date": r[12], "status": r[13]
        })
    conn.close()
    return jsonify(jobs)

@app.route('/api/jobs/update_cost', methods=['POST'])
def update_cost():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET estimate=?, extra_cost=?, discount=? WHERE id=?",
                   (float(data['cost']), float(data['extra_cost']), float(data['discount']), data['id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/jobs/update', methods=['POST'])
def update_status():
    data = request.json
    status = data['status']
    job_id = data['id']
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    init_db()
app.run(host='0.0.0.0', port=5000)
