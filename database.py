"""
database.py - SQLite Database access layer for VehicleCare
Handles schema creation, connections, parameterized queries, transactions,
and database backups/restores.
"""

import os
import sqlite3
import shutil
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "vehiclecare.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return the absolute path to the database file."""
    if custom_path:
        return os.path.abspath(custom_path)
    os.makedirs(DEFAULT_DB_DIR, exist_ok=True)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establish a connection with SQLite, enforce foreign keys and row factory.
    Caller is responsible for closing, or use managed_connection().
    """
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def managed_connection(db_path: Optional[str] = None):
    """Context manager that ensures the sqlite3 connection is properly closed."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables, indexes and default settings."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()

        # Vehicles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_type TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                registration_number TEXT NOT NULL COLLATE NOCASE UNIQUE,
                purchase_date TEXT,
                current_odometer REAL NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Fuel records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuel_records (
                fuel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                purchase_date TEXT NOT NULL,
                litres REAL NOT NULL,
                price_per_litre REAL NOT NULL,
                total_cost REAL NOT NULL,
                odometer REAL NOT NULL,
                fuel_station TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
            )
        """)

        # Service records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_records (
                service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                service_date TEXT NOT NULL,
                odometer REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                service_centre TEXT,
                cost REAL NOT NULL,
                next_service_date TEXT,
                next_service_odometer REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
            )
        """)

        # Expenses table (Other expenses excluding fuel and service)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_vehicle ON fuel_records(vehicle_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fuel_date ON fuel_records(purchase_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_vehicle ON service_records(vehicle_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service_date ON service_records(service_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_vehicle ON expenses(vehicle_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);")

        # Default settings
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('currency', '₹')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reminder_days', '7')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('app_version', '1.0.0')")

        conn.commit()


# =====================================================================
# VEHICLE OPERATIONS
# =====================================================================

def get_all_vehicles(db_path: Optional[str] = None) -> List[sqlite3.Row]:
    """Retrieve all vehicles ordered by brand and model."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT vehicle_id, vehicle_type, brand, model, registration_number,
                   purchase_date, current_odometer, notes, created_at
            FROM vehicles
            ORDER BY brand ASC, model ASC
        """)
        return cursor.fetchall()


def get_vehicle_by_id(vehicle_id: int, db_path: Optional[str] = None) -> Optional[sqlite3.Row]:
    """Retrieve a single vehicle by its ID."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        return cursor.fetchone()


def get_vehicle_by_registration(reg_number: str, exclude_id: Optional[int] = None, db_path: Optional[str] = None) -> Optional[sqlite3.Row]:
    """Check for existing vehicle with the same registration number (case-insensitive)."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        clean_reg = reg_number.strip()
        if exclude_id is not None:
            cursor.execute(
                "SELECT * FROM vehicles WHERE LOWER(registration_number) = LOWER(?) AND vehicle_id != ?",
                (clean_reg, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT * FROM vehicles WHERE LOWER(registration_number) = LOWER(?)",
                (clean_reg,)
            )
        return cursor.fetchone()


def add_vehicle(vehicle_type: str, brand: str, model: str, registration_number: str,
                purchase_date: Optional[str], current_odometer: float,
                notes: Optional[str] = None, db_path: Optional[str] = None) -> int:
    """Insert a new vehicle into the database."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehicles (vehicle_type, brand, model, registration_number, purchase_date, current_odometer, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_type.strip(),
            brand.strip(),
            model.strip(),
            registration_number.strip().upper(),
            purchase_date.strip() if purchase_date else None,
            float(current_odometer),
            notes.strip() if notes else None
        ))
        conn.commit()
        return cursor.lastrowid


def update_vehicle(vehicle_id: int, vehicle_type: str, brand: str, model: str,
                   registration_number: str, purchase_date: Optional[str],
                   current_odometer: float, notes: Optional[str] = None,
                   db_path: Optional[str] = None) -> bool:
    """Update vehicle details."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vehicles
            SET vehicle_type = ?, brand = ?, model = ?, registration_number = ?,
                purchase_date = ?, current_odometer = ?, notes = ?
            WHERE vehicle_id = ?
        """, (
            vehicle_type.strip(),
            brand.strip(),
            model.strip(),
            registration_number.strip().upper(),
            purchase_date.strip() if purchase_date else None,
            float(current_odometer),
            notes.strip() if notes else None,
            vehicle_id
        ))
        conn.commit()
        return cursor.rowcount > 0


def update_vehicle_odometer_if_higher(vehicle_id: int, new_odometer: float, db_path: Optional[str] = None) -> None:
    """Keep the vehicle's current odometer synchronized if a newer service/fuel entry has a higher reading."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vehicles
            SET current_odometer = ?
            WHERE vehicle_id = ? AND current_odometer < ?
        """, (float(new_odometer), vehicle_id, float(new_odometer)))
        conn.commit()


def delete_vehicle(vehicle_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a vehicle and cascade deletes to related records."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_vehicle_dependent_counts(vehicle_id: int, db_path: Optional[str] = None) -> Dict[str, int]:
    """Count dependent fuel, service, and expense records for safety prompts."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fuel_records WHERE vehicle_id = ?", (vehicle_id,))
        fuel_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM service_records WHERE vehicle_id = ?", (vehicle_id,))
        service_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM expenses WHERE vehicle_id = ?", (vehicle_id,))
        expense_count = cursor.fetchone()[0]
        return {
            "fuel": fuel_count,
            "service": service_count,
            "expenses": expense_count,
            "total": fuel_count + service_count + expense_count
        }


# =====================================================================
# FUEL OPERATIONS & MILEAGE CALCULATION
# =====================================================================

def get_fuel_records(vehicle_id: Optional[int] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     db_path: Optional[str] = None) -> List[sqlite3.Row]:
    """Fetch fuel records with optional filtering, sorted by purchase date and odometer desc."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT f.fuel_id, f.vehicle_id, f.purchase_date, f.litres,
                   f.price_per_litre, f.total_cost, f.odometer, f.fuel_station,
                   f.notes, f.created_at,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   v.registration_number
            FROM fuel_records f
            JOIN vehicles v ON f.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        params: List[Any] = []
        if vehicle_id:
            query += " AND f.vehicle_id = ?"
            params.append(vehicle_id)
        if start_date:
            query += " AND f.purchase_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND f.purchase_date <= ?"
            params.append(end_date)

        query += " ORDER BY f.purchase_date DESC, f.odometer DESC, f.fuel_id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def add_fuel_record(vehicle_id: int, purchase_date: str, litres: float,
                    price_per_litre: float, odometer: float,
                    fuel_station: Optional[str] = None, notes: Optional[str] = None,
                    db_path: Optional[str] = None) -> int:
    """Add a fuel purchase record and update vehicle odometer if reading is higher."""
    total_cost = round(float(litres) * float(price_per_litre), 2)
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fuel_records (vehicle_id, purchase_date, litres, price_per_litre, total_cost, odometer, fuel_station, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            purchase_date.strip(),
            round(float(litres), 3),
            round(float(price_per_litre), 2),
            total_cost,
            float(odometer),
            fuel_station.strip() if fuel_station else None,
            notes.strip() if notes else None
        ))
        record_id = cursor.lastrowid
        conn.commit()

    update_vehicle_odometer_if_higher(vehicle_id, odometer, db_path)
    return record_id


def update_fuel_record(fuel_id: int, vehicle_id: int, purchase_date: str,
                       litres: float, price_per_litre: float, odometer: float,
                       fuel_station: Optional[str] = None, notes: Optional[str] = None,
                       db_path: Optional[str] = None) -> bool:
    """Update an existing fuel record."""
    total_cost = round(float(litres) * float(price_per_litre), 2)
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fuel_records
            SET vehicle_id = ?, purchase_date = ?, litres = ?, price_per_litre = ?,
                total_cost = ?, odometer = ?, fuel_station = ?, notes = ?
            WHERE fuel_id = ?
        """, (
            vehicle_id,
            purchase_date.strip(),
            round(float(litres), 3),
            round(float(price_per_litre), 2),
            total_cost,
            float(odometer),
            fuel_station.strip() if fuel_station else None,
            notes.strip() if notes else None,
            fuel_id
        ))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        update_vehicle_odometer_if_higher(vehicle_id, odometer, db_path)
    return success


def delete_fuel_record(fuel_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a fuel record."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fuel_records WHERE fuel_id = ?", (fuel_id,))
        conn.commit()
        return cursor.rowcount > 0


def calculate_fuel_mileage_for_vehicle(vehicle_id: int, db_path: Optional[str] = None) -> Dict[int, Optional[float]]:
    """
    Calculate mileage (km/L) for each fuel record of a vehicle.
    Method:
      Records are ordered chronologically by purchase_date ASC, odometer ASC, fuel_id ASC.
      For record i (where i > 0):
        Distance = Odometer_i - Odometer_{i-1}
        If Distance > 0 and Litres_i > 0:
          Mileage = Distance / Litres_i
        Else:
          None (invalid backwards/zero odometer or invalid fuel)
      For the first record (i = 0):
        Mileage is None (N/A) because there is no prior refill to compare against.
    Returns:
      Dict mapping fuel_id -> mileage (km/L) or None if N/A.
    """
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fuel_id, purchase_date, odometer, litres
            FROM fuel_records
            WHERE vehicle_id = ?
            ORDER BY purchase_date ASC, odometer ASC, fuel_id ASC
        """, (vehicle_id,))
        records = cursor.fetchall()

    results: Dict[int, Optional[float]] = {}
    if not records:
        return results

    prev_record = None
    for rec in records:
        fid = rec["fuel_id"]
        odo = rec["odometer"]
        litres = rec["litres"]

        if prev_record is None:
            results[fid] = None  # First record, cannot calculate
        else:
            prev_odo = prev_record["odometer"]
            distance = odo - prev_odo
            if distance > 0 and litres > 0:
                results[fid] = round(distance / litres, 2)
            else:
                results[fid] = None  # Backwards or zero distance
        prev_record = rec

    return results


def calculate_overall_vehicle_mileage(vehicle_id: int, db_path: Optional[str] = None) -> Optional[float]:
    """
    Calculate overall average mileage across all consecutive valid fuel refills for a vehicle.
    Returns None if fewer than 2 records or total litres <= 0.
    """
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fuel_id, purchase_date, odometer, litres
            FROM fuel_records
            WHERE vehicle_id = ?
            ORDER BY purchase_date ASC, odometer ASC, fuel_id ASC
        """, (vehicle_id,))
        records = cursor.fetchall()

    if len(records) < 2:
        return None

    total_distance = 0.0
    total_litres = 0.0

    for i in range(1, len(records)):
        dist = records[i]["odometer"] - records[i-1]["odometer"]
        lit = records[i]["litres"]
        if dist > 0 and lit > 0:
            total_distance += dist
            total_litres += lit

    if total_litres > 0 and total_distance > 0:
        return round(total_distance / total_litres, 2)
    return None


# =====================================================================
# SERVICE HISTORY & REMINDERS
# =====================================================================

def get_service_records(vehicle_id: Optional[int] = None,
                        category: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        db_path: Optional[str] = None) -> List[sqlite3.Row]:
    """Fetch service records with optional filtering."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT s.service_id, s.vehicle_id, s.service_date, s.odometer,
                   s.category, s.description, s.service_centre, s.cost,
                   s.next_service_date, s.next_service_odometer, s.notes, s.created_at,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   v.registration_number
            FROM service_records s
            JOIN vehicles v ON s.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        params: List[Any] = []
        if vehicle_id:
            query += " AND s.vehicle_id = ?"
            params.append(vehicle_id)
        if category and category != "All":
            query += " AND s.category = ?"
            params.append(category)
        if start_date:
            query += " AND s.service_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.service_date <= ?"
            params.append(end_date)

        query += " ORDER BY s.service_date DESC, s.odometer DESC, s.service_id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def add_service_record(vehicle_id: int, service_date: str, odometer: float,
                       category: str, description: str, cost: float,
                       service_centre: Optional[str] = None,
                       next_service_date: Optional[str] = None,
                       next_service_odometer: Optional[float] = None,
                       notes: Optional[str] = None,
                       db_path: Optional[str] = None) -> int:
    """Add a new service record and update vehicle odometer if reading is higher."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO service_records (
                vehicle_id, service_date, odometer, category, description,
                service_centre, cost, next_service_date, next_service_odometer, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            service_date.strip(),
            float(odometer),
            category.strip(),
            description.strip(),
            service_centre.strip() if service_centre else None,
            round(float(cost), 2),
            next_service_date.strip() if next_service_date else None,
            float(next_service_odometer) if next_service_odometer is not None else None,
            notes.strip() if notes else None
        ))
        record_id = cursor.lastrowid
        conn.commit()

    update_vehicle_odometer_if_higher(vehicle_id, odometer, db_path)
    return record_id


def update_service_record(service_id: int, vehicle_id: int, service_date: str,
                          odometer: float, category: str, description: str, cost: float,
                          service_centre: Optional[str] = None,
                          next_service_date: Optional[str] = None,
                          next_service_odometer: Optional[float] = None,
                          notes: Optional[str] = None,
                          db_path: Optional[str] = None) -> bool:
    """Update a service record."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE service_records
            SET vehicle_id = ?, service_date = ?, odometer = ?, category = ?,
                description = ?, service_centre = ?, cost = ?,
                next_service_date = ?, next_service_odometer = ?, notes = ?
            WHERE service_id = ?
        """, (
            vehicle_id,
            service_date.strip(),
            float(odometer),
            category.strip(),
            description.strip(),
            service_centre.strip() if service_centre else None,
            round(float(cost), 2),
            next_service_date.strip() if next_service_date else None,
            float(next_service_odometer) if next_service_odometer is not None else None,
            notes.strip() if notes else None,
            service_id
        ))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        update_vehicle_odometer_if_higher(vehicle_id, odometer, db_path)
    return success


def delete_service_record(service_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a service record."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM service_records WHERE service_id = ?", (service_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_upcoming_reminders(lead_days: int = 7, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve upcoming and overdue maintenance reminders based on next_service_date
    and next_service_odometer from service records.
    Returns sorted list with status: 'OVERDUE', 'DUE SOON', or 'UPCOMING'.
    """
    today = date.today()
    threshold_date = today + timedelta(days=lead_days)

    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.service_id, s.vehicle_id, s.category, s.description,
                   s.next_service_date, s.next_service_odometer, s.service_date,
                   v.brand || ' ' || v.model AS vehicle_model,
                   v.registration_number, v.current_odometer
            FROM service_records s
            JOIN vehicles v ON s.vehicle_id = v.vehicle_id
            WHERE s.next_service_date IS NOT NULL OR s.next_service_odometer IS NOT NULL
            ORDER BY s.next_service_date ASC
        """)
        rows = cursor.fetchall()

    reminders = []
    for row in rows:
        next_date_str = row["next_service_date"]
        next_odo = row["next_service_odometer"]
        curr_odo = row["current_odometer"] or 0.0

        is_overdue = False
        is_due_soon = False
        reasons = []

        # Date-based evaluation
        if next_date_str:
            try:
                next_d = datetime.strptime(next_date_str, "%Y-%m-%d").date()
                if next_d < today:
                    is_overdue = True
                    days_over = (today - next_d).days
                    reasons.append(f"Overdue by {days_over} day{'s' if days_over != 1 else ''} ({next_date_str})")
                elif next_d <= threshold_date:
                    is_due_soon = True
                    days_left = (next_d - today).days
                    reasons.append(f"Due in {days_left} day{'s' if days_left != 1 else ''} ({next_date_str})")
                else:
                    reasons.append(f"Scheduled on {next_date_str}")
            except ValueError:
                pass

        # Odometer-based evaluation
        if next_odo is not None and next_odo > 0:
            odo_diff = next_odo - curr_odo
            if odo_diff <= 0:
                is_overdue = True
                reasons.append(f"Exceeded by {abs(round(odo_diff))} km (Target: {next_odo:g} km, Current: {curr_odo:g} km)")
            elif odo_diff <= 500:  # Within 500 km
                is_due_soon = True
                reasons.append(f"Due in {round(odo_diff)} km (Target: {next_odo:g} km)")
            else:
                reasons.append(f"Due at {next_odo:g} km ({round(odo_diff)} km left)")

        if is_overdue:
            status = "OVERDUE"
            priority = 1
        elif is_due_soon:
            status = "DUE SOON"
            priority = 2
        else:
            status = "UPCOMING"
            priority = 3

        if reasons:
            reminders.append({
                "service_id": row["service_id"],
                "vehicle_id": row["vehicle_id"],
                "vehicle_name": f"{row['vehicle_model']} ({row['registration_number']})",
                "registration_number": row["registration_number"],
                "category": row["category"],
                "description": row["description"],
                "next_date": next_date_str or "N/A",
                "next_odometer": f"{next_odo:g} km" if next_odo else "N/A",
                "status": status,
                "priority": priority,
                "reason": " • ".join(reasons)
            })

    reminders.sort(key=lambda r: (r["priority"], r["next_date"]))
    return reminders


# =====================================================================
# EXPENSE MANAGEMENT (Other expenses)
# =====================================================================

EXPENSE_CATEGORIES = [
    "Insurance",
    "Repairs",
    "Spare parts",
    "Accessories",
    "Parking and tolls",
    "Taxes and registration",
    "Cleaning & Detailing",
    "Other"
]

SERVICE_CATEGORIES = [
    "Oil Change",
    "General Service",
    "Brake Pads",
    "Tyre Replacement",
    "Battery",
    "Spark Plug",
    "Coolant & Fluids",
    "Suspension",
    "Air Filter",
    "Wheel Alignment",
    "Inspection",
    "Other"
]


def get_expenses(vehicle_id: Optional[int] = None,
                 category: Optional[str] = None,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 db_path: Optional[str] = None) -> List[sqlite3.Row]:
    """Fetch other vehicle expenses."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT e.expense_id, e.vehicle_id, e.expense_date, e.category,
                   e.amount, e.description, e.created_at,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   v.registration_number
            FROM expenses e
            JOIN vehicles v ON e.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        params: List[Any] = []
        if vehicle_id:
            query += " AND e.vehicle_id = ?"
            params.append(vehicle_id)
        if category and category != "All":
            query += " AND e.category = ?"
            params.append(category)
        if start_date:
            query += " AND e.expense_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND e.expense_date <= ?"
            params.append(end_date)

        query += " ORDER BY e.expense_date DESC, e.expense_id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()


def add_expense(vehicle_id: int, expense_date: str, category: str,
                amount: float, description: Optional[str] = None,
                db_path: Optional[str] = None) -> int:
    """Add a new general expense."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (vehicle_id, expense_date, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
        """, (
            vehicle_id,
            expense_date.strip(),
            category.strip(),
            round(float(amount), 2),
            description.strip() if description else None
        ))
        conn.commit()
        return cursor.lastrowid


def update_expense(expense_id: int, vehicle_id: int, expense_date: str,
                   category: str, amount: float, description: Optional[str] = None,
                   db_path: Optional[str] = None) -> bool:
    """Update an expense record."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE expenses
            SET vehicle_id = ?, expense_date = ?, category = ?, amount = ?, description = ?
            WHERE expense_id = ?
        """, (
            vehicle_id,
            expense_date.strip(),
            category.strip(),
            round(float(amount), 2),
            description.strip() if description else None,
            expense_id
        ))
        conn.commit()
        return cursor.rowcount > 0


def delete_expense(expense_id: int, db_path: Optional[str] = None) -> bool:
    """Delete an expense record."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE expense_id = ?", (expense_id,))
        conn.commit()
        return cursor.rowcount > 0


# =====================================================================
# DASHBOARD SUMMARIES & RECENT ACTIVITY
# =====================================================================

def get_dashboard_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate summary totals for the dashboard cards:
      - total_vehicles
      - total_fuel_expenses
      - total_service_costs
      - total_other_expenses
      - total_expenses = fuel + service + other (NO double counting)
    """
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()

        # Total vehicles
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0] or 0

        # Total fuel costs
        cursor.execute("SELECT COALESCE(SUM(total_cost), 0.0) FROM fuel_records")
        total_fuel = float(cursor.fetchone()[0] or 0.0)

        # Total service costs
        cursor.execute("SELECT COALESCE(SUM(cost), 0.0) FROM service_records")
        total_service = float(cursor.fetchone()[0] or 0.0)

        # Total other expenses
        cursor.execute("SELECT COALESCE(SUM(amount), 0.0) FROM expenses")
        total_other = float(cursor.fetchone()[0] or 0.0)

        # Total overall expenses
        total_expenses = round(total_fuel + total_service + total_other, 2)

        return {
            "total_vehicles": total_vehicles,
            "total_fuel_expenses": round(total_fuel, 2),
            "total_service_costs": round(total_service, 2),
            "total_other_expenses": round(total_other, 2),
            "total_expenses": total_expenses
        }


def get_recent_activity(limit: int = 8, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Combine recent fuel purchases, services, and other expenses into a unified
    chronological feed for the dashboard table.
    """
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 'Fuel' AS activity_type,
                   f.purchase_date AS activity_date,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   f.litres || ' L @ ' || f.price_per_litre || '/L (' || COALESCE(f.fuel_station, 'Fuel') || ')' AS description,
                   f.total_cost AS amount,
                   f.fuel_id AS item_id
            FROM fuel_records f
            JOIN vehicles v ON f.vehicle_id = v.vehicle_id

            UNION ALL

            SELECT 'Service' AS activity_type,
                   s.service_date AS activity_date,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   s.category || ': ' || s.description AS description,
                   s.cost AS amount,
                   s.service_id AS item_id
            FROM service_records s
            JOIN vehicles v ON s.vehicle_id = v.vehicle_id

            UNION ALL

            SELECT 'Expense' AS activity_type,
                   e.expense_date AS activity_date,
                   v.brand || ' ' || v.model || ' (' || v.registration_number || ')' AS vehicle_name,
                   e.category || ': ' || COALESCE(e.description, '') AS description,
                   e.amount AS amount,
                   e.expense_id AS item_id
            FROM expenses e
            JOIN vehicles v ON e.vehicle_id = v.vehicle_id

            ORDER BY activity_date DESC, item_id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

    return [
        {
            "type": r["activity_type"],
            "date": r["activity_date"],
            "vehicle": r["vehicle_name"],
            "description": r["description"],
            "amount": float(r["amount"])
        }
        for r in rows
    ]


# =====================================================================
# REPORTS & AGGREGATIONS
# =====================================================================

def get_report_expenses_by_vehicle(start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aggregate fuel, service, other expenses, and total per vehicle."""
    vehicles = get_all_vehicles(db_path)
    result = []

    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        for v in vehicles:
            vid = v["vehicle_id"]
            name = f"{v['brand']} {v['model']} ({v['registration_number']})"

            # Fuel sum
            q_fuel = "SELECT COALESCE(SUM(total_cost), 0.0), COALESCE(SUM(litres), 0.0) FROM fuel_records WHERE vehicle_id = ?"
            params_f: List[Any] = [vid]
            if start_date:
                q_fuel += " AND purchase_date >= ?"
                params_f.append(start_date)
            if end_date:
                q_fuel += " AND purchase_date <= ?"
                params_f.append(end_date)
            cursor.execute(q_fuel, params_f)
            fuel_sum, total_litres = cursor.fetchone()

            # Service sum
            q_serv = "SELECT COALESCE(SUM(cost), 0.0) FROM service_records WHERE vehicle_id = ?"
            params_s: List[Any] = [vid]
            if start_date:
                q_serv += " AND service_date >= ?"
                params_s.append(start_date)
            if end_date:
                q_serv += " AND service_date <= ?"
                params_s.append(end_date)
            cursor.execute(q_serv, params_s)
            serv_sum = cursor.fetchone()[0]

            # Expense sum
            q_exp = "SELECT COALESCE(SUM(amount), 0.0) FROM expenses WHERE vehicle_id = ?"
            params_e: List[Any] = [vid]
            if start_date:
                q_exp += " AND expense_date >= ?"
                params_e.append(start_date)
            if end_date:
                q_exp += " AND expense_date <= ?"
                params_e.append(end_date)
            cursor.execute(q_exp, params_e)
            exp_sum = cursor.fetchone()[0]

            total_v = round(fuel_sum + serv_sum + exp_sum, 2)
            result.append({
                "vehicle_id": vid,
                "vehicle_name": name,
                "type": v["vehicle_type"],
                "fuel_expense": round(fuel_sum, 2),
                "total_litres": round(total_litres, 2),
                "service_expense": round(serv_sum, 2),
                "other_expense": round(exp_sum, 2),
                "total_expense": total_v,
                "current_odometer": v["current_odometer"]
            })

    return result


def get_report_monthly_breakdown(vehicle_id: Optional[int] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None,
                                 db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aggregate expenses by month (YYYY-MM)."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT substr(activity_date, 1, 7) AS month_str,
                   SUM(CASE WHEN activity_type = 'Fuel' THEN amount ELSE 0 END) AS fuel_cost,
                   SUM(CASE WHEN activity_type = 'Service' THEN amount ELSE 0 END) AS service_cost,
                   SUM(CASE WHEN activity_type = 'Expense' THEN amount ELSE 0 END) AS other_cost,
                   SUM(amount) AS total_cost
            FROM (
                SELECT 'Fuel' AS activity_type, purchase_date AS activity_date, total_cost AS amount, vehicle_id
                FROM fuel_records
                UNION ALL
                SELECT 'Service' AS activity_type, service_date AS activity_date, cost AS amount, vehicle_id
                FROM service_records
                UNION ALL
                SELECT 'Expense' AS activity_type, expense_date AS activity_date, amount, vehicle_id
                FROM expenses
            )
            WHERE 1=1
        """
        params: List[Any] = []
        if vehicle_id:
            query += " AND vehicle_id = ?"
            params.append(vehicle_id)
        if start_date:
            query += " AND activity_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND activity_date <= ?"
            params.append(end_date)

        query += " GROUP BY month_str ORDER BY month_str DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [
        {
            "month": r["month_str"],
            "fuel_cost": round(r["fuel_cost"], 2),
            "service_cost": round(r["service_cost"], 2),
            "other_cost": round(r["other_cost"], 2),
            "total_cost": round(r["total_cost"], 2)
        }
        for r in rows
    ]


# =====================================================================
# SETTINGS, BACKUP & RESTORE
# =====================================================================

def get_setting(key: str, default: Optional[str] = None, db_path: Optional[str] = None) -> Optional[str]:
    """Retrieve setting value by key."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str, db_path: Optional[str] = None) -> None:
    """Store or update setting."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()


def backup_database(destination_filepath: str, db_path: Optional[str] = None) -> bool:
    """Create a live, clean backup copy of the SQLite database."""
    source_path = get_db_path(db_path)
    if not os.path.exists(source_path):
        return False

    with managed_connection(db_path) as src_conn:
        dest_conn = sqlite3.connect(destination_filepath)
        try:
            src_conn.backup(dest_conn)
            return True
        finally:
            dest_conn.close()


def restore_database(source_filepath: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Safely validate and restore database from a backup file.
    Creates an automatic recovery backup of the current database before replacing.
    """
    if not os.path.isfile(source_filepath):
        return False, "Selected backup file does not exist."

    # Validate that the source file is indeed a valid SQLite database with required tables
    try:
        test_conn = sqlite3.connect(source_filepath)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in test_cursor.fetchall()}
        test_conn.close()

        required_tables = {"vehicles", "fuel_records", "service_records", "expenses"}
        if not required_tables.issubset(tables):
            return False, "The selected file is not a valid VehicleCare backup."
    except Exception as e:
        return False, f"Failed to read backup file: {str(e)}"

    target_path = get_db_path(db_path)

    # Make safety backup of target before overwrite
    safety_backup = target_path + f".pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    if os.path.exists(target_path):
        try:
            shutil.copy2(target_path, safety_backup)
        except Exception as e:
            return False, f"Could not create safety backup of current data: {str(e)}"

    try:
        shutil.copy2(source_filepath, target_path)
        return True, "Database restored successfully."
    except Exception as e:
        # Attempt to roll back from safety backup if copy failed
        if os.path.exists(safety_backup):
            shutil.copy2(safety_backup, target_path)
        return False, f"Restore failed: {str(e)}"


# =====================================================================
# DEMO DATA / RESET (OPTIONAL WITH USER CONFIRMATION)
# =====================================================================

def clear_all_data(db_path: Optional[str] = None) -> None:
    """Clear all records from vehicles, fuel, services, and expenses tables."""
    with managed_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses")
        cursor.execute("DELETE FROM service_records")
        cursor.execute("DELETE FROM fuel_records")
        cursor.execute("DELETE FROM vehicles")
        conn.commit()


def load_demo_data(db_path: Optional[str] = None) -> None:
    """Populate clean, realistic sample records for demonstration and testing."""
    init_db(db_path)
    today = date.today()

    # Add 2 vehicles: a car and a motorcycle
    v1_id = add_vehicle(
        vehicle_type="Car",
        brand="Hyundai",
        model="Creta SX",
        registration_number="MH-12-AB-1234",
        purchase_date=(today - timedelta(days=365)).strftime("%Y-%m-%d"),
        current_odometer=14850.0,
        notes="Personal family compact SUV",
        db_path=db_path
    )

    v2_id = add_vehicle(
        vehicle_type="Bike",
        brand="Royal Enfield",
        model="Classic 350",
        registration_number="MH-12-XY-9876",
        purchase_date=(today - timedelta(days=200)).strftime("%Y-%m-%d"),
        current_odometer=4200.0,
        notes="Daily commuter bike",
        db_path=db_path
    )

    # Fuel records for Car
    add_fuel_record(
        vehicle_id=v1_id,
        purchase_date=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
        litres=38.5,
        price_per_litre=104.50,
        odometer=14200.0,
        fuel_station="HP Petrol Pump, Camp",
        notes="Full tank refill",
        db_path=db_path
    )

    add_fuel_record(
        vehicle_id=v1_id,
        purchase_date=(today - timedelta(days=12)).strftime("%Y-%m-%d"),
        litres=41.2,
        price_per_litre=104.80,
        odometer=14850.0,
        fuel_station="Indian Oil, Highway",
        notes="Highway travel refill",
        db_path=db_path
    )

    # Fuel records for Bike
    add_fuel_record(
        vehicle_id=v2_id,
        purchase_date=(today - timedelta(days=25)).strftime("%Y-%m-%d"),
        litres=10.0,
        price_per_litre=104.50,
        odometer=3850.0,
        fuel_station="Shell Station",
        notes="City commute",
        db_path=db_path
    )

    add_fuel_record(
        vehicle_id=v2_id,
        purchase_date=(today - timedelta(days=5)).strftime("%Y-%m-%d"),
        litres=9.5,
        price_per_litre=104.80,
        odometer=4200.0,
        fuel_station="Shell Station",
        notes="Regular refill",
        db_path=db_path
    )

    # Service records
    add_service_record(
        vehicle_id=v1_id,
        service_date=(today - timedelta(days=60)).strftime("%Y-%m-%d"),
        odometer=13000.0,
        category="General Service",
        description="Engine oil replacement, oil filter, air filter cleaning and general inspection",
        service_centre="Hyundai Authorized Service, Baner",
        cost=4850.0,
        next_service_date=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
        next_service_odometer=18000.0,
        notes="Next service due at 18,000 km or next month",
        db_path=db_path
    )

    add_service_record(
        vehicle_id=v2_id,
        service_date=(today - timedelta(days=45)).strftime("%Y-%m-%d"),
        odometer=3500.0,
        category="Oil Change",
        description="Semi-synthetic engine oil change and chain lubrication",
        service_centre="Royal Enfield Service Hub",
        cost=1250.0,
        next_service_date=(today + timedelta(days=4)).strftime("%Y-%m-%d"),
        next_service_odometer=5000.0,
        notes="Chain adjustment required",
        db_path=db_path
    )

    # Other Expenses
    add_expense(
        vehicle_id=v1_id,
        expense_date=(today - timedelta(days=120)).strftime("%Y-%m-%d"),
        category="Insurance",
        amount=18500.0,
        description="Annual comprehensive insurance policy renewal with zero depreciation",
        db_path=db_path
    )

    add_expense(
        vehicle_id=v1_id,
        expense_date=(today - timedelta(days=15)).strftime("%Y-%m-%d"),
        category="Parking and tolls",
        amount=380.0,
        description="Fastag highway toll charges",
        db_path=db_path
    )

    add_expense(
        vehicle_id=v2_id,
        expense_date=(today - timedelta(days=90)).strftime("%Y-%m-%d"),
        category="Accessories",
        amount=2400.0,
        description="Crash guard and mobile holder installation",
        db_path=db_path
    )
