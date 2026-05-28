import os
import json
from datetime import datetime
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__, template_folder='.')
app.secret_key = "fixify_super_cloud_secure_key_99"

# SUPABASE CLOUD CONNECTION
SUPABASE_URL = "https://wgkdrknsynjipoynjof.supabase.co"
SUPABASE_KEY = "sb_publishable_3i7z0XcrCNuCgL8C3KTP3g_TnrCEz4i64vKms9vVj9BWh3v9W"

ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"

def make_supabase_request(url, method="GET", data=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    req_data = None
    if data:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, headers=headers, method=method, data=req_data)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Supabase Error:", e)
        return []

@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('index.html', show_login=True)
    return render_template('index.html', show_login=False)

@app.route('/api/login', methods=['POST'])
def do_login():
    data = request.json or {}
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Galat ID ya Password bhai!"})

@app.route('/api/logout', methods=['POST'])
def do_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json
        
        # Pull data safely using native urllib
        count_url = f"{SUPABASE_URL}/rest/v1/jobs?select=id"
        all_rows = make_supabase_request(count_url, method="GET")
        next_num = len(all_rows) + 1 if isinstance(all_rows, list) else 1
        
        next_id = f"FIX{next_num:04d}"
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        payload = {
            "id": next_id, "category": data.get('category'), "name": data.get('name'),
            "phone1": data.get('phone1'), "device": data.get('device'), "imei": data.get('imei',''),
            "password": data.get('password',''), "problem": data.get('problem'),
            "estimate": float(data.get('estimate', 0)), "advance": float(data.get('advance', 0)),
            "extra_cost": 0.0, "discount": 0.0, "created_date": today_str, "status": "Pending"
        }
        
        insert_url = f"{SUPABASE_URL}/rest/v1/jobs"
        make_supabase_request(insert_url, method="POST", data=payload)
        return jsonify({"success": True, "id": next_id})
        
    # GET Method
    fetch_url = f"{SUPABASE_URL}/rest/v1/jobs?select=*"
    rows = make_supabase_request(fetch_url, method="GET")
    jobs = []
    if isinstance(rows, list):
        for r in rows:
            jobs.append({
                "id": r.get('id'), "category": r.get('category'), "name": r.get('name'),
                "phone1": r.get('phone1'), "device": r.get('device'), "estimate": r.get('estimate'),
                "advance": r.get('advance'), "extra_cost": r.get('extra_cost'), "discount": r.get('discount'),
                "date": r.get('created_date'), "status": r.get('status')
            })
    return jsonify(jobs)

@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{data.get('id')}"
    make_supabase_request(url, method="PATCH", data={"status": data.get('status')})
    return jsonify({"success": True})

@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{data.get('id')}"
    payload = {"extra_cost": float(data.get('extra_cost', 0)), "discount": float(data.get('discount', 0))}
    make_supabase_request(url, method="PATCH", data=payload)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
