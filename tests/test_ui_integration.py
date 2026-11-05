"""
test_ui_integration.py - Headless/Off-screen GUI integration test for VehicleCareApp.
Verifies window initialization, page switching, demo data loading,
and UI widget state integrity.
"""

import os
import gc
import unittest
import tempfile
import database
from main import VehicleCareApp


class TestUIIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "ui_test.db")

        # Point database to test path
        self._orig_db_path = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = self.test_db_path
        database.init_db(self.test_db_path)

        # Create Tk app without mapping window to screen
        self.app = VehicleCareApp()
        self.app.withdraw()  # Hide window during automated test
        self.app.update()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass

        database.DEFAULT_DB_PATH = self._orig_db_path
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_pages_navigation(self):
        """Test switching across all sidebar pages without errors."""
        pages = [
            "Dashboard",
            "My Vehicles",
            "Fuel Tracker",
            "Service History",
            "Expenses",
            "Reports",
            "Settings"
        ]
        for p in pages:
            self.app.show_page(p)
            self.app.update()
            self.assertEqual(self.app._current_page, p)
            self.assertEqual(self.app.pages[p].winfo_manager(), "pack")

    def test_demo_data_population_and_ui_update(self):
        """Test loading demo data and verifying UI summary updates."""
        database.load_demo_data(self.test_db_path)
        self.app._on_data_modified()
        self.app.update()

        # Check dashboard metrics
        dash = self.app.pages["Dashboard"]
        dash.refresh_data()
        self.app.update()

        self.assertEqual(dash.card_vehicles.lbl_value.cget("text"), "2")

        # Check Vehicles page
        veh_view = self.app.pages["My Vehicles"]
        veh_view.refresh_data()
        self.app.update()
        self.assertEqual(len(veh_view._vehicles_cache), 2)

        # Check Fuel page
        fuel_view = self.app.pages["Fuel Tracker"]
        fuel_view.refresh_data()
        self.app.update()
        fuel_records = database.get_fuel_records(db_path=self.test_db_path)
        self.assertEqual(len(fuel_records), 4)

        # Check Reports page
        rep_view = self.app.pages["Reports"]
        rep_view.generate_report()
        self.app.update()
        self.assertGreater(len(rep_view._current_report_data), 0)


if __name__ == "__main__":
    unittest.main()
