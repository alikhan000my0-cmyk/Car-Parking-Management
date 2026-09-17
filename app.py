from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import sqlite3

app = Flask(__name__)

app.secret_key = "carparking123"

DATABASE = "parking.db"

slots = ["A1", "A2", "A3", "A4", "A5"]

RATES = {
    "Bike": 10,
    "Car": 20,
    "SUV": 30
}


# =========================
# DATABASE CONNECTION
# =========================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================
# CREATE DATABASE TABLES
# =========================

def init_db():

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            vehicle TEXT NOT NULL,

            owner TEXT NOT NULL,

            mobile TEXT NOT NULL,

            type TEXT NOT NULL,

            slot TEXT NOT NULL,

            entry_time TEXT NOT NULL

        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            vehicle TEXT NOT NULL,

            owner TEXT NOT NULL,

            slot TEXT NOT NULL,

            type TEXT NOT NULL,

            entry_time TEXT NOT NULL,

            exit_time TEXT NOT NULL,

            hours INTEGER NOT NULL,

            rate INTEGER NOT NULL,

            fee INTEGER NOT NULL

        )
    """)

    conn.commit()

    conn.close()


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        if username == "alikhan77" and password == "Ali@77":

            session["admin"] = True

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="❌ Wrong username or password!"
        )

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM vehicles ORDER BY id DESC"
    )

    vehicles = cursor.fetchall()

    cursor.execute(
        "SELECT SUM(fee) AS total FROM history"
    )

    result = cursor.fetchone()

    total_collection = result["total"] or 0

    conn.close()

    occupied = len(vehicles)

    available = len(slots) - occupied

    return render_template(
        "index.html",
        total_slots=len(slots),
        occupied=occupied,
        available=available,
        total_collection=total_collection,
        vehicles=vehicles,
        slots=slots
    )


# =========================
# PARK VEHICLE
# =========================

@app.route("/parking", methods=["GET", "POST"])
def parking():

    if "admin" not in session:
        return redirect("/")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT slot FROM vehicles"
    )

    occupied_slots = [
        row["slot"] for row in cursor.fetchall()
    ]

    available_slots = [
        slot for slot in slots
        if slot not in occupied_slots
    ]

    if request.method == "POST":

        vehicle = request.form["vehicle"]

        owner = request.form["owner"]

        mobile = request.form["mobile"]

        vehicle_type = request.form["type"]

        slot = request.form["slot"]

        if slot in occupied_slots:

            conn.close()

            return "❌ This slot is already occupied!"

        entry_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            INSERT INTO vehicles
            (vehicle, owner, mobile, type, slot, entry_time)

            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            vehicle,
            owner,
            mobile,
            vehicle_type,
            slot,
            entry_time
        ))

        conn.commit()

        conn.close()

        return redirect("/dashboard")

    conn.close()

    return render_template(
        "parking.html",
        available_slots=available_slots
    )


# =========================
# REMOVE VEHICLE
# =========================

@app.route("/remove", methods=["GET", "POST"])
def remove():

    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":

        vehicle_number = request.form["vehicle"]

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM vehicles
            WHERE LOWER(vehicle) = LOWER(?)
        """, (vehicle_number,))

        vehicle = cursor.fetchone()

        if vehicle is None:

            conn.close()

            return render_template(
                "remove.html",
                message="❌ Vehicle not found!"
            )

        entry_time = datetime.strptime(
            vehicle["entry_time"],
            "%Y-%m-%d %H:%M:%S"
        )

        exit_time = datetime.now()

        duration = exit_time - entry_time

        hours = max(
            1,
            int(duration.total_seconds() / 3600)
        )

        rate = RATES.get(
            vehicle["type"],
            20
        )

        fee = hours * rate

        cursor.execute("""
            INSERT INTO history
            (
                vehicle,
                owner,
                slot,
                type,
                entry_time,
                exit_time,
                hours,
                rate,
                fee
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle["vehicle"],
            vehicle["owner"],
            vehicle["slot"],
            vehicle["type"],
            vehicle["entry_time"],
            exit_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            hours,
            rate,
            fee
        ))

        cursor.execute(
            "DELETE FROM vehicles WHERE id = ?",
            (vehicle["id"],)
        )

        conn.commit()

        conn.close()

        return render_template(
            "receipt.html",
            vehicle=vehicle,
            entry_time=entry_time,
            exit_time=exit_time,
            hours=hours,
            rate=rate,
            fee=fee
        )

    return render_template(
        "remove.html",
        message=""
    )


# =========================
# SEARCH VEHICLE
# =========================

@app.route("/search", methods=["GET", "POST"])
def search():

    if "admin" not in session:
        return redirect("/")

    vehicle = None

    if request.method == "POST":

        vehicle_number = request.form["vehicle"]

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM vehicles
            WHERE LOWER(vehicle) = LOWER(?)
        """, (vehicle_number,))

        vehicle = cursor.fetchone()

        conn.close()

    return render_template(
        "search.html",
        vehicle=vehicle
    )


# =========================
# PARKING HISTORY
# =========================

@app.route("/history")
def show_history():

    if "admin" not in session:
        return redirect("/")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM history
        ORDER BY id DESC
    """)

    history = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history
    )


# =========================
# TOTAL COLLECTION
# =========================

@app.route("/collection")
def collection():

    if "admin" not in session:
        return redirect("/")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT SUM(fee) AS total FROM history"
    )

    result = cursor.fetchone()

    total = result["total"] or 0

    conn.close()

    return render_template(
        "collection.html",
        total=total
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# START DATABASE
# =========================

init_db()


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(debug=True)
