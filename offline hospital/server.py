from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

SERVER_DB = "server.db"

def init_db():
    conn = sqlite3.connect(SERVER_DB)

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

    # Add AI columns to existing database
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

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/sync_patient", methods=["POST"])
def sync_patient():

    data = request.get_json(silent=True) or {}

    required = ["id", "name"]
    missing = [field for field in required if not data.get(field)]

    if missing:
        return jsonify({
            "success": False,
            "message": f"Missing required field(s): {', '.join(missing)}"
        }), 400

    conn = sqlite3.connect(SERVER_DB)

    conn.execute("""
        INSERT OR REPLACE INTO patients
        (id, name, age, gender, phone, symptoms,
         ai_priority, ai_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        data["name"],
        data.get("age"),
        data.get("gender"),
        data.get("phone"),
        data.get("symptoms"),
        data.get("ai_priority"),
        data.get("ai_message")
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Patient synced to server"
    })


@app.route("/sync_appointment", methods=["POST"])
def sync_appointment():

    data = request.get_json(silent=True) or {}

    required = ["id", "name"]
    missing = [field for field in required if not data.get(field)]

    if missing:
        return jsonify({
            "success": False,
            "message": f"Missing required field(s): {', '.join(missing)}"
        }), 400

    conn = sqlite3.connect(SERVER_DB)

    conn.execute("""
        INSERT OR REPLACE INTO appointments
        (id, name, email, phone, department, appt_date, appt_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        data["name"],
        data.get("email"),
        data.get("phone"),
        data.get("department"),
        data.get("appt_date"),
        data.get("appt_time")
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Appointment synced to server"
    })

# ================= EDIT PATIENT =================

@app.route("/update-patient/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id):

    data = request.get_json()

    try:
        conn = sqlite3.connect(SERVER_DB)

        conn.execute("""
            UPDATE patients
            SET name = ?,
                age = ?,
                gender = ?,
                phone = ?,
                symptoms = ?,
                ai_priority = ?,
                ai_message = ?
            WHERE id = ?
        """, (
            data.get("name"),
            data.get("age"),
            data.get("gender"),
            data.get("phone"),
            data.get("symptoms"),
            data.get("ai_priority"),
            data.get("ai_message"),
            patient_id
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Patient updated successfully"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ================= DELETE PATIENT =================

@app.route("/delete-patient/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id):

    try:
        conn = sqlite3.connect(SERVER_DB)

        conn.execute(
            "DELETE FROM patients WHERE id = ?",
            (patient_id,)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Patient deleted successfully"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
if __name__ == "__main__":
    init_db()
    app.run(port=5001, debug=True)