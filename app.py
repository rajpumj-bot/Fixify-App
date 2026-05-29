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
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY")

if not SUPABASE_KEY:
    print("⚠️ WARNING: SUPABASE_KEY not set in environment")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

ADMIN_USER = "admin"
ADMIN_PASS = "fixify#0821"


# =============================
# SMS ENGINE
# =============================
def send_status_sms(phone, customer_name, device, status):
    if not FAST2SMS_API_KEY:
        print("SMS SKIPPED: FAST2SMS_API_KEY missing")
        return False

    msg = None

    if status == "Repairing":
        msg = f"Hi {customer_name}, your {device} is now under repair at Fixify."
    elif status == "Ready":
        msg = f"Hi {customer_name}, your {device} is READY for pickup. - Fixify Tech"

    if not msg:
        return False

    try:
        res = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={
                "authorization": FAST2SMS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "message": msg,
                "language": "english",
                "route": "q",
                "numbers": str(phone)
            }
        )
        return res.status_code == 200
    except Exception as e:
        print("SMS ERROR:", e)
        return False


# =============================
# HOME
# =============================
@app.route("/")
def home():
    return render_template("index.html")


# =============================
# LOGIN
# =============================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username == ADMIN_USER and password == ADMIN_PASS:
        session.update({"logged_in": True, "role": "Chairman", "name": "Chairman"})
        return jsonify({"success": True, "role": "Chairman", "name": "Chairman"})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{username}"

    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            users = res.json()
            if users and users[0]["password"] == password:
                session.update({
                    "logged_in": True,
                    "role": users[0].get("role", "Employee"),
                    "name": users[0]["emp_name"]
                })
                return jsonify({
                    "success": True,
                    "role": users[0].get("role", "Employee"),
                    "name": users[0]["emp_name"]
                })
    except Exception as e:
        print("LOGIN ERROR:", e)

    return jsonify({"success": False, "message": "Invalid login"})


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
# JOBS (MAIN FIXED ENGINE)
# =============================
@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    # ================= POST JOB =================
    if request.method == "POST":
        data = request.json or {}

        now = datetime.now().strftime("%d-%m-%Y %H:%M")

        get_res = requests.get(
            f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id",
            headers=HEADERS
        )

        total = len(get_res.json()) + 1 if get_res.status_code == 200 else 1
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

        print("➡️ INSERT JOB:", payload)

        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/fixify_jobs",
            headers=HEADERS,
            json=payload
        )

        print("⬅️ SUPABASE RESPONSE:", res.text)

        if res.status_code not in [200, 201, 204]:
            return jsonify({
                "success": False,
                "message": res.text
            })

        return jsonify({"success": True, "job_id": job_id})

    # ================= GET JOBS =================
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*",
        headers=HEADERS
    )

    return jsonify(res.json() if res.status_code == 200 else [])


# =============================
# STATUS UPDATE + SMS
# =============================
@app.route("/api/update_status", methods=["POST"])
def update_status():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    job_id = data.get("id")
    new_status = data.get("status")

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"

    old = requests.get(url, headers=HEADERS)

    res = requests.patch(url, headers=HEADERS, json={"status": new_status})

    if res.status_code in [200, 204]:
        if old.status_code == 200 and old.json():
            job = old.json()[0]
            send_status_sms(
                job.get("phone1"),
                job.get("name"),
                job.get("device"),
                new_status
            )

    return jsonify({"success": res.status_code in [200, 204]})


# =============================
# PRICING MODERATION ROUTE (ADDED FIX)
# =============================
@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    job_id = data.get("id")
    
    payload = {
        "extra_charge": float(data.get("extra_charge") or 0),
        "discount": float(data.get("discount") or 0),
        "spare_cost": float(data.get("spare_cost") or 0)
    }

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"
    res = requests.patch(url, headers=HEADERS, json=payload)
    
    return jsonify({"success": res.status_code in [200, 204]})


# =============================
# PARTS
# =============================
@app.route("/api/parts", methods=["GET", "POST", "DELETE"])
def parts():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        data = request.json
        payload = {
            "part_name": data.get("part_name"),
            "model": data.get("model"),
            "price": float(data.get("price") or 0),
            "date": datetime.now().strftime("%d-%m-%Y")
        }

        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/fixify_parts",
            headers=HEADERS,
            json=payload
        )

        return jsonify({"success": res.status_code in [200, 201]})

    if request.method == "DELETE":
        part_id = request.args.get("id")
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}",
            headers=HEADERS
        )
        return jsonify({"success": True})

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*",
        headers=HEADERS
    )

    return jsonify(res.json() if res.status_code == 200 else [])


# =============================
# RUN APP
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
