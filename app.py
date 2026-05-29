import os
import json
from datetime import datetime
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__, template_folder='.')
app.secret_key = "fixify_super_cloud_secure_key_99"

# SUPABASE CLOUD CONNECTION INFO
SUPABASE_URL = "https://wgkdrknsynjipoynjof.supabase.co"
SUPABASE_KEY = "sb_publishable_3i7z0XcrCNuCgL8C3KTP3g_TnrCEz4i64vKms9vVj9BWh3v9W"

ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"  # Aap apna password yahan badal sakte ho bhai

def make_supabase_request(url, method="GET", data=None):
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # POST aur PATCH ke liye Representation return mandatory hai
    if method in ["POST", "PATCH"]:
        headers["Prefer"] = "return=representation"
        
    if req_data:
        headers["Content-Length"] = str(len(req_data))
        
    req = urllib.request.Request(url, headers=headers, method=method, data=req_data)
    try:
        with urllib.request.urlopen(req) as response:
            res_read = response.read().decode("utf-8")
            if res_read:
                return json.loads(res_read)
            return []
    except Exception as e:
        print("Supabase Fatal Network Log:", e)
        return None

@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('index.html', show_login=True)
    return render_template('index.html', 
                           show_login=False, 
                           user_role=session.get('role', 'Employee'), 
                           emp_name=session.get('emp_name', 'Staff'))

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
        if db_user.get('password') == p:
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

# --- SPARE PARTS RATES MANAGER API ---
@app.route('/api/parts', methods=['GET', 'POST', 'DELETE'])
def handle_parts():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Strict float numbers formatting for database
        try:
            w_cost = float(data.get('wholesale_cost', 0) or 0)
        except:
            w_cost = 0.0
            
        payload = {
            "part_name": str(data.get('part_name', 'Unnamed Part')),
            "model_compatibility": str(data.get('model_compatibility', '')),
            "wholesale_cost": w_cost,
            "updated_at": today_str
        }
        url = f"{SUPABASE_URL}/rest/v1/fixify_parts"
        make_supabase_request(url, method="POST", data=payload)
        return jsonify({"success": True})
        
    if request.method == 'DELETE':
        part_id = request.args.get('id')
        url = f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}"
        make_supabase_request(url, method="DELETE")
        return jsonify({"success": True})

    url = f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*"
    rows = make_supabase_request(url, method="GET")
    return jsonify(rows if isinstance(rows, list) else [])

# --- ADMINISTRATIVE EMPLOYEE SYSTEM ---
@app.route('/api/employees', methods=['GET', 'POST', 'DELETE'])
def handle_employees():
    if not session.get('logged_in') or session.get('role') != 'Chairman':
        return jsonify({"error": "Unauthorized Access"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        payload = {
            "username": str(data.get('username', '')).strip(),
            "password": str(data.get('password', '')).strip(),
            "emp_name": str(data.get('emp_name', '')).strip(),
            "role": "Employee"
        }
        url = f"{SUPABASE_URL}/rest/v1/fixify_users"
        make_supabase_request(url, method="POST", data=payload)
        return jsonify({"success": True})
        
    if request.method == 'DELETE':
        username = request.args.get('username')
        if username == 'admin':
            return jsonify({"success": False, "message": "Chairman master delete nahi ho sakta!"})
        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(username)}"
        make_supabase_request(url, method="DELETE")
        return jsonify({"success": True})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?select=username,emp_name,role"
    rows = make_supabase_request(url, method="GET")
    return jsonify(rows if isinstance(rows, list) else [])

# --- MAIN JOBSHEET ENGINE PANEL ---
@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    if request.method == 'POST':
        data = request.json or {}
        
        count_url = f"{SUPABASE_URL}/rest/v1/jobs?select=id"
        all_rows = make_supabase_request(count_url, method="GET")
        next_num = len(all_rows) + 1 if isinstance(all_rows, list) else 1
        
        next_id = f"FIX{next_num:04d}"
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Explicit String/Float formatting for database acceptance
        try:
            est_cost = float(data.get('estimate', 0) or 0)
        except:
            est_cost = 0.0
            
        try:
            adv_cost = float(data.get('advance', 0) or 0)
        except:
            adv_cost = 0.0
            
        payload = {
            "id": str(next_id),
            "category": str(data.get('category', 'Mobile')),
            "name": str(data.get('name', '')),
            "phone1": str(data.get('phone1', '')),
            "device": str(data.get('device', '')),
            "imei": str(data.get('imei', '')),
            "password": str(data.get('password', '')),
            "problem": str(data.get('problem', '')),
            "estimate": est_cost,
            "advance": adv_cost,
            "extra_cost": 0.0,
            "discount": 0.0,
            "spare_part_cost": 0.0,
            "created_date": str(today_str),
            "status": "Pending",
            "created_by": str(session.get('emp_name', 'Staff'))
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
            # Safe data conversion block
            def safe_float(v):
                try: return float(v) if v is not None else 0.0
                except: return 0.0
                
            jobs.append({
                "id": str(r.get('id', '')),
                "category": str(r.get('category', 'Mobile')),
                "name": str(r.get('name', '')),
                "phone1": str(r.get('phone1', '')),
                "device": str(r.get('device', '')),
                "problem": str(r.get('problem', '')),
                "estimate": safe_float(r.get('estimate')),
                "advance": safe_float(r.get('advance')),
                "extra_cost": safe_float(r.get('extra_cost')),
                "discount": safe_float(r.get('discount')),
                "spare_part_cost": safe_float(r.get('spare_part_cost')),
                "date": str(r.get('created_date', '')),
                "status": str(r.get('status', 'Pending')),
                "created_by": str(r.get('created_by', 'Staff'))
            })
    jobs.sort(key=lambda x: x['id'], reverse=True)
    return jsonify(jobs)

@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{data.get('id')}"
    make_supabase_request(url, method="PATCH", data={"status": str(data.get('status'))})
    return jsonify({"success": True})

@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    url = f"{SUPABASE_URL}/rest/v1/jobs?id=eq.{data.get('id')}"
    
    try: ext = float(data.get('extra_cost', 0) or 0)
    except: ext = 0.0
    try: dsc = float(data.get('discount', 0) or 0)
    except: dsc = 0.0
    try: spc = float(data.get('spare_part_cost', 0) or 0)
    except: spc = 0.0
    
    payload = {
        "extra_cost": ext,
        "discount": dsc,
        "spare_part_cost": spc
    }
    make_supabase_request(url, method="PATCH", data=payload)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
