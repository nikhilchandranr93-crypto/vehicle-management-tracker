"""
Unit tests for calculations and reminder logic in VehicleCare.
"""

import os
import gc
import unittest
import tempfile
from datetime import date, timedelta
import database


class TestCalculations(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_calc.db")
        database.init_db(self.db_path)

        # Create a test vehicle
        self.v_id = database.add_vehicle(
            vehicle_type="Car",
            brand="Toyota",
            model="Innova",
            registration_number="MH-01-AA-0001",
            purchase_date="2023-01-01",
            current_odometer=10000.0,
            db_path=self.db_path
        )

    def tearDown(self):
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_fuel_cost_calculation(self):
        """Test total fuel cost is accurately calculated (litres * price_per_litre)."""
        f_id = database.add_fuel_record(
            vehicle_id=self.v_id,
            purchase_date="2024-01-01",
            litres=40.5,
            price_per_litre=102.50,
            odometer=10000.0,
            db_path=self.db_path
        )
        records = database.get_fuel_records(vehicle_id=self.v_id, db_path=self.db_path)
        self.assertEqual(len(records), 1)
        expected_cost = round(40.5 * 102.50, 2)  # 4151.25
        self.assertEqual(records[0]["total_cost"], expected_cost)

    def test_mileage_calculation_single_record(self):
        """Test that single fuel record returns N/A (None) for mileage."""
        f_id = database.add_fuel_record(
            vehicle_id=self.v_id,
            purchase_date="2024-01-01",
            litres=30.0,
            price_per_litre=100.0,
            odometer=10000.0,
            db_path=self.db_path
        )
        mileage_dict = database.calculate_fuel_mileage_for_vehicle(self.v_id, db_path=self.db_path)
        self.assertIn(f_id, mileage_dict)
        self.assertIsNone(mileage_dict[f_id])

        overall = database.calculate_overall_vehicle_mileage(self.v_id, db_path=self.db_path)
        self.assertIsNone(overall)

    def test_mileage_consecutive_records(self):
        """Test consecutive refills calculate correct km/L."""
        # 1st refill: 10,000 km, 30L (Initial point)
        f1 = database.add_fuel_record(
            vehicle_id=self.v_id, purchase_date="2024-01-01",
            litres=30.0, price_per_litre=100.0, odometer=10000.0, db_path=self.db_path
        )
        # 2nd refill: 10,450 km, 30L -> Distance = 450 km, Mileage = 450 / 30 = 15.0 km/L
        f2 = database.add_fuel_record(
            vehicle_id=self.v_id, purchase_date="2024-01-15",
            litres=30.0, price_per_litre=100.0, odometer=10450.0, db_path=self.db_path
        )
        # 3rd refill: 11,000 km, 25L -> Distance = 550 km, Mileage = 550 / 25 = 22.0 km/L
        f3 = database.add_fuel_record(
            vehicle_id=self.v_id, purchase_date="2024-02-01",
            litres=25.0, price_per_litre=100.0, odometer=11000.0, db_path=self.db_path
        )

        mileage_dict = database.calculate_fuel_mileage_for_vehicle(self.v_id, db_path=self.db_path)
        self.assertIsNone(mileage_dict[f1])
        self.assertEqual(mileage_dict[f2], 15.0)
        self.assertEqual(mileage_dict[f3], 22.0)

        # Overall: Total distance = 450 + 550 = 1000 km, Total litres = 30 + 25 = 55L -> 1000 / 55 = 18.18 km/L
        overall = database.calculate_overall_vehicle_mileage(self.v_id, db_path=self.db_path)
        self.assertEqual(overall, 18.18)

    def test_mileage_edge_cases_backwards_odometer(self):
        """Test backwards odometer readings return None rather than negative mileage."""
        f1 = database.add_fuel_record(
            vehicle_id=self.v_id, purchase_date="2024-01-01",
            litres=30.0, price_per_litre=100.0, odometer=10000.0, db_path=self.db_path
        )
        # Backwards entry (e.g. user typo: 9500 instead of 10500)
        f2 = database.add_fuel_record(
            vehicle_id=self.v_id, purchase_date="2024-01-10",
            litres=20.0, price_per_litre=100.0, odometer=9500.0, db_path=self.db_path
        )
        mileage_dict = database.calculate_fuel_mileage_for_vehicle(self.v_id, db_path=self.db_path)
        self.assertIsNone(mileage_dict[f1])
        self.assertIsNone(mileage_dict[f2])

    def test_maintenance_reminders_status(self):
        """Test status determination for overdue, due soon, and upcoming maintenance."""
        today = date.today()

        # Service 1: Overdue by date (due 10 days ago)
        database.add_service_record(
            vehicle_id=self.v_id,
            service_date="2023-12-01",
            odometer=8000.0,
            category="Brake Pads",
            description="Replace front brake pads",
            cost=1500.0,
            next_service_date=(today - timedelta(days=10)).strftime("%Y-%m-%d"),
            db_path=self.db_path
        )

        # Service 2: Due soon by date (due in 4 days with default 7-day lead)
        database.add_service_record(
            vehicle_id=self.v_id,
            service_date="2024-01-01",
            odometer=9000.0,
            category="Oil Change",
            description="Engine oil",
            cost=2000.0,
            next_service_date=(today + timedelta(days=4)).strftime("%Y-%m-%d"),
            db_path=self.db_path
        )

        # Service 3: Upcoming (due in 30 days)
        database.add_service_record(
            vehicle_id=self.v_id,
            service_date="2024-01-15",
            odometer=9500.0,
            category="Tyre Replacement",
            description="All four tyres",
            cost=12000.0,
            next_service_date=(today + timedelta(days=30)).strftime("%Y-%m-%d"),
            db_path=self.db_path
        )

        # Service 4: Overdue by odometer (current odometer is 10000, next service at 9800)
        database.add_service_record(
            vehicle_id=self.v_id,
            service_date="2023-11-01",
            odometer=7000.0,
            category="Spark Plug",
            description="Spark plugs",
            cost=600.0,
            next_service_odometer=9800.0,
            db_path=self.db_path
        )

        reminders = database.get_upcoming_reminders(lead_days=7, db_path=self.db_path)
        statuses = {r["category"]: r["status"] for r in reminders}

        self.assertEqual(statuses.get("Brake Pads"), "OVERDUE")
        self.assertEqual(statuses.get("Spark Plug"), "OVERDUE")
        self.assertEqual(statuses.get("Oil Change"), "DUE SOON")
        self.assertEqual(statuses.get("Tyre Replacement"), "UPCOMING")


if __name__ == "__main__":
    unittest.main()
