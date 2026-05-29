```python
import os
import json
import uuid
from datetime import datetime
import urllib.request
import urllib.error
import urllib.parse

from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='.')

# =========================
# SECURITY CONFIG
# =========================
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "fixify_super_cloud_secure_key_99"
)

# =========================
# SUPABASE CONFIG
# =========================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# =========================
# ADMIN LOGIN
# =========================
ADMIN_USER = "admin"
ADMIN_PASS = "fixify@2026"

# =========================
# SUPABASE REQUEST FUNCTION
# =========================
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

            response_text = response.read().decode("utf-8")

            print("✅ SUPABASE SUCCESS")
            print(response_text)

            return json.loads(response_text) if response_text else []

    except urllib.error.HTTPError as e:

        print("❌ SUPABASE HTTP ERROR")
        print("STATUS:", e.code)

        try:
            print("BODY:", e.read().decode())
        except:
            pass

        return None

    except Exception as e:

        print("❌ GENERAL ERROR")
        print(str(e))

        return None


# =========================
# HOME
# =========================
@app.route('/')
def home():
    return render_template('index.html')


# =========================
# SESSION CHECK
# =========================
@app.route('/api/session', methods=['GET'])
def get_session():

    if not session.get('logged_in'):

        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "role": session.get('role', 'Employee'),
        "emp_name": session.get('emp_name', 'Staff')
    })


# =========================
# LOGIN
# =========================
@app.route('/api/login', methods=['POST'])
def do_login():

    data = request.json or {}

    username = str(data.get('username', '')).strip()
    password = str(data.get('password', '')).strip()

    # ================= ADMIN LOGIN =================
    if username == ADMIN_USER and password == ADMIN_PASS:

        session['logged_in'] = True
        session['username'] = ADMIN_USER
        session['role'] = "Chairman"
        session['emp_name'] = "Chairman Master"

        return jsonify({
            "success": True,
            "role": "Chairman",
            "emp_name": "Chairman Master"
        })

    # ================= EMPLOYEE LOGIN =================
    safe_username = urllib.parse.quote(username)

    url = (
        f"{SUPABASE_URL}/rest/v1/fixify_users"
        f"?username=eq.{safe_username}"
    )

    user_rows = make_supabase_request(url, method="GET")

    if isinstance(user_rows, list) and len(user_rows) > 0:

        db_user = user_rows[0]

        stored_password = db_user.get('password', '')

        if check_password_hash(stored_password, password):

            session['logged_in'] = True
            session['username'] = db_user.get('username')
            session['role'] = db_user.get('role')
            session['emp_name'] = db_user.get('emp_name')

            return jsonify({
                "success": True,
                "role": db_user.get('role'),
                "emp_name": db_user.get('emp_name')
            })

    return jsonify({
        "success": False,
        "message": "Galat ID ya Password!"
    })


# =========================
# LOGOUT
# =========================
@app.route('/api/logout', methods=['POST'])
def do_logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================
# PARTS API
# =========================
@app.route('/api/parts', methods=['GET', 'POST', 'DELETE'])
def handle_parts():

    if not session.get('logged_in'):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    # ================= ADD PART =================
    if request.method == 'POST':

        data = request.json or {}

        today_str = datetime.now().strftime("%Y-%m-%d")

        try:
            wholesale_cost = float(
                data.get('wholesale_cost', 0) or 0
            )
        except:
            wholesale_cost = 0.0

        payload = [{
            "part_name": str(data.get('part_name', 'Part')),
            "model_compatibility": str(
                data.get('model_compatibility', '')
            ),
            "wholesale_cost": wholesale_cost,
            "updated_at": today_str
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_parts"

        result = make_supabase_request(
            url,
            method="POST",
            data=payload
        )

        if result is None:

            return jsonify({
                "success": False,
                "message": "Part save failed"
            }), 500

        return jsonify({
            "success": True
        })

    # ================= DELETE PART =================
    if request.method == 'DELETE':

        if session.get('role') != 'Chairman':

            return jsonify({
                "error": "Unauthorized"
            }), 401

        part_id = request.args.get('id', '')

        safe_id = urllib.parse.quote(part_id)

        url = (
            f"{SUPABASE_URL}/rest/v1/fixify_parts"
            f"?id=eq.{safe_id}"
        )

        make_supabase_request(url, method="DELETE")

        return jsonify({
            "success": True
        })

    # ================= GET PARTS =================
    url = f"{SUPABASE_URL}/rest/v1/fixify_parts?select=*"

    rows = make_supabase_request(url, method="GET")

    return jsonify(rows if isinstance(rows, list) else [])


# =========================
# EMPLOYEE API
# =========================
@app.route('/api/employees', methods=['GET', 'POST', 'DELETE'])
def handle_employees():

    if (
        not session.get('logged_in')
        or session.get('role') != 'Chairman'
    ):

        return jsonify({
            "error": "Unauthorized Access"
        }), 401

    # ================= CREATE EMPLOYEE =================
    if request.method == 'POST':

        data = request.json or {}

        raw_password = str(
            data.get('password', '')
        ).strip()

        hashed_password = generate_password_hash(raw_password)

        payload = [{
            "username": str(
                data.get('username', '')
            ).strip(),

            "password": hashed_password,

            "emp_name": str(
                data.get('emp_name', '')
            ).strip(),

            "role": "Employee"
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_users"

        result = make_supabase_request(
            url,
            method="POST",
            data=payload
        )

        if result is None:

            return jsonify({
                "success": False,
                "message": "Employee create failed"
            }), 500

        return jsonify({
            "success": True
        })

    # ================= DELETE EMPLOYEE =================
    if request.method == 'DELETE':

        username = request.args.get('username', '')

        safe_username = urllib.parse.quote(username)

        url = (
            f"{SUPABASE_URL}/rest/v1/fixify_users"
            f"?username=eq.{safe_username}"
        )

        make_supabase_request(url, method="DELETE")

        return jsonify({
            "success": True
        })

    # ================= GET EMPLOYEES =================
    url = (
        f"{SUPABASE_URL}/rest/v1/fixify_users"
        f"?select=username,emp_name,role"
    )

    rows = make_supabase_request(url, method="GET")

    return jsonify(rows if isinstance(rows, list) else [])


# =========================
# JOBS API
# =========================
@app.route('/api/jobs', methods=['GET', 'POST'])
def handle_jobs():

    if not session.get('logged_in'):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    # ================= CREATE JOB =================
    if request.method == 'POST':

        data = request.json or {}

        job_id = f"FIX-{uuid.uuid4().hex[:6].upper()}"

        today_str = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        try:
            estimate = float(
                data.get('estimate', 0) or 0
            )
        except:
            estimate = 0.0

        try:
            advance = float(
                data.get('advance', 0) or 0
            )
        except:
            advance = 0.0

        payload = [{
            "id": job_id,

            "category": str(
                data.get('category', 'Mobile')
            ),

            "name": str(
                data.get('name', '')
            ),

            "phone1": str(
                data.get('phone1', '')
            ),

            "device": str(
                data.get('device', '')
            ),

            "imei": str(
                data.get('imei', '')
            ),

            "password": str(
                data.get('password', '')
            ),

            "problem": str(
                data.get('problem', '')
            ),

            "estimate": estimate,

            "advance": advance,

            "extra_cost": 0.0,

            "discount": 0.0,

            "spare_part_cost": 0.0,

            "created_date": today_str,

            "status": "Pending",

            "created_by": str(
                session.get('emp_name', 'Staff')
            )
        }]

        url = f"{SUPABASE_URL}/rest/v1/fixify_jobs"

        result = make_supabase_request(
            url,
            method="POST",
            data=payload
        )

        if result is None:

            return jsonify({
                "success": False,
                "message": "Database insert failed"
            }), 500

        return jsonify({
            "success": True,
            "id": job_id
        })

    # ================= GET JOBS =================
    fetch_url = (
        f"{SUPABASE_URL}/rest/v1/fixify_jobs?select=*"
    )

    rows = make_supabase_request(
        fetch_url,
        method="GET"
    )

    jobs = []

    if isinstance(rows, list):

        for r in rows:

            try:
                estimate = float(
                    r.get('estimate', 0) or 0
                )
            except:
                estimate = 0.0

            try:
                advance = float(
                    r.get('advance', 0) or 0
                )
            except:
                advance = 0.0

            try:
                extra_cost = float(
                    r.get('extra_cost', 0) or 0
                )
            except:
                extra_cost = 0.0

            try:
                discount = float(
                    r.get('discount', 0) or 0
                )
            except:
                discount = 0.0

            try:
                spare_part_cost = float(
                    r.get('spare_part_cost', 0) or 0
                )
            except:
                spare_part_cost = 0.0

            jobs.append({

                "id": str(r.get('id', '')),

                "category": str(
                    r.get('category', 'Mobile')
                ),

                "name": str(
                    r.get('name', '')
                ),

                "phone1": str(
                    r.get('phone1', '')
                ),

                "device": str(
                    r.get('device', '')
                ),

                "problem": str(
                    r.get('problem', '')
                ),

                "estimate": estimate,

                "advance": advance,

                "extra_cost": extra_cost,

                "discount": discount,

                "spare_part_cost": spare_part_cost,

                "date": str(
                    r.get('created_date', '')
                ),

                "status": str(
                    r.get('status', 'Pending')
                ),

                "created_by": str(
                    r.get('created_by', 'Staff')
                )
            })

    jobs.sort(
        key=lambda x: x['date'],
        reverse=True
    )

    return jsonify(jobs)


# =========================
# UPDATE STATUS
# =========================
@app.route('/api/jobs/update_status', methods=['POST'])
def update_status():

    if not session.get('logged_in'):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.json or {}

    safe_id = urllib.parse.quote(
        str(data.get('id'))
    )

    url = (
        f"{SUPABASE_URL}/rest/v1/fixify_jobs"
        f"?id=eq.{safe_id}"
    )

    payload = {
        "status": str(
            data.get('status', 'Pending')
        )
    }

    make_supabase_request(
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
@app.route('/api/jobs/update_pricing', methods=['POST'])
def update_pricing():

    if not session.get('logged_in'):

        return jsonify({
            "error": "Unauthorized"
        }), 401

    data = request.json or {}

    safe_id = urllib.parse.quote(
        str(data.get('id'))
    )

    url = (
        f"{SUPABASE_URL}/rest/v1/fixify_jobs"
        f"?id=eq.{safe_id}"
    )

    try:
        extra_cost = float(
            data.get('extra_cost', 0) or 0
        )
    except:
        extra_cost = 0.0

    try:
        discount = float(
            data.get('discount', 0) or 0
        )
    except:
        discount = 0.0

    try:
        spare_part_cost = float(
            data.get('spare_part_cost', 0) or 0
        )
    except:
        spare_part_cost = 0.0

    payload = {
        "extra_cost": extra_cost,
        "discount": discount,
        "spare_part_cost": spare_part_cost
    }

    make_supabase_request(
        url,
        method="PATCH",
        data=payload
    )

    return jsonify({
        "success": True
    })


# =========================
# MAIN
# =========================
if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=int(
            os.environ.get("PORT", 5000)
        )
    )
```
