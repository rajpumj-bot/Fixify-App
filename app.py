from flask import Flask, render_template, request, jsonify, session
import requests
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = "fixify_secure_key_2026"

# =============================
# CONFIG
# =============================
SUPABASE_URL = "https://wgkdrknsynjzipoynjof.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

ADMIN_USER = "admin"
ADMIN_PASS = "fixify#0821"


# =============================
# SMS FUNCTION
# =============================
def send_status_sms(phone, name, device, status):
    if not FAST2SMS_API_KEY:
        return False

    msg = None
    if status == "Repairing":
        msg = f"{name}, your {device} is now under repair."
    elif status == "Ready":
        msg = f"{name}, your {device} is READY for pickup."

    if not msg:
        return False

    try:
        r = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={
                "authorization": FAST2SMS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "message": msg,
                "numbers": str(phone),
                "route": "q",
                "language": "english"
            }
        )
        return r.status_code == 200
    except:
        return False


# =============================
# HOME
# =============================
@app.route("/")
def home():
    return render_template("index.html")


# =============================
# LOGIN (FIXED 100%)
# =============================
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        # Admin login
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["logged_in"] = True
            session["role"] = "Chairman"
            session["name"] = "Chairman"
            return jsonify({"success": True, "role": "Chairman", "name": "Chairman"})

        # Supabase login
        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{username}"
        res = requests.get(url, headers=HEADERS)

        if res.status_code != 200:
            return jsonify({"success": False, "message": "Database error"})

        users = res.json()

        if not users:
            return jsonify({"success": False, "message": "User not found"})

        user = users[0]

        if user.get("password") != password:
            return jsonify({"success": False, "message": "Wrong password"})

        session["logged_in"] = True
        session["role"] = user.get("role", "Employee")
        session["name"] = user.get("emp_name")

        return jsonify({"success": True, "role": session["role"], "name": session["name"]})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# =============================
# SESSION
# =============================
@app.route("/api/session")
def check_session():
    return jsonify({
        "logged_in": bool(session.get("logged_in")),
        "role": session.get("role"),
        "name": session.get("name")
    })


# =============================
# LOGOUT
# =============================
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# =============================
# JOBS
# =============================
@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.json or {}
        now = datetime.now().strftime("%d-%m-%Y %H:%M")

        r = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id", headers=HEADERS)
        total = len(r.json()) + 1 if r.status_code == 200 else 1
        job_id = f"FIX{total:04d}"

        payload = {
            "id": job_id,
            "category": data.get("category", ""),
            "device": data.get("device", ""),
            "name": data.get("name", ""),
            "phone1": data.get("phone1", ""),
            "problem": data.get("problem", ""),
            "password": data.get("password", ""),
            "imei": data.get("imei", ""),
            "estimate": float(data.get("estimate") or 0),
            "advance": float(data.get("advance") or 0),
            "extra_charge": 0,
            "discount": 0,
            "spare_cost": 0,
            "status": "Pending",
            "date": now,
            "created_by": session.get("name")
        }

        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/fixify_jobs",
            headers=HEADERS,
            json=payload
        )

        if res.status_code not in [200, 201, 204]:
            return jsonify({"success": False, "message": res.text})

        return jsonify({"success": True, "job_id": job_id})

    res = requests.get(f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*", headers=HEADERS)
    return jsonify(res.json() if res.status_code == 200 else [])


# =============================
# STATUS UPDATE
# =============================
@app.route("/api/update_status", methods=["POST"])
def update_status():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    job_id = data.get("id")
    status = data.get("status")

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"

    old = requests.get(url, headers=HEADERS)
    res = requests.patch(url, headers=HEADERS, json={"status": status})

    if res.status_code in [200, 204] and old.status_code == 200:
        if old.json():
            job = old.json()[0]
            send_status_sms(job.get("phone1"), job.get("name"), job.get("device"), status)

    return jsonify({"success": True})


# =============================
# PRICING UPDATE (FIXED)
# =============================
@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    job_id = data.get("id")

    payload = {
        "discount": float(data.get("discount") or 0),
        "extra_charge": float(data.get("extra_charge") or 0),
        "spare_cost": float(data.get("spare_cost") or 0)
    }

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"

    res = requests.patch(url, headers=HEADERS, json=payload)

    return jsonify({"success": res.status_code in [200, 204]})


# =============================
# RUN
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
