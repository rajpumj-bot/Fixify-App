import os
from flask import Flask, render_template, request, jsonify, session
from supabase import create_client, Client
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fixify_secure_secret_token_9988")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ensure Static directories framework structure exists
os.makedirs("static", exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/session", methods=["GET"])
def get_session():
    if "user" in session:
        return jsonify({"logged_in": True, "username": session["user"], "role": session.get("role", "Employee")})
    return jsonify({"logged_in": False})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    u = data.get("username", "").strip()
    p = data.get("password", "").strip()
    
    if u == "admin":
        try:
            res = supabase.table("fixify_chairman").select("*").eq("username", "admin").execute()
            if res.data and res.data[0].get("password") == p:
                session["user"] = "admin"
                session["role"] = "Chairman"
                return jsonify({"success": True, "role": "Chairman"})
        except Exception:
            if p == "admin123":
                session["user"] = "admin"
                session["role"] = "Chairman"
                return jsonify({"success": True, "role": "Chairman"})
        return jsonify({"success": False, "message": "Invalid Chairman Token Pin."})
        
    try:
        res = supabase.table("fixify_staff").select("*").eq("username", u).execute()
        if res.data and res.data[0].get("password") == p:
            session["user"] = u
            session["role"] = "Employee"
            return jsonify({"success": True, "role": "Employee"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Database Error: {str(e)}"})
        
    return jsonify({"success": False, "message": "Invalid Identity credentials."})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/jobs", methods=["GET", "POST"])
def handle_jobs():
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized access gateway."}), 401
        
    if request.method == "POST":
        data = request.json or {}
        try:
            res_count = supabase.table("fixify_registry").select("id", count="exact").execute()
            next_num = (res_count.count or 0) + 1
            generated_job_id = f"FIX{next_num:04d}"
            
            payload = {
                "id": generated_job_id,
                "name": data.get("name"),
                "phone1": data.get("phone1"),
                "category": data.get("category"),
                "device": data.get("device"),
                "imei": data.get("imei"),
                "password": data.get("password"),
                "problem": data.get("problem"),
                "solution": data.get("solution", "Standard Fix Required"),
                "estimate": float(data.get("estimate", 0)),
                "advance": float(data.get("advance", 0)),
                "status": "Pending",
                "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
                "created_by": session["user"]
            }
            supabase.table("fixify_registry").insert(payload).execute()
            return jsonify({"success": True, "id": generated_job_id})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
            
    try:
        res = supabase.table("fixify_registry").select("*").order("date", desc=True).execute()
        return jsonify(res.data or [])
    except Exception:
        return jsonify([])

@app.route("/api/update_status", methods=["POST"])
def update_status():
    if "user" not in session:
        return jsonify({"success": False}), 401
    data = request.json or {}
    try:
        supabase.table("fixify_registry").update({"status": data.get("status")}).eq("id", data.get("id")).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/update_pricing", methods=["POST"])
def update_pricing():
    if "user" not in session or session.get("role") != "Chairman":
        return jsonify({"success": False, "message": "Restricted administrative override node."}), 403
        
    data = request.json or {}
    job_id = data.get("id")
    disc = float(data.get("discount", 0))
    
    try:
        if list == -999 or disc == -999:
            supabase.table("fixify_registry").delete().eq("id", job_id).execute()
            return jsonify({"success": True, "message": "Purged successfully"})

        if disc == -1:
            custom_name = data.get("custom_name")
            custom_phone = data.get("custom_phone")
            supabase.table("fixify_registry").update({
                "name": custom_name,
                "phone1": custom_phone
            }).eq("id", job_id).execute()
            return jsonify({"success": True, "message": "Profile synced"})

        payload = {
            "discount": disc,
            "extra_charge": float(data.get("extra_charge", 0)),
            "spare_cost": float(data.get("spare_cost", 0))
        }
        supabase.table("fixify_registry").update(payload).eq("id", job_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/parts", methods=["GET", "POST", "DELETE"])
def handle_parts():
    if "user" not in session:
        return jsonify([]), 401
    if request.method == "POST":
        if session.get("role") != "Chairman": return jsonify({"success":False}), 403
        data = request.json or {}
        payload = {
            "part_name": data.get("part_name"), "model": data.get("model"),
            "price": float(data.get("price", 0)), "date": datetime.now().strftime("%d-%m-%Y")
        }
        supabase.table("fixify_parts").insert(payload).execute()
        return jsonify({"success": True})
    elif request.method == "DELETE":
        if session.get("role") != "Chairman": return jsonify({"success":False}), 403
        part_id = request.args.get("id")
        supabase.table("fixify_parts").delete().eq("id", part_id).execute()
        return jsonify({"success": True})
    try:
        res = supabase.table("fixify_parts").select("*").execute()
        return jsonify(res.data or [])
    except Exception: return jsonify([])

# 🔥 FIXED INCORRECT PARAMETER METHOD MAPPING IN EMPLOYEE ROUTE
@app.route("/api/employees", methods=["GET", "POST", "DELETE"])
def handle_employees():
    if "user" not in session or session.get("role") != "Chairman":
        return jsonify([]), 403
    if request.method == "POST":
        data = request.json or {}
        payload = {"emp_name": data.get("emp_name"), "username": data.get("username"), "password": data.get("password")}
        supabase.table("fixify_staff").insert(payload).execute()
        return jsonify({"success": True})
    elif request.method == "DELETE":
        u = request.args.get("username")
        supabase.table("fixify_staff").delete().eq("username", u).execute()
        return jsonify({"success": True})
    try:
        res = supabase.table("fixify_staff").select("*").execute()
        return jsonify(res.data or [])
    except Exception: return jsonify([])

@app.route("/api/update_chairman_pass", methods=["POST"])
def update_chairman_pass():
    if "user" not in session or session.get("role") != "Chairman": return jsonify({"success":False}), 403
    np = (request.json or {}).get("new_password")
    try:
        supabase.table("fixify_chairman").update({"password": np}).eq("username", "admin").execute()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
