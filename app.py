import os
import json
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse

from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = "fixify_secret_key_2026"

# ============================================
# SUPABASE CONFIG
# ============================================

SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"

SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"

ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"

# ============================================
# SUPABASE REQUEST FUNCTION
# ============================================

def make_supabase_request(url, method="GET", data=None):

    req_data = None

    if data is not None:
        req_data = json.dumps(data).encode("utf-8")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    req = urllib.request.Request(
        url,
        headers=headers,
        method=method,
        data=req_data
    )

    try:

        with urllib.request.urlopen(req) as response:

            result = response.read().decode("utf-8")

            if result:
                return json.loads(result)

            return []

    except urllib.error.HTTPError as e:

        print("HTTP ERROR:", e.code)

        try:
            print(e.read().decode())
        except:
            pass

        return None

    except Exception as e:

        print("GENERAL ERROR:", str(e))
        return None


# ============================================
# HOME PAGE
# ============================================

@app.route('/')
def home():
    return render_template('index.html')


# ============================================
# SESSION CHECK
# ============================================

@app.route('/api/session')
def session_check():

    if not session.get("logged_in"):

        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "role": session.get("role"),
        "emp_name": session.get("emp_name")
    })


# ============================================
# LOGIN
# ============================================

@app.route('/api/login', methods=['POST'])
def login():

    data = request.json or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    # ADMIN LOGIN

    if username == ADMIN_USER and password == ADMIN_PASS:

        session["logged_in"] = True
        session["role"] = "Chairman"
        session["emp_name"] = "Chairman Master"

        return jsonify({
            "success": True,
            "role": "Chairman",
            "emp_name": "Chairman Master"
        })

    # EMPLOYEE LOGIN

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(username)}"

    users = make_supabase_request(url)

    if isinstance(users, list) and len(users) > 0:

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
        "message": "Invalid username or password"
    })


# ============================================
# LOGOUT
# ============================================

@app.route('/api/logout', methods=['POST'])
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


# ============================================
# CREATE + FETCH JOBS
# ============================================

@app.route('/api/jobs', methods=['GET', 'POST'])
def jobs():

    if not session.get("logged_in"):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    # =====================================
    # CREATE JOB
    # =====================================

    if request.method == 'POST':

        data = request.json or {}

        count_url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=id"

        all_jobs = make_supabase_request(count_url)

        next_num = 1

        if isinstance(all_jobs, list):
            next_num = len(all_jobs) + 1

        job_id = f"FIX{next_num:04d}"

        payload = [{
            "id": job_id,
            "category": data.get("category"),
            "name": data.get("name"),
            "phone1": data.get("phone1"),
            "device": data.get("device"),
            "imei": data.get("imei"),
            "password": data.get("password"),
            "problem": data.get("problem"),
            "estimate": float(data.get("estimate", 0)),
            "advance": float(data.get("advance", 0)),
            "extra_cost": 0,
            "discount": 0,
            "spare_part_cost": 0,
            "status": "Pending",
            "created_by": session.get("emp_name"),
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }]

        insert_url = f"{SUPABASE_URL}/rest/v1/fixify_jobs"

        result = make_supabase_request(
            insert_url,
            method="POST",
            data=payload
        )

        if result is None:

            return jsonify({
                "success": False,
                "message": "Database insert failed"
            })

        return jsonify({
            "success": True,
            "id": job_id
        })

    # =====================================
    # FETCH JOBS
    # =====================================

    fetch_url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*"

    jobs_data = make_supabase_request(fetch_url)

    if not isinstance(jobs_data, list):
        jobs_data = []

    return jsonify(jobs_data)


# ============================================
# UPDATE STATUS
# ============================================

@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():

    if not session.get("logged_in"):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.json or {}

    job_id = data.get("id")
    status = data.get("status")

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"

    make_supabase_request(
        url,
        method="PATCH",
        data={
            "status": status
        }
    )

    return jsonify({
        "success": True
    })


# ============================================
# UPDATE PRICING
# ============================================

@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():

    if not session.get("logged_in"):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.json or {}

    job_id = data.get("id")

    payload = {
        "extra_cost": float(data.get("extra_cost", 0)),
        "discount": float(data.get("discount", 0)),
        "spare_part_cost": float(data.get("spare_part_cost", 0))
    }

    url = f"{SUPABASE_URL}/rest/v1/fixify_jobs?id=eq.{job_id}"

    make_supabase_request(
        url,
        method="PATCH",
        data=payload
    )

    return jsonify({
        "success": True
    })


# ============================================
# PARTS API
# ============================================

@app.route('/api/parts', methods=['GET', 'POST', 'DELETE'])
def parts():

    if not session.get("logged_in"):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    # =====================================
    # ADD PART
    # =====================================

    if request.method == 'POST':

        data = request.json or {}

        payload = [{
            "part_name": data.get("part_name"),
            "model_compatibility": data.get("model_compatibility"),
            "wholesale_cost": float(data.get("wholesale_cost", 0)),
            "updated_at": datetime.now().strftime("%Y-%m-%d")
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_parts"

        result = make_supabase_request(
            url,
            method="POST",
            data=payload
        )

        if result is None:

            return jsonify({
                "success": False
            })

        return jsonify({
            "success": True
        })

    # =====================================
    # DELETE PART
    # =====================================

    if request.method == 'DELETE':

        part_id = request.args.get("id")

        url = f"{SUPABASE_URL}/rest/v1/fixify_parts?id=eq.{part_id}"

        make_supabase_request(
            url,
            method="DELETE"
        )

        return jsonify({
            "success": True
        })

    # =====================================
    # FETCH PARTS
    # =====================================

    url = f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*"

    parts_data = make_supabase_request(url)

    if not isinstance(parts_data, list):
        parts_data = []

    return jsonify(parts_data)


# ============================================
# EMPLOYEE API
# ============================================

@app.route('/api/employees', methods=['GET', 'POST', 'DELETE'])
def employees():

    if not session.get("logged_in"):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    if session.get("role") != "Chairman":

        return jsonify({
            "error": "Only Chairman Allowed"
        }), 403

    # =====================================
    # CREATE EMPLOYEE
    # =====================================

    if request.method == 'POST':

        data = request.json or {}

        payload = [{
            "username": data.get("username"),
            "password": data.get("password"),
            "emp_name": data.get("emp_name"),
            "role": "Employee"
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_users"

        make_supabase_request(
            url,
            method="POST",
            data=payload
        )

        return jsonify({
            "success": True
        })

    # =====================================
    # DELETE EMPLOYEE
    # =====================================

    if request.method == 'DELETE':

        username = request.args.get("username")

        url = f"{SUPABASE_URL}/rest/v1/fixify_users?username=eq.{urllib.parse.quote(username)}"

        make_supabase_request(
            url,
            method="DELETE"
        )

        return jsonify({
            "success": True
        })

    # =====================================
    # FETCH EMPLOYEES
    # =====================================

    url = f"{SUPABASE_URL}/rest/v1/fixify_users?select=username,emp_name,role"

    users = make_supabase_request(url)

    if not isinstance(users, list):
        users = []

    return jsonify(users)


# ============================================
# START SERVER
# ============================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
