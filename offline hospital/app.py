import requests
import sqlite3
import threading
import time

from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

LOCAL_DB = "hospital.db"
SERVER_DB = "server.db"

SERVER_URL = "http://127.0.0.1:5001"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_local_db():
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_server_db():
    conn = sqlite3.connect(SERVER_DB)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# ACTIVITY LOG HELPER
# =========================================================

def add_activity_log(patient_id, action, details):

    try:

        conn = get_local_db()

        conn.execute("""
            INSERT INTO activity_logs
            (patient_id, action, details)
            VALUES (?, ?, ?)
        """, (
            patient_id,
            action,
            details
        ))

        conn.commit()
        conn.close()

    except Exception as e:

        print("Activity log error:", e)


# =========================================================
# CREATE DATABASES
# =========================================================

def init_databases():

    # =====================================================
    # LOCAL DATABASE
    # =====================================================

    conn = get_local_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            symptoms TEXT,
            synced INTEGER DEFAULT 0
        )
    """)

    # Add AI columns if they don't already exist
    columns = [
        ("ai_priority", "TEXT"),
        ("ai_message", "TEXT")
    ]

    for column_name, column_type in columns:

        try:

            conn.execute(
                f"ALTER TABLE patients ADD COLUMN {column_name} {column_type}"
            )

        except sqlite3.OperationalError:
            pass


    # =====================================================
    # APPOINTMENTS
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            department TEXT,
            appt_date TEXT,
            appt_time TEXT,
            synced INTEGER DEFAULT 0
        )
    """)


    # =====================================================
    # ACTIVITY LOG
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    conn.commit()
    conn.close()


    # =====================================================
    # SERVER DATABASE
    # =====================================================

    conn = get_server_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            symptoms TEXT
        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            department TEXT,
            appt_date TEXT,
            appt_time TEXT
        )
    """)


    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return "Offline AI Hospital Management System is Running!"


# =========================================================
# PAGES
# =========================================================

@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html")


@app.route("/register")
def register_page():

    return render_template("register.html")


@app.route("/book")
def book_page():

    return render_template("appointment.html")


@app.route("/assistant")
def assistant_page():

    return render_template("assistant.html")


# =========================================================
# SERVER STATUS
# =========================================================

@app.route("/server-status")
def server_status():

    try:

        response = requests.get(
            f"{SERVER_URL}/health",
            timeout=2
        )

        if response.status_code == 200:

            return jsonify({
                "online": True
            })

    except:

        pass


    return jsonify({
        "online": False
    })


# =========================================================
# PATIENT REGISTRATION
# =========================================================

@app.route("/register_patient", methods=["POST"])
def register_patient():

    data = request.get_json()

    name = data.get("name")
    age = data.get("age")
    gender = data.get("gender")
    phone = data.get("phone")
    symptoms = data.get("symptoms")


    # Validation

    if not name:

        return jsonify({
            "success": False,
            "message": "Patient name is required"
        }), 400


    if not symptoms:

        return jsonify({
            "success": False,
            "message": "Symptoms are required"
        }), 400


    try:

        age = int(age)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Age must be a number"
        }), 400


    conn = get_local_db()


    # =====================================================
    # OFFLINE AI ANALYSIS
    # =====================================================

    ai_result = analyze_symptoms(
        symptoms,
        age
    )

    ai_priority = ai_result["priority"]
    ai_message = ai_result["message"]


    # =====================================================
    # INSERT PATIENT
    # =====================================================

    conn.execute("""
        INSERT INTO patients
        (
            name,
            age,
            gender,
            phone,
            symptoms,
            ai_priority,
            ai_message,
            synced
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        name,
        age,
        gender,
        phone,
        symptoms,
        ai_priority,
        ai_message
    ))


    # Get newly created patient ID

    patient_id = conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]


    # =====================================================
    # ACTIVITY LOG
    # =====================================================

    conn.execute("""
        INSERT INTO activity_logs
        (
            patient_id,
            action,
            details
        )
        VALUES (?, ?, ?)
    """, (
        patient_id,
        "PATIENT_ADDED",
        f"Patient {name} registered successfully"
    ))


    conn.commit()
    conn.close()


    return jsonify({

        "success": True,

        "message":
            "Patient registered successfully",

        "ai_priority":
            ai_priority,

        "ai_message":
            ai_message,

        "sync_status":
            "Pending"

    })


# =========================================================
# EDIT PATIENT
# =========================================================

@app.route(
    "/edit-patient/<int:patient_id>",
    methods=["PUT"]
)
def edit_patient(patient_id):

    data = request.get_json()

    try:

        conn = get_local_db()


        # Check patient exists

        patient = conn.execute("""
            SELECT name
            FROM patients
            WHERE id = ?
        """, (
            patient_id,
        )).fetchone()


        if not patient:

            conn.close()

            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404


        name = data.get("name")
        age = data.get("age")
        gender = data.get("gender")
        phone = data.get("phone")
        symptoms = data.get("symptoms")


        # =================================================
        # RE-ANALYZE SYMPTOMS
        # =================================================

        ai_result = analyze_symptoms(
            symptoms or "",
            age
        )

        ai_priority = ai_result["priority"]
        ai_message = ai_result["message"]


        # =================================================
        # UPDATE PATIENT
        # =================================================

        conn.execute("""
            UPDATE patients
            SET
                name = ?,
                age = ?,
                gender = ?,
                phone = ?,
                symptoms = ?,
                ai_priority = ?,
                ai_message = ?,
                synced = 0
            WHERE id = ?
        """, (
            name,
            age,
            gender,
            phone,
            symptoms,
            ai_priority,
            ai_message,
            patient_id
        ))


        # =================================================
        # ACTIVITY LOG
        # =================================================

        conn.execute("""
            INSERT INTO activity_logs
            (
                patient_id,
                action,
                details
            )
            VALUES (?, ?, ?)
        """, (
            patient_id,
            "PATIENT_EDITED",
            f"Patient {name} details updated"
        ))


        conn.commit()
        conn.close()


        return jsonify({

            "success": True,

            "message":
                "Patient updated locally",

            "ai_priority":
                ai_priority,

            "ai_message":
                ai_message

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# =========================================================
# DELETE PATIENT
# =========================================================

@app.route(
    "/delete-patient/<int:patient_id>",
    methods=["DELETE"]
)
def delete_local_patient(patient_id):

    try:

        conn = get_local_db()


        # Get patient name before deleting

        patient = conn.execute("""
            SELECT name
            FROM patients
            WHERE id = ?
        """, (
            patient_id,
        )).fetchone()


        if not patient:

            conn.close()

            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404


        patient_name = patient["name"]


        # =================================================
        # LOG DELETE BEFORE DELETE
        # =================================================

        conn.execute("""
            INSERT INTO activity_logs
            (
                patient_id,
                action,
                details
            )
            VALUES (?, ?, ?)
        """, (
            patient_id,
            "PATIENT_DELETED",
            f"Patient {patient_name} deleted"
        ))


        # =================================================
        # DELETE PATIENT
        # =================================================

        conn.execute("""
            DELETE FROM patients
            WHERE id = ?
        """, (
            patient_id,
        ))


        conn.commit()
        conn.close()


        return jsonify({

            "success": True,

            "message":
                "Patient deleted successfully"

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# =========================================================
# ACTIVITY LOGS
# =========================================================

@app.route("/activity-logs", methods=["GET"])
def get_activity_logs():

    try:

        conn = get_local_db()


        logs = conn.execute("""
            SELECT
                id,
                patient_id,
                action,
                details,
                created_at
            FROM activity_logs
            ORDER BY id DESC
        """).fetchall()


        conn.close()


        return jsonify({

            "success": True,

            "logs": [
                dict(log)
                for log in logs
            ]

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# =========================================================
# APPOINTMENT BOOKING
# =========================================================

@app.route(
    "/book_appointment",
    methods=["POST"]
)
def book_appointment():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    department = data.get("department")
    appt_date = data.get("date")
    appt_time = data.get("time")


    if (
        not name
        or not department
        or not appt_date
        or not appt_time
    ):

        return jsonify({

            "success": False,

            "message":
                "Name, department, date and time are required"

        }), 400


    conn = get_local_db()


    conn.execute("""
        INSERT INTO appointments
        (
            name,
            email,
            phone,
            department,
            appt_date,
            appt_time,
            synced
        )
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        name,
        email,
        phone,
        department,
        appt_date,
        appt_time
    ))


    conn.commit()
    conn.close()


    return jsonify({

        "success": True,

        "message":
            "Appointment booked successfully",

        "sync_status":
            "Pending"

    })


# =========================================================
# GET APPOINTMENTS
# =========================================================

@app.route(
    "/appointments",
    methods=["GET"]
)
def get_appointments():

    conn = get_local_db()


    appointments = conn.execute("""
        SELECT *
        FROM appointments
        ORDER BY id DESC
    """).fetchall()


    conn.close()


    return jsonify({

        "success": True,

        "total_appointments":
            len(appointments),

        "appointments":
            [
                dict(a)
                for a in appointments
            ]

    })


# =========================================================
# OFFLINE FAQ ASSISTANT
# =========================================================

HOSPITAL_FAQ = [

    (
        ["service", "services", "offer"],

        "Our hospital offers Cardiology, Pediatrics, General Medicine, "
        "Emergency Care, and Orthopedics."
    ),

    (
        ["emergency"],

        "The Emergency Department operates 24/7. In a medical emergency, "
        "go directly to the Emergency entrance."
    ),

    (
        ["visiting hour", "visiting hours", "visit"],

        "General visiting hours are 10:00 AM - 12:00 PM "
        "and 4:00 PM - 6:00 PM daily."
    ),

    (
        ["book", "appointment", "booking", "schedule"],

        "You can book an appointment on the Book Appointment page — "
        "choose a department, date, and time."
    ),

    (
        ["children", "child", "kid", "pediatric"],

        "The Pediatrics department handles treatment for children."
    ),

    (
        ["location", "address", "where"],

        "Please check the hospital's official address on the "
        "reception page."
    ),

    (
        ["timing", "open", "opd", "hour"],

        "The hospital is open 24 hours for emergencies. "
        "Outpatient (OPD) timings are 9:00 AM - 5:00 PM."
    ),

    (
        ["department", "departments"],

        "Departments available: Cardiology, Pediatrics, "
        "General Medicine, Emergency Care, and Orthopedics."
    )

]


def answer_question(question):

    q = question.lower().strip()


    for keywords, answer in HOSPITAL_FAQ:

        for keyword in keywords:

            if keyword in q:

                return answer


    return (
        "I don't have information on that yet. "
        "Please contact hospital reception for further assistance."
    )


@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    question = data.get("question")


    if not question:

        return jsonify({

            "success": False,

            "message":
                "Question is required"

        }), 400


    answer = answer_question(question)


    return jsonify({

        "success": True,

        "question": question,

        "answer": answer

    })


# =========================================================
# SYNC PATIENT DATA
# =========================================================

def sync_pending_data():

    conn = get_local_db()


    pending_patients = conn.execute("""
        SELECT *
        FROM patients
        WHERE synced = 0
    """).fetchall()


    for patient in pending_patients:

        data = {

            "id":
                patient["id"],

            "name":
                patient["name"],

            "age":
                patient["age"],

            "gender":
                patient["gender"],

            "phone":
                patient["phone"],

            "symptoms":
                patient["symptoms"],

            "ai_priority":
                patient["ai_priority"],

            "ai_message":
                patient["ai_message"]

        }


        try:

            response = requests.post(

                f"{SERVER_URL}/sync_patient",

                json=data,

                timeout=3

            )


            if response.status_code == 200:

                conn.execute("""
                    UPDATE patients
                    SET synced = 1
                    WHERE id = ?
                """, (
                    patient["id"],
                ))


                # Activity log

                conn.execute("""
                    INSERT INTO activity_logs
                    (
                        patient_id,
                        action,
                        details
                    )
                    VALUES (?, ?, ?)
                """, (

                    patient["id"],

                    "PATIENT_SYNCED",

                    f"Patient {patient['name']} synced to server"

                ))


                print(
                    f"Patient {patient['id']} synced successfully."
                )


        except requests.exceptions.RequestException:

            print(
                "Server unavailable. "
                "Keeping data locally."
            )


    conn.commit()
    conn.close()


# =========================================================
# SYNC APPOINTMENTS
# =========================================================

def sync_pending_appointments():

    conn = get_local_db()


    pending_appointments = conn.execute("""
        SELECT *
        FROM appointments
        WHERE synced = 0
    """).fetchall()


    for appt in pending_appointments:

        data = {

            "id":
                appt["id"],

            "name":
                appt["name"],

            "email":
                appt["email"],

            "phone":
                appt["phone"],

            "department":
                appt["department"],

            "appt_date":
                appt["appt_date"],

            "appt_time":
                appt["appt_time"]

        }


        try:

            response = requests.post(

                f"{SERVER_URL}/sync_appointment",

                json=data,

                timeout=3

            )


            if response.status_code == 200:

                conn.execute("""
                    UPDATE appointments
                    SET synced = 1
                    WHERE id = ?
                """, (
                    appt["id"],
                ))


                print(
                    f"Appointment {appt['id']} synced successfully."
                )


        except requests.exceptions.RequestException:

            print(
                "Server unavailable. "
                "Keeping appointment locally."
            )


    conn.commit()
    conn.close()

# =========================================================
# OFFLINE AI SYMPTOM ANALYSIS
# =========================================================

def analyze_symptoms(symptoms, age=0):

    symptoms = (symptoms or "").lower().strip()

    try:
        age = int(age)
    except (ValueError, TypeError):
        age = 0


    # =====================================================
    # URGENT SYMPTOMS
    # =====================================================

    urgent_keywords = [

        "chest pain",
        "chest pressure",
        "difficulty breathing",
        "breathing difficulty",
        "shortness of breath",
        "severe bleeding",
        "heavy bleeding",
        "unconscious",
        "fainted",
        "seizure",
        "stroke",
        "severe allergic reaction",
        "face drooping",
        "paralysis"

    ]


    # =====================================================
    # MODERATE SYMPTOMS
    # =====================================================

    moderate_keywords = [

        "high fever",
        "fever",
        "vomiting",
        "dehydration",
        "severe headache",
        "persistent pain",
        "dizziness",
        "diarrhea",
        "abdominal pain",
        "stomach pain",
        "infection",
        "weakness"

    ]


    # =====================================================
    # CHECK URGENT SYMPTOMS FIRST
    # =====================================================

    for keyword in urgent_keywords:

        if keyword in symptoms:

            return {

                "priority": "URGENT",

                "message":
                    f"Potentially serious symptom detected: "
                    f"{keyword}. Immediate medical assessment "
                    f"is recommended."

            }


    # =====================================================
    # ELDERLY PATIENT + MODERATE SYMPTOM
    # =====================================================

    if age >= 65:

        for keyword in moderate_keywords:

            if keyword in symptoms:

                return {

                    "priority": "URGENT",

                    "message":
                        f"The patient is age {age} and has "
                        f"{keyword}. Higher-priority medical "
                        f"assessment is recommended."

                }


    # =====================================================
    # CHECK MODERATE SYMPTOMS
    # =====================================================

    for keyword in moderate_keywords:

        if keyword in symptoms:

            return {

                "priority": "MODERATE",

                "message":
                    f"Symptom detected: {keyword}. "
                    f"Medical assessment is recommended."

            }


    # =====================================================
    # NORMAL
    # =====================================================

    return {

        "priority": "NORMAL",

        "message":
            "No high-priority symptom pattern was detected. "
            "Routine medical assessment may be appropriate."

    }


# =========================================================
# AUTOMATIC SYNC
# =========================================================

def automatic_sync():

    while True:

        time.sleep(10)

        print(
            "\nChecking for pending data..."
        )

        sync_pending_data()

        sync_pending_appointments()


# =========================================================
# DOCTOR DASHBOARD - PATIENTS
# =========================================================

@app.route(
    "/patients",
    methods=["GET"]
)
def get_patients():

    conn = get_local_db()


    patients = conn.execute("""
        SELECT
            id,
            name,
            age,
            gender,
            phone,
            symptoms,
            ai_priority,
            ai_message,
            synced
        FROM patients

        ORDER BY
            CASE ai_priority
                WHEN 'URGENT' THEN 1
                WHEN 'MODERATE' THEN 2
                ELSE 3
            END,

            id DESC
    """).fetchall()


    conn.close()


    patient_list = []


    for patient in patients:

        patient_list.append(
            dict(patient)
        )


    return jsonify({

        "success":
            True,

        "total_patients":
            len(patient_list),

        "patients":
            patient_list

    })


# =========================================================
# MANUAL SYNC
# =========================================================

@app.route(
    "/sync",
    methods=["POST"]
)
def sync_data():

    sync_pending_data()

    sync_pending_appointments()


    return jsonify({

        "success":
            True,

        "message":
            "Synchronization completed"

    })


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    init_databases()


    # Start automatic sync

    sync_thread = threading.Thread(

        target=automatic_sync,

        daemon=True

    )

    sync_thread.start()


    app.run(

        debug=True,

        use_reloader=False

    )