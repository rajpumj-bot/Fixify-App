import os
import json
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse
import uuid
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='.')
app.secret_key = "fixify_super_cloud_secure_key_99"

SUPABASE_URL = "[https://wgkdrknsynjipoynjof.supabase.co](https://wgkdrknsynjipoynjof.supabase.co)"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"

def make_supabase_request(url, method="GET", data=None):
    if not SUPABASE_KEY:
        print("❌ CRITICAL ERROR: SUPABASE_KEY environment variable missing on Render!")
        return None
        
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if req_data:
        headers["Content-Length"] = str(len(req_data))
        
    req = urllib.request.Request(url, headers=headers, method=method, data=req_data)
    try:
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode("utf-8")
            print("✅ SUPABASE SUCCESS")
            return json.loads(response_text) if response_text else []
    except urllib.error.HTTPError as e:
        print("❌ SUPABASE HTTP ERROR")
        print("STATUS:", e.code)
        try:
            error_body = e.read().decode()
            print("BODY:", error_body)
        except Exception as ex:
            print("READ ERROR:", str(ex))
        return None
    except Exception as e:
        print("❌ GENERAL ERROR:", str(e))
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/session', methods=['GET'])
def get_session():
    if not session.get('logged_in'):
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "role": session.get('role', 'Employee'),
        "emp_name": session.get('emp_name', 'Staff')
    })

@app.route('/api/login', methods=['POST'])
def do_login():
    data = request.json or {}
    u = data.get('username', '').strip()
    p = data.get('password', '').strip()
    
    if u == ADMIN_USER and p == ADMIN_PASS:
        session['logged_in'] = True
        session['username'] = ADMIN_USER
        session['role'] = "Chairman"
        session['emp_name'] = "Chairman Master"
        return jsonify({"success": True, "role": "Chairman", "emp_name": "Chairman Master"})
        
    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(u)}"
    user_rows = make_supabase_request(url, method="GET")
    
    if isinstance(user_rows, list) and len(user_rows) > 0:
        db_user = user_rows[0]
        if check_password_hash(db_user.get('password'), p):
            session['logged_in'] = True
            session['username'] = db_user.get('username')
            session['role'] = db_user.get('role')
            session['emp_name'] = db_user.get('emp_name')
            return jsonify({"success": True, "role": db_user.get('role'), "emp_name": db_user.get('emp_name')})
            
    return jsonify({"success": False, "message": "Galat ID ya Password bhai!"})

@app.route('/api/logout', methods=['POST'])
def do_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/parts', methods=['GET', 'POST', 'DELETE'])
def handle_parts():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        try: w_cost = float(data.get('wholesale_cost', 0) or 0)
        except: w_cost = 0.0
            
        payload = [{
            "part_name": str(data.get('part_name', 'Part')),
            "model_compatibility": str(data.get('model_compatibility', '')),
            "wholesale_cost": w_cost,
            "updated_at": today_str
        }]
        
        url = f"{SUPABASE_URL}/rest/v1/fixify_parts"
        result = make_supabase_request(url, method="POST", data=payload)
        
        if result is None:
            return jsonify({"success": False, "message": "Part save failed"})
        return jsonify({"success": True})
        
    if request.method == 'DELETE':
        if session.get('role') != 'Chairman':
            return jsonify({"success": False, "message": "Access Denied: Only Chairman can delete records!"}), 401
            
        part_id = request.args.get('id')
        url = f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}"
        make_supabase_request(url, method="DELETE")
        return jsonify({"success": True})

    url = f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*"
    rows = make_supabase_request(url, method="GET")
    return jsonify(rows if isinstance(rows, list) else [])

@app.route('/api/employees', methods=['GET', 'POST', 'DELETE'])
def handle_employees():
    if not session.get('logged_in') or session.get('role') != 'Chairman':
        return jsonify({"error": "Unauthorized Access"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        hashed_password = generate_password_hash(str(data.get('password', '')).strip())
        
        payload = [{
            "username": str(data.get('username', '')).strip(),
            "password": hashed_password,
            "emp_name": str(data.get('emp_name', '')).strip(),
            "role": "Employee"
        }]
        url = f"{SUPABASE_URL}/rest/v1/fixify_users"
        make_supabase_request(url, method="POST", data=payload)
        return jsonify({"success": True})
        
    if request.method == 'DELETE':
        username = request.args.get('username')
        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(username)}"
        make_supabase_request(url, method="DELETE")
        return jsonify({"success": True})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?select=username,emp_name,role"
    rows = make_supabase_request(url, method="GET")
    return jsonify(rows if isinstance(rows, list) else [])

@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        unique_token = uuid.uuid4().hex[:6].upper()
        next_id = f"FIX-{unique_token}"
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try: est = float(data.get('estimate', 0) or 0)
        except: est = 0.0
        try: adv = float(data.get('advance', 0) or 0)
        except: adv = 0.0
        
        payload = [{
            "id": str(next_id), "category": str(data.get('category', 'Mobile')), "name": str(data.get('name', '')),
            "phone1": str(data.get('phone1', '')), "device": str(data.get('device', '')), "imei": str(data.get('imei', '')),
            "password": str(data.get('password', '')), "problem": str(data.get('problem', '')),
            "estimate": est, "advance": adv, "extra_cost": 0.0, "discount": 0.0, "spare_part_cost": 0.0,
            "created_date": str(today_str), "status": "Pending", "created_by": str(session.get('emp_name', 'Staff'))
        }]
        
        insert_url = f"{SUPABASE_URL}/rest/v1/fixify_jobs"
        result = make_supabase_request(insert_url, method="POST", data=payload)
        
        if result is None:
            return jsonify({"success": False, "message": "Database write protection failure"})
            
        return jsonify({"success": True, "id": next_id})
        
    fetch_url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*"
    rows = make_supabase_request(fetch_url, method="GET")
    jobs = []
    if isinstance(rows, list):
        for r in rows:
            try: est_val = float(r.get('estimate', 0) or 0)
            except: est_val = 0.0
            try: adv_val = float(r.get('advance', 0) or 0)
            except: adv_val = 0.0
            try: ext_val = float(r.get('extra_cost', 0) or 0)
            except: ext_val = 0.0
            try: dsc_val = float(r.get('discount', 0) or 0)
            except: dsc_val = 0.0
            try: spc_val = float(r.get('spare_part_cost', 0) or 0)
            except: spc_val = 0.0
                
            jobs.append({
                "id": str(r.get('id', '')), "category": str(r.get('category', 'Mobile')), "name": str(r.get('name', '')),
                "phone1": str(r.get('phone1', '')), "device": str(r.get('device', '')), "problem": str(r.get('problem', '')),
                "estimate": est_val, "advance": adv_val, "extra_cost": ext_val, "discount": dsc_val, "spare_part_cost": spc_val,
                "date": str(r.get('created_date', '')), "status": str(r.get('status', 'Pending')),
                "created_by": str(r.get('created_by', 'Staff'))
            })
    return jsonify(jobs)

@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data.get('id')}"
    make_supabase_request(url, method="PATCH", data={"status": str(data.get('status'))})
    return jsonify({"success": True})

@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data.get('id')}"
    
    try: ext = float(data.get('extra_cost', 0) or 0)
    except: ext = 0.0
    try: dsc = float(data.get('discount', 0) or 0)
    except: dsc = 0.0
    try: spc = float(data.get('spare_part_cost', 0) or 0)
    except: spc = 0.0
        
    payload = {"extra_cost": ext, "discount": dsc, "spare_part_cost": spc}
    make_supabase_request(url, method="PATCH", data=payload)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
