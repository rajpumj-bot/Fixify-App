import os
import json
import urllib.request
import urllib.parse
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__, template_folder='.')
app.secret_key = "fixify_super_cloud_secure_key_99"

SUPABASE_URL = "https://wgkdrknsynjipoynjof.supabase.co"
SUPABASE_KEY = "sb_publishable_3i7z0XcrCNuCgL8C3KTP3g_TnrCEz4i64vKms9vVj9BWh3v9W"

ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"

def make_supabase_request(url, method="GET", data=None):
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    if method in ["POST", "PATCH"]:
        headers["Prefer"] = "return=representation"
    if req_data:
        headers["Content-Length"] = str(len(req_data))
        
    req = urllib.request.Request(url, headers=headers, method=method, data=req_data)
    try:
        with urllib.request.urlopen(req) as response:
            res_read = response.read().decode("utf-8")
            return json.loads(res_read) if res_read else []
    except Exception as e:
        print("Supabase Backend Error:", e)
        return []

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
