import os
import json
from datetime import datetime
import urllib.request
import urllib.parse
import urllib.error

from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = "fixify_secret_key_2026"

# =========================
# SUPABASE SETTINGS
# =========================

SUPABASE_URL = "https://wgkdrknsynjzipoynjof.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indna2Rya25zeW5qemlwb3luam9mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk5NjA0NTAsImV4cCI6MjA5NTUzNjQ1MH0.iqyC80PtFmAiUCki56Uk1F-ybQFSmR86XR8rTKTtBFY"

ADMIN_USER = "admin"
ADMIN_PASS = "fixify#0821"

# =========================
# SUPABASE REQUEST
# =========================

def supabase_request(url, method="GET", data=None):

    req_data = None

    if data:
        req_data = json.dumps(data).encode("utf-8")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    req = urllib.request.Request(
        url,
        data=req_data,
        headers=headers,
        method=method
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode()
            return json.loads(result) if result else []

    except urllib.error.HTTPError as e:
        print("SUPABASE ERROR:", e.read().decode())
        return None

    except Exception as e:
        print("GENERAL ERROR:", str(e))
        return None


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return "Fixify Server Running"


# =========================
# SESSION
# =========================

@app.route("/api/session")
def api_session():

    if not session.get("logged_in"):
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "role": session.get("role"),
        "emp_name": session.get("emp_name")
    })


# =========================
# LOGIN
# =========================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.json

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # Chairman Login

    if username == ADMIN_USER and password == ADMIN_PASS:

        session["logged_in"] = True
        session["role"] = "Chairman"
        session["emp_name"] = "Chairman"

        return jsonify({
            "success": True,
            "role": "Chairman",
            "emp_name": "Chairman"
        })

    # Employee Login

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(username)}"

    users = supabase_request(url)

    if users and len(users) > 0:

        user = users[0]

        if user.get("password") == password:

            session["logged_in"] = True
            session["role"] = user.get("role")
            session["emp_name"] = user.get("emp_name")

            return jsonify({
                "success": True,
                "role": user.get("role"),
                "emp_name": user.get("emp_name")
            })

    return jsonify({
        "success": False,
        "message": "Wrong ID Password"
    })


# =========================
# LOGOUT
# =========================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================
# JOBS
# =========================

@app.route("/api/jobs", methods=["GET", "POST"])
def jobs():

    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    # CREATE JOB

    if request.method == "POST":

        data = request.json

        job_id = "FIX" + datetime.now().strftime("%H%M%S")

        payload = [{
            "id": job_id,
            "category": data.get("category"),
            "device": data.get("device"),
            "name": data.get("name"),
            "phone1": data.get("phone1"),
            "problem": data.get("problem"),
            "password": data.get("password"),
            "imei": data.get("imei"),
            "estimate": float(data.get("estimate", 0)),
            "advance": float(data.get("advance", 0)),
            "extra_cost": 0,
            "discount": 0,
            "spare_part_cost": 0,
            "status": "Pending",
            "created_date": datetime.now().strftime("%d-%m-%Y %I:%M %p"),
            "created_by": session.get("emp_name")
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_jobs"

        result = supabase_request(
            url,
            method="POST",
            data=payload
        )

        if result is None:
            return jsonify({
                "success": False
            })

        return jsonify({
            "success": True,
            "id": job_id
        })

    # GET JOBS

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*"

    jobs = supabase_request(url)

    return jsonify(jobs if jobs else [])


# =========================
# UPDATE STATUS
# =========================

@app.route("/api/jobs/update_status", methods=["POST"])
def update_status():

    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data.get('id')}"

    payload = {
        "status": data.get("status")
    }

    supabase_request(
        url,
        method="PATCH",
        data=payload
    )

    return jsonify({
        "success": True
    })


# =========================
# UPDATE PRICING
# =========================

@app.route("/api/jobs/update_pricing", methods=["POST"])
def update_pricing():

    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{data.get('id')}"

    payload = {
        "extra_cost": float(data.get("extra_cost", 0)),
        "discount": float(data.get("discount", 0)),
        "spare_part_cost": float(data.get("spare_part_cost", 0))
    }

    supabase_request(
        url,
        method="PATCH",
        data=payload
    )

    return jsonify({
        "success": True
    })


# =========================
# EMPLOYEES
# =========================

@app.route("/api/employees", methods=["GET", "POST"])
def employees():

    if session.get("role") != "Chairman":
        return jsonify({"error": "Unauthorized"}), 401

    # ADD EMPLOYEE

    if request.method == "POST":

        data = request.json

        payload = [{
            "username": data.get("username"),
            "password": data.get("password"),
            "emp_name": data.get("emp_name"),
            "role": "Employee"
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_users"

        supabase_request(
            url,
            method="POST",
            data=payload
        )

        return jsonify({
            "success": True
        })

    # GET EMPLOYEES

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?select=*"

    users = supabase_request(url)

    return jsonify(users if users else [])


# =========================
# START
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
