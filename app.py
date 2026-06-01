import os
from flask import Flask, render_template, request, jsonify, session
import requests
from datetime import datetime, timedelta, timezone

app = Flask(__name__, template_folder='templates')
app.secret_key = "fixify_secure_key_2026"

SUPABASE_URL = "https://wgkdrknsynjzipoynjof.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

ADMIN_USER = "admin"
ADMIN_PASS = "fixify#0821"

def get_india_time_string():
    utc_time = datetime.now(timezone.utc)
    india_tz = timezone(timedelta(hours=5, minutes=30))
    india_time = utc_time.astimezone(india_tz)
    return india_time.strftime("%d-%m-%Y %H:%M")

def send_status_sms(phone, customer_name, device, status):
    if not FAST2SMS_API_KEY: return False
    msg = None
    if status == "Repairing":
        msg = f"Hi {customer_name}, your {device} is now under repair at Fixify."
    elif status == "Ready":
        msg = f"Hi {customer_name}, your {device} is READY for pickup. - Fixify Tech"
    if not msg: return False
    try:
        requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": FAST2SMS_API_KEY, "Content-Type": "application/json"},
            json={"message": msg, "language": "english", "route": "q", "numbers": str(phone)}
        )
        return True
    except Exception: return False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username == ADMIN_USER and password == ADMIN_PASS:
        session.update({"logged_in": True, "role": "Chairman", "name": "Chairman"})
        return jsonify({"success": True, "role": "Chairman", "name": "Chairman"})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{username}"
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200 and res.json():
            user = res.json()[0]
            if user["password"] == password:
                user_role = user.get("role", "Employee")
                session.update({"logged_in": True, "role": user_role, "name": user["emp_name"]})
                return jsonify({"success": True, "role": user_role, "name": user["emp_name"]})
    except Exception as e: print("LOGIN ERROR:", e)
    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route("/api/session")
def check_session():
    return jsonify({"logged_in": bool(session.get("logged_in")), "role": session.get("role"), "name": session.get("name")})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if not session.get("logged_in"): return jsonify([]), 401
    if request.method == "POST":
        data = request.json or {}
        get_res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id", headers=HEADERS)
        total = len(get_res.json()) + 1 if get_res.status_code == 200 else 1
        job_id = f"FIX{total:04d}"
        payload = {
            "id": job_id, "category": str(data.get("category", "")), "device": str(data.get("device", "")),
            "name": str(data.get("name", "")), "phone1": str(data.get("phone1", "")), "problem": str(data.get("problem", "")),
            "password": str(data.get("password", "")), "imei": str(data.get("solution") or "Standard Fix Required"),
            "estimate": float(data.get("estimate") or 0), "advance": float(data.get("advance") or 0),
            "extra_charge": "0", "discount": "0", "spare_cost": "0", "status": "Pending", "date": get_india_time_string(), "created_by": session.get("name")
        }
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_jobs", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201, 204], "job_id": job_id})
    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*", headers=HEADERS)
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/api/update_status", methods=["POST"])
def update_status():
    if not session.get("logged_in"): return jsonify({"success": False}), 401
    data = request.json or {}
    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data.get('id')}"
    old = requests.get(url, headers=HEADERS)
    res = requests.patch(url, headers=HEADERS, json={"status": data.get("status")})
    if res.status_code in [200, 204] and old.status_code == 200 and old.json():
        job = old.json()[0]
        send_status_sms(job.get("phone1"), job.get("name"), job.get("device"), data.get("status"))
    return jsonify({"success": res.status_code in [200, 204]})

@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if session.get("role") not in ["Chairman", "Manager"]: return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    job_id = data.get("id")
    disc_check = data.get("discount")
    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"
    if disc_check == -999:
        return jsonify({"success": requests.delete(url, headers=HEADERS).status_code in [200, 204]})
    if disc_check == -1:
        return jsonify({"success": requests.patch(url, headers=HEADERS, json={"name": str(data.get("custom_name")), "phone1": str(data.get("custom_phone"))}).status_code in [200, 204]})
    payload = {"extra_charge": str(data.get("extra_charge") or "0"), "discount": str(data.get("discount") or "0"), "spare_cost": str(data.get("spare_cost") or "0")}
    return jsonify({"success": requests.patch(url, headers=HEADERS, json=payload).status_code in [200, 204]})

# ========================================================
# 🔥 COMPONENT MATRICES DATA ROUTING WITH COMPATIBILITY SCHEMA MAPPING
# ========================================================
@app.route("/api/parts", methods=["GET", "POST", "DELETE"])
def parts():
    if not session.get("logged_in"): return jsonify([]), 401
    if request.method == "POST":
        data = request.json or {}
        # Utilizing structural alignment variables to secure dual metrics matrix slots
        payload = {
            "part_name": str(data.get("part_name")), 
            "model_compatibility": str(data.get("model")),
            "wholesale_cost": float(data.get("price_agrade") or 0), # Mapped to A-Grade parameters slot
            "updated_at": str(data.get("price_normal") or "0") # Mapped to Normal Quality parameters slot
        }
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_parts", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201]})

    if request.method == "DELETE":
        part_id = request.args.get("id")
        requests.delete(f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}", headers=HEADERS)
        return jsonify({"success": True})

    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*", headers=HEADERS)
    normalized_data = []
    if res.status_code == 200:
        for p in res.json():
            normalized_data.append({
                "id": p.get("id"), "part_name": p.get("part_name"), "model": p.get("model_compatibility"),
                "price_agrade": p.get("wholesale_cost"), "price_normal": p.get("updated_at")
            })
    return jsonify(normalized_data)

@app.route("/api/employees", methods=["GET", "POST", "DELETE"])
def employees():
    if session.get("role") not in ["Chairman", "Manager"]: return jsonify([]), 403
    if request.method == "POST":
        data = request.json or {}
        payload = {"emp_name": str(data.get("emp_name")), "username": str(data.get("username")), "password": str(data.get("password")), "role": str(data.get("role") or "Employee")}
        res = requests.post(f"{SUPABASE_URL}/rest/v1/fixify_users", headers=HEADERS, json=payload)
        return jsonify({"success": res.status_code in [200, 201]})
    if request.method == "DELETE":
        u = request.args.get("username")
        return jsonify({"success": requests.delete(f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{u}", headers=HEADERS).status_code in [200, 204]})
    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_users?select=*", headers=HEADERS)
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/manifest.json")
def manifest():
    return jsonify({"short_name": "Fixify", "name": "FIXIFY TECH REPAIR", "start_url": "/", "display": "standalone"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
