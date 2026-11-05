"""
Unit tests for database.py in VehicleCare
Uses a temporary in-memory or isolated SQLite file to avoid touching user data.
"""

import os
import gc
import unittest
import tempfile
import sqlite3
from datetime import date, timedelta
import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_vehiclecare.db")
        database.init_db(self.db_path)

    def tearDown(self):
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_schema_initialization(self):
        """Test tables exist and settings are populated."""
        with database.managed_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("vehicles", tables)
            self.assertIn("fuel_records", tables)
            self.assertIn("service_records", tables)
            self.assertIn("expenses", tables)
            self.assertIn("settings", tables)

        currency = database.get_setting("currency", db_path=self.db_path)
        self.assertEqual(currency, "₹")

    def test_vehicle_crud(self):
        """Test adding, listing, updating, and deleting a vehicle."""
        v_id = database.add_vehicle(
            vehicle_type="Car",
            brand="Honda",
            model="City",
            registration_number="KA-01-AB-1234",
            purchase_date="2023-01-15",
            current_odometer=15000.0,
            notes="Initial test",
            db_path=self.db_path
        )
        self.assertIsInstance(v_id, int)

        # Retrieve
        v = database.get_vehicle_by_id(v_id, db_path=self.db_path)
        self.assertIsNotNone(v)
        self.assertEqual(v["brand"], "Honda")
        self.assertEqual(v["model"], "City")
        self.assertEqual(v["registration_number"], "KA-01-AB-1234")
        self.assertEqual(v["current_odometer"], 15000.0)

        # Update
        updated = database.update_vehicle(
            vehicle_id=v_id,
            vehicle_type="Car",
            brand="Honda",
            model="City ZX",
            registration_number="KA-01-AB-1234",
            purchase_date="2023-01-15",
            current_odometer=16500.0,
            notes="Updated note",
            db_path=self.db_path
        )
        self.assertTrue(updated)
        v_updated = database.get_vehicle_by_id(v_id, db_path=self.db_path)
        self.assertEqual(v_updated["model"], "City ZX")
        self.assertEqual(v_updated["current_odometer"], 16500.0)

        # Delete
        deleted = database.delete_vehicle(v_id, db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(database.get_vehicle_by_id(v_id, db_path=self.db_path))

    def test_duplicate_registration_validation(self):
        """Test that duplicate registration numbers (case-insensitive) are rejected."""
        database.add_vehicle(
            vehicle_type="Bike",
            brand="Yamaha",
            model="R15",
            registration_number="DL-03-CC-9999",
            purchase_date="2022-05-10",
            current_odometer=5000.0,
            db_path=self.db_path
        )

        # Duplicate check helper
        existing = database.get_vehicle_by_registration("dl-03-cc-9999", db_path=self.db_path)
        self.assertIsNotNone(existing)

        # Attempting insert should raise sqlite3.IntegrityError
        with self.assertRaises(sqlite3.IntegrityError):
            database.add_vehicle(
                vehicle_type="Bike",
                brand="Yamaha",
                model="MT-15",
                registration_number="DL-03-CC-9999",
                purchase_date="2023-01-01",
                current_odometer=2000.0,
                db_path=self.db_path
            )

    def test_cascading_delete_and_dependent_counts(self):
        """Test foreign key cascading delete on vehicle deletion."""
        v_id = database.add_vehicle(
            vehicle_type="Car",
            brand="Maruti",
            model="Swift",
            registration_number="MH-14-GH-5555",
            purchase_date="2021-08-20",
            current_odometer=25000.0,
            db_path=self.db_path
        )

        # Add fuel, service, and expense
        f_id = database.add_fuel_record(
            vehicle_id=v_id,
            purchase_date="2024-01-10",
            litres=30.0,
            price_per_litre=100.0,
            odometer=25500.0,
            db_path=self.db_path
        )
        s_id = database.add_service_record(
            vehicle_id=v_id,
            service_date="2024-01-15",
            odometer=25600.0,
            category="Oil Change",
            description="Routine oil change",
            cost=2500.0,
            db_path=self.db_path
        )
        e_id = database.add_expense(
            vehicle_id=v_id,
            expense_date="2024-01-20",
            category="Insurance",
            amount=8000.0,
            db_path=self.db_path
        )

        counts = database.get_vehicle_dependent_counts(v_id, db_path=self.db_path)
        self.assertEqual(counts["fuel"], 1)
        self.assertEqual(counts["service"], 1)
        self.assertEqual(counts["expenses"], 1)
        self.assertEqual(counts["total"], 3)

        # Delete vehicle
        database.delete_vehicle(v_id, db_path=self.db_path)

        # Ensure cascade deleted all child records
        with database.managed_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM fuel_records WHERE vehicle_id = ?", (v_id,))
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM service_records WHERE vehicle_id = ?", (v_id,))
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM expenses WHERE vehicle_id = ?", (v_id,))
            self.assertEqual(c.fetchone()[0], 0)

    def test_dashboard_summary_no_double_counting(self):
        """Verify dashboard totals correctly calculate total expenses = fuel + service + other."""
        v_id = database.add_vehicle(
            vehicle_type="Car",
            brand="Tata",
            model="Nexon",
            registration_number="MH-02-EZ-7777",
            purchase_date="2022-01-01",
            current_odometer=10000.0,
            db_path=self.db_path
        )

        # Fuel = 3000
        database.add_fuel_record(
            vehicle_id=v_id, purchase_date="2024-02-01",
            litres=30.0, price_per_litre=100.0, odometer=10500.0, db_path=self.db_path
        )
        # Service = 4500
        database.add_service_record(
            vehicle_id=v_id, service_date="2024-02-10", odometer=10600.0,
            category="General Service", description="Servicing", cost=4500.0, db_path=self.db_path
        )
        # Expense = 1200
        database.add_expense(
            vehicle_id=v_id, expense_date="2024-02-15",
            category="Accessories", amount=1200.0, description="Seat covers", db_path=self.db_path
        )

        summary = database.get_dashboard_summary(db_path=self.db_path)
        self.assertEqual(summary["total_vehicles"], 1)
        self.assertEqual(summary["total_fuel_expenses"], 3000.0)
        self.assertEqual(summary["total_service_costs"], 4500.0)
        self.assertEqual(summary["total_other_expenses"], 1200.0)
        # Total = 3000 + 4500 + 1200 = 8700
        self.assertEqual(summary["total_expenses"], 8700.0)

    def test_backup_and_restore(self):
        """Test database backup and safe restore."""
        v_id = database.add_vehicle(
            vehicle_type="Bike", brand="KTM", model="Duke 250",
            registration_number="MH-12-KT-1111", purchase_date="2023-01-01",
            current_odometer=3000.0, db_path=self.db_path
        )

        backup_file = os.path.join(self.temp_dir.name, "backup.db")
        backup_ok = database.backup_database(backup_file, db_path=self.db_path)
        self.assertTrue(backup_ok)
        self.assertTrue(os.path.exists(backup_file))

        # Now clear all data
        database.clear_all_data(db_path=self.db_path)
        self.assertEqual(len(database.get_all_vehicles(db_path=self.db_path)), 0)

        # Restore from backup
        restore_ok, msg = database.restore_database(backup_file, db_path=self.db_path)
        self.assertTrue(restore_ok)

        # Vehicle should be back
        restored_v = database.get_vehicle_by_id(v_id, db_path=self.db_path)
        self.assertIsNotNone(restored_v)
        self.assertEqual(restored_v["model"], "Duke 250")


if __name__ == "__main__":
    unittest.main()
