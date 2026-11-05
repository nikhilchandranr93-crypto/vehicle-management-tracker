# VehicleCare — Vehicle Management Tracker

A desktop vehicle management application built with **Python 3**, **Tkinter / ttk**, and **SQLite**.

VehicleCare enables individual vehicle owners to track multiple bikes and cars, monitor fuel expenses and refill mileage (km/L), schedule maintenance reminders, track ownership costs (insurance, taxes, accessories, repairs), and export reports to CSV.

---

## Key Features

1. **Dashboard Overview**
   - 4 summary cards: Total Vehicles, Total Fuel Expenses, Total Service Costs, and Total Expenses.
   - Live activity feed showing recent fuel purchases, services, and expenses.
   - Maintenance alert panel highlighting overdue and upcoming vehicle services.
   - One-click quick actions to register vehicles, log fuel, add services, and record expenses.

2. **Vehicle Registration**
   - Support for Cars, Bikes, Scooters, and Commercial vehicles.
   - Enforces unique registration numbers (case-insensitive) to prevent duplicates.
   - Tracks current odometer readings, purchase dates, and notes.
   - Cascading delete protection: warns you of linked fuel and service records before deletion.

3. **Fuel Tracker & Mileage (km/L)**
   - Log litres, price per litre, total cost (automatically computed), odometer, and fuel stations.
   - Accurate consecutive-refill mileage calculation: `(Odometer_Current - Odometer_Previous) / Litres`.
   - Rejects or flags backwards odometer readings and handles initial refills cleanly.
   - Filter records by vehicle and date range.

4. **Service History & Reminders**
   - Categorized maintenance logs (Oil Change, Brake Pads, General Service, Battery, Tyres, etc.).
   - Configure next service due dates and target odometer readings.
   - Automated alerts for overdue services and services due within a configurable lead time (default: 7 days).

5. **General Expenses (No Double-Counting)**
   - Track vehicle-related costs not in fuel or service: Insurance, Taxes, Tolls, Parking, Accessories, etc.
   - Explicit formula: `Total Expenses = Fuel Expenses + Service Costs + Other Expenses`.

6. **Reports & CSV Export**
   - Filter by date range and view:
     - Expenses by Vehicle (Fuel, Litres, Service, Other, Total, Odometer)
     - Monthly Expense Breakdown (Month-by-month financial summary)
     - Comprehensive Transaction Log
   - One-click export to CSV using Python's standard `csv` module.

7. **Settings, Backup & Restore**
   - Customizable currency display (defaults to ₹ INR; supports $, €, £, C$, A$, ¥, AED).
   - Adjustable reminder lead-time (3, 7, 14, 30 days).
   - Live SQLite database backup and safe restore with automatic pre-restore backup.
   - Optional demo data loader for demonstration and evaluation.

---

## Project Structure

```
VehicleCare/
├── main.py               # Main application entry point, sidebar navigation, window routing
├── database.py           # SQLite database layer, schema, CRUD operations, calculations
├── ui_common.py          # Design system: colors, typography, StatCard, TableView, buttons
├── dashboard.py          # Dashboard view with summary cards, activity feed, alerts
├── vehicles.py           # Vehicle management module (table, search, add/edit dialogs)
├── fuel.py               # Fuel tracking and mileage calculation module
├── service.py            # Service history and maintenance reminders module
├── expenses.py           # Other expenses module (insurance, taxes, tolls, accessories)
├── reports.py            # Financial reports and CSV export module
├── settings.py           # Preferences, database backup/restore, demo data
├── requirements.txt      # Pure standard library specification
├── README.md             # Complete documentation
├── data/
│   └── vehiclecare.db    # SQLite database (auto-created on first run)
└── tests/
    ├── test_database.py       # Unit tests for schema, CRUD, cascading deletes
    ├── test_calculations.py   # Unit tests for fuel costs, mileage, reminders
    └── test_ui_integration.py # Headless GUI integration and page navigation tests
```

---

## Requirements & Installation

- **Python Version**: Python 3.8 or higher (tested on Python 3.10, 3.11, 3.12, 3.15).
- **Dependencies**: Pure Python Standard Library (`tkinter`, `sqlite3`, `csv`, `shutil`, `datetime`, `unittest`). No third-party packages required.

### Launching the Application

On Windows:
```bash
python main.py
```
Or using the Python launcher:
```bash
py main.py
```

---

## Running the Automated Test Suite

VehicleCare includes unit tests and UI integration tests. Tests run in isolated temporary databases without modifying user data.

To execute all tests:
```bash
python -m unittest discover -s tests -v
```

Expected output:
```
test_fuel_cost_calculation ... ok
test_maintenance_reminders_status ... ok
test_mileage_calculation_single_record ... ok
test_mileage_consecutive_records ... ok
test_mileage_edge_cases_backwards_odometer ... ok
test_backup_and_restore ... ok
test_cascading_delete_and_dependent_counts ... ok
test_dashboard_summary_no_double_counting ... ok
test_duplicate_registration_validation ... ok
test_schema_initialization ... ok
test_vehicle_crud ... ok
test_demo_data_population_and_ui_update ... ok
test_pages_navigation ... ok

Ran 13 tests in 1.5s
OK
```

---

## Database Management & Backup

- **Database Location**: The database is stored at `data/vehiclecare.db` relative to the application directory.
- **Backing Up**: Go to **Settings** → click **💾 Backup Database** → choose your destination `.db` file.
- **Restoring**: Go to **Settings** → click **🔄 Restore Database** → select a valid backup `.db` file. VehicleCare verifies table integrity and creates a pre-restore safety copy before restoring.
- **Demo Data**: Go to **Settings** → click **Load Sample Demo Data** to populate realistic sample vehicles, fuel fill-ups, and service logs for testing.

---

## Design System & Theme

- **Window Dimensions**: 1100 × 700 px (minimum 850 × 580 px).
- **Main Background**: `#F3F5F9`
- **Sidebar Background**: `#172238` (Deep Navy)
- **Active Accent**: `#3478F6` (Electric Blue)
- **Card Background**: `#FFFFFF`
- **Text Main**: `#202B3C`
- **Text Secondary**: `#7B8798`
- **Border**: `#E0E5ED`
- **Typography**: Segoe UI (with clean system fallbacks)
