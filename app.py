from flask import Flask, render_template, request, jsonify, session
import requests
from datetime import datetime
import os

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


# ================= SMS =================
def send_sms(phone, name, device, status):
    if not FAST2SMS_API_KEY:
        return False

    msg = None
    if status == "Repairing":
        msg = f"{name}, your {device} is under repair - Fixify"
    elif status == "Ready":
        msg = f"{name}, your {device} is READY for pickup - Fixify"
    else:
        return False

    try:
        requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": FAST2SMS_API_KEY},
            json={
                "message": msg,
                "numbers": phone,
                "route": "q"
            }
        )
        return True
    except:
        return False


# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= LOGIN =================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    u = data.get("username", "")
    p = data.get("password", "")

    if u == ADMIN_USER and p == ADMIN_PASS:
        session.update({"logged_in": True, "role": "Chairman", "name": "Chairman"})
        return jsonify({"success": True, "role": "Chairman", "name": "Chairman"})

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{u}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code == 200 and res.json():
        user = res.json()[0]
        if user["password"] == p:
            session.update({"logged_in": True, "role": user.get("role"), "name": user["emp_name"]})
            return jsonify({"success": True, "role": user["role"], "name": user["emp_name"]})

    return jsonify({"success": False, "message": "Invalid login"})


# ================= SESSION =================
@app.route("/api/session")
def session_check():
    return jsonify({
        "logged_in": bool(session.get("logged_in")),
        "role": session.get("role"),
        "name": session.get("name")
    })


# ================= LOGOUT =================
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# ================= JOBS =================
@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    # CREATE JOB
    if request.method == "POST":
        data = request.json or {}

        now = datetime.now().strftime("%d-%m-%Y %H:%M")

        count = requests.get(
            f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id",
            headers=HEADERS
        )

        job_id = f"FIX{len(count.json())+1:04d}" if count.status_code == 200 else "FIX0001"

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

    # GET JOBS
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*",
        headers=HEADERS
    )

    return jsonify(res.json() if res.status_code == 200 else [])


# ================= STATUS UPDATE =================
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
            j = old.json()[0]
            send_sms(j.get("phone1"), j.get("name"), j.get("device"), status)

    return jsonify({"success": True})


# ================= PRICING =================
@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data['id']}"

    payload = {
        "extra_charge": float(data.get("extra_charge") or 0),
        "discount": float(data.get("discount") or 0),
        "spare_cost": float(data.get("spare_cost") or 0)
    }

    res = requests.patch(url, headers=HEADERS, json=payload)

    return jsonify({"success": res.status_code in [200, 204]})


# ================= PARTS =================
@app.route("/api/parts", methods=["GET", "POST", "DELETE"])
def parts():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "POST":
        d = request.json
        payload = {
            "part_name": d.get("part_name"),
            "model": d.get("model"),
            "price": float(d.get("price") or 0),
            "date": datetime.now().strftime("%d-%m-%Y")
        }

        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/fixify_parts",
            headers=HEADERS,
            json=payload
        )

        return jsonify({"success": True})

    if request.method == "DELETE":
        pid = request.args.get("id")
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{pid}",
            headers=HEADERS
        )
        return jsonify({"success": True})

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*",
        headers=HEADERS
    )

    return jsonify(res.json() if res.status_code == 200 else [])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
