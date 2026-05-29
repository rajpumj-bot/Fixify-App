from flask import Flask, render_template, request, jsonify, session
import requests
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = "fixify_secure_key_2026"

SUPABASE_URL = "https://wgkdrknsynjzipoynjof.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

ADMIN_USER = "admin"

def get_admin_pass():
    # Pehle DB se password check karega, agar nahi mila toh default "fixify#0821" rakhega
    try:
        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.admin"
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200 and len(res.json()) > 0:
            return res.json()[0]["password"]
    except:
        pass
    return "fixify#0821"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username == ADMIN_USER and password == get_admin_pass():
        session.update({"logged_in": True, "role": "Chairman", "name": "Chairman"})
        return jsonify({"success": True, "role": "Chairman", "name": "Chairman"})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{username}"
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            users = res.json()
            if len(users) > 0 and users[0]["password"] == password and users[0]["role"] != "Chairman":
                session.update({"logged_in": True, "role": "Employee", "name": users[0]["emp_name"]})
                return jsonify({"success": True, "role": "Employee", "name": users[0]["emp_name"]})
    except Exception as e:
        print("LOGIN ERROR:", str(e))

    return jsonify({"success": False, "message": "Wrong Username or Password"})

@app.route("/api/session")
def check_session():
    if session.get("logged_in"):
        return jsonify({"logged_in": True, "role": session.get("role"), "name": session.get("name")})
    return jsonify({"logged_in": False})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/update_chairman_pass", methods=["POST"])
def update_chairman_pass():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_pass = data.get("new_password", "").strip()
    
    # DB me check karenge ki admin row h ya nahi, h toh patch nahi to post
    check_url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.admin"
    res = requests.get(check_url, headers=HEADERS)
    
    if res.status_code == 200 and len(res.json()) > 0:
        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.admin"
        r = requests.patch(url, headers=HEADERS, json={"password": new_pass})
    else:
        url = f"{SUPABASE_URL}/rest/v1/fixify_users"
        r = requests.post(url, headers=HEADERS, json={"username": "admin", "password": new_pass, "emp_name": "Chairman", "role": "Chairman"})
        
    return jsonify({"success": r.status_code in [200, 201, 204]})

@app.route("/api/employees", methods=["GET", "POST", "DELETE"])
def employees():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.json
        payload = {"username": data["username"], "password": data["password"], "emp_name": data["emp_name"], "role": "Employee"}
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_users", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201]})

    if request.method == "DELETE":
        username = request.args.get("username")
        requests.delete(f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{username}", headers=HEADERS)
        return jsonify({"success": True})

    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_users?select=*", headers=HEADERS)
    return jsonify([u for u in res.json() if u['username'] != 'admin'] if res.status_code == 200 else [])

@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.json
        now = datetime.now().strftime("%d-%m-%Y %H:%M")
        
        get_res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id", headers=HEADERS)
        total = len(get_res.json()) + 1 if get_res.status_code == 200 else 1
        job_id = f"FIX{total:04d}"

        payload = {
            "id": job_id, "customer_name": data["customer_name"], "phone": data["phone"],
            "device": data["device"], "category": data["category"], "problem": data["problem"],
            "pin_password": data["pin_password"], "estimate": float(data["estimate"]), "advance": float(data["advance"]),
            "extra_charge": 0, "discount": 0, "spare_cost": 0, "status": "Pending", "date": now, "created_by": session.get("name")
        }
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_jobs", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201], "job_id": job_id})

    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*", headers=HEADERS)
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/api/update_status", methods=["POST"])
def update_status():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data['id']}", headers=HEADERS, json={"status": data["status"]})
    return jsonify({"success": res.status_code in [200, 204]})

@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    payload = {"extra_charge": float(data["extra_charge"]), "discount": float(data["discount"]), "spare_cost": float(data["spare_cost"])}
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data['id']}", headers=HEADERS, json=payload)
    return jsonify({"success": res.status_code in [200, 204]})

@app.route("/api/parts", methods=["GET", "POST", "DELETE"])
def parts():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.json
        payload = {"part_name": data["part_name"], "model": data["model"], "price": float(data["price"]), "date": datetime.now().strftime("%d-%m-%Y")}
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_parts", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201]})

    if request.method == "DELETE":
        part_id = request.args.get("id")
        requests.delete(f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}", headers=HEADERS)
        return jsonify({"success": True})

    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*", headers=HEADERS)
    return jsonify(res.json() if res.status_code == 200 else [])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
