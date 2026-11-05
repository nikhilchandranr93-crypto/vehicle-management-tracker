"""
fuel.py - Fuel Tracker and Mileage Calculation module for VehicleCare.
Allows recording fuel purchases, calculating consecutive refill mileage,
filtering historical records, and viewing fuel expense statistics.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from typing import Optional, Callable, Dict, Any, List
import database
from ui_common import (
    COLORS, FONTS, StyledButton, CardContainer, TableView,
    FormDialog, format_currency, format_odometer
)


class FuelFormDialog(FormDialog):
    """Modal dialog for adding or editing a fuel purchase record."""
    def __init__(self, parent, fuel_record: Optional[dict] = None,
                 default_vehicle_id: Optional[int] = None,
                 on_success: Optional[Callable] = None):
        title = "Edit Fuel Record" if fuel_record else "Record Fuel Purchase"
        super().__init__(parent, title=title, width=540, height=540)
        self.fuel_record = fuel_record
        self.default_vehicle_id = default_vehicle_id
        self.on_success = on_success

        self._vehicles = [dict(v) for v in database.get_all_vehicles()]
        self._build_form()

    def _build_form(self):
        body = self.body_card

        # Vehicle selection
        tk.Label(body, text="Select Vehicle *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.vehicle_options = {
            f"{v['brand']} {v['model']} ({v['registration_number']})": v["vehicle_id"]
            for v in self._vehicles
        }
        self.cmb_vehicle = ttk.Combobox(body, values=list(self.vehicle_options.keys()), state="readonly", font=FONTS["body"])
        self.cmb_vehicle.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Select initial vehicle
        if self.fuel_record:
            for name, vid in self.vehicle_options.items():
                if vid == self.fuel_record["vehicle_id"]:
                    self.cmb_vehicle.set(name)
                    break
        elif self.default_vehicle_id:
            for name, vid in self.vehicle_options.items():
                if vid == self.default_vehicle_id:
                    self.cmb_vehicle.set(name)
                    break
        elif self.vehicle_options:
            self.cmb_vehicle.current(0)

        # Purchase Date & Odometer
        tk.Label(body, text="Purchase Date * (YYYY-MM-DD)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.ent_date = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_date.grid(row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 10), ipady=4)
        if self.fuel_record:
            self.ent_date.insert(0, self.fuel_record["purchase_date"])
        else:
            self.ent_date.insert(0, date.today().strftime("%Y-%m-%d"))

        tk.Label(body, text="Odometer Reading (km) *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=2, column=1, sticky="w", pady=(0, 2))
        self.ent_odo = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_odo.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 10), ipady=4)
        if self.fuel_record:
            self.ent_odo.insert(0, str(self.fuel_record["odometer"]))

        # Fuel Quantity & Price per Litre
        currency = database.get_setting("currency", "₹")
        tk.Label(body, text="Quantity (Litres) *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.ent_litres = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_litres.grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(0, 10), ipady=4)
        self.ent_litres.bind("<KeyRelease>", lambda e: self._recalculate_total())
        if self.fuel_record:
            self.ent_litres.insert(0, str(self.fuel_record["litres"]))

        tk.Label(body, text=f"Price per Litre ({currency}) *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=4, column=1, sticky="w", pady=(0, 2))
        self.ent_price = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_price.grid(row=5, column=1, sticky="ew", padx=(6, 0), pady=(0, 10), ipady=4)
        self.ent_price.bind("<KeyRelease>", lambda e: self._recalculate_total())
        if self.fuel_record:
            self.ent_price.insert(0, str(self.fuel_record["price_per_litre"]))

        # Auto-calculated Total Cost Display
        cost_box = tk.Frame(body, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1, padx=12, pady=8)
        cost_box.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tk.Label(cost_box, text="Total Fuel Cost:", font=FONTS["body_bold"], fg=COLORS["primary"], bg="#EFF6FF").pack(side="left")
        self.lbl_calculated_total = tk.Label(cost_box, text=f"{currency} 0.00", font=FONTS["header"], fg=COLORS["primary"], bg="#EFF6FF")
        self.lbl_calculated_total.pack(side="right")
        self._recalculate_total()

        # Fuel Station & Notes
        tk.Label(body, text="Fuel Station / Brand (Optional)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.ent_station = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_station.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=4)
        if self.fuel_record and self.fuel_record.get("fuel_station"):
            self.ent_station.insert(0, self.fuel_record["fuel_station"])

        tk.Label(body, text="Optional Notes", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.ent_notes = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_notes.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(0, 5), ipady=4)
        if self.fuel_record and self.fuel_record.get("notes"):
            self.ent_notes.insert(0, self.fuel_record["notes"])

        body.grid_columnconfigure((0, 1), weight=1)

    def _recalculate_total(self):
        currency = database.get_setting("currency", "₹")
        try:
            litres = float(self.ent_litres.get().strip())
            price = float(self.ent_price.get().strip())
            if litres > 0 and price > 0:
                tot = litres * price
                self.lbl_calculated_total.config(text=format_currency(tot, currency))
                return
        except ValueError:
            pass
        self.lbl_calculated_total.config(text=format_currency(0.0, currency))

    def on_submit(self):
        veh_name = self.cmb_vehicle.get()
        if not veh_name or veh_name not in self.vehicle_options:
            messagebox.showerror("Validation Error", "Please select a registered vehicle.", parent=self)
            return

        vehicle_id = self.vehicle_options[veh_name]
        p_date = self.ent_date.get().strip()
        odo_str = self.ent_odo.get().strip()
        litres_str = self.ent_litres.get().strip()
        price_str = self.ent_price.get().strip()
        station = self.ent_station.get().strip()
        notes = self.ent_notes.get().strip()

        # Date validation
        try:
            datetime.strptime(p_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Date must follow YYYY-MM-DD format (e.g. 2024-03-25).", parent=self)
            return

        # Numeric validations
        try:
            odometer = float(odo_str)
            if odometer < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Odometer must be a non-negative number.", parent=self)
            return

        try:
            litres = float(litres_str)
            if litres <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Fuel quantity must be greater than 0.", parent=self)
            return

        try:
            price = float(price_str)
            if price <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Price per litre must be greater than 0.", parent=self)
            return

        try:
            if self.fuel_record:
                database.update_fuel_record(
                    fuel_id=self.fuel_record["fuel_id"],
                    vehicle_id=vehicle_id,
                    purchase_date=p_date,
                    litres=litres,
                    price_per_litre=price,
                    odometer=odometer,
                    fuel_station=station if station else None,
                    notes=notes if notes else None
                )
            else:
                database.add_fuel_record(
                    vehicle_id=vehicle_id,
                    purchase_date=p_date,
                    litres=litres,
                    price_per_litre=price,
                    odometer=odometer,
                    fuel_station=station if station else None,
                    notes=notes if notes else None
                )

            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save fuel purchase: {str(e)}", parent=self)


class FuelView(tk.Frame):
    def __init__(self, parent, on_data_changed: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_main"], **kwargs)
        self.on_data_changed = on_data_changed

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header & Actions
        top_frame = tk.Frame(self, bg=COLORS["bg_main"])
        top_frame.pack(fill="x", padx=24, pady=(20, 16))

        title_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="Fuel Tracker & Mileage",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Monitor fuel purchases, mileage (km/L) between refills, and fuel costs",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        btn_box.pack(side="right")

        StyledButton(
            btn_box,
            text="+ Record Fuel",
            variant="primary",
            command=self.open_add_dialog
        ).pack(side="left", padx=4)

        StyledButton(
            btn_box,
            text="Edit Selected",
            variant="outline",
            command=self.open_edit_dialog
        ).pack(side="left", padx=4)

        StyledButton(
            btn_box,
            text="Delete",
            variant="danger",
            command=self.delete_selected
        ).pack(side="left", padx=4)

        # 2. Summary Mini-Cards Banner
        stats_frame = tk.Frame(self, bg=COLORS["bg_main"])
        stats_frame.pack(fill="x", padx=24, pady=(0, 16))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="fuel_stats")

        self.stat_total_spent = self._create_mini_stat(stats_frame, 0, "TOTAL FUEL EXPENSE", "₹ 0.00")
        self.stat_total_litres = self._create_mini_stat(stats_frame, 1, "TOTAL FUEL PURCHASED", "0.0 L")
        self.stat_avg_price = self._create_mini_stat(stats_frame, 2, "AVG. PRICE / LITRE", "₹ 0.00 / L")
        self.stat_avg_mileage = self._create_mini_stat(stats_frame, 3, "OVERALL MILEAGE", "N/A", subtitle="Calculated between fill-ups")

        # 3. Filter Bar
        filter_card = CardContainer(self, padx=16, pady=10)
        filter_card.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(filter_card, text="Filter by Vehicle:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 6))

        self.cmb_filter_veh = ttk.Combobox(filter_card, state="readonly", font=FONTS["body"], width=28)
        self.cmb_filter_veh.pack(side="left", padx=(0, 12))
        self.cmb_filter_veh.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(filter_card, text="Date Range:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 6))

        self.ent_start_date = tk.Entry(filter_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=11)
        self.ent_start_date.pack(side="left", padx=(0, 4), ipady=2)

        tk.Label(filter_card, text="to", font=FONTS["body"], fg=COLORS["text_muted"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))

        self.ent_end_date = tk.Entry(filter_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=11)
        self.ent_end_date.pack(side="left", padx=(0, 8), ipady=2)

        StyledButton(filter_card, text="Apply Filter", variant="primary", command=self.apply_filters).pack(side="left", padx=4)
        StyledButton(filter_card, text="Reset", variant="secondary", command=self.reset_filters).pack(side="left", padx=4)

        self.lbl_record_count = tk.Label(filter_card, text="0 records", font=FONTS["small"], fg=COLORS["text_muted"], bg=COLORS["card_bg"])
        self.lbl_record_count.pack(side="right")

        # 4. Main Records Table
        table_card = CardContainer(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Mileage Note
        note_frame = tk.Frame(table_card, bg="#F0F9FF", highlightbackground="#BAE6FD", highlightthickness=1, padx=10, pady=6)
        note_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            note_frame,
            text="ℹ Mileage Method: Mileage (km/L) is estimated using consecutive odometer readings and refill quantity: (Odometer_Current - Odometer_Previous) / Litres. The first refill or non-consecutive records will display N/A.",
            font=FONTS["small"],
            fg="#0369A1",
            bg="#F0F9FF",
            anchor="w"
        ).pack(fill="x")

        columns = [
            {"id": "id", "name": "ID", "width": 45, "anchor": "center"},
            {"id": "date", "name": "Date", "width": 95, "anchor": "center"},
            {"id": "vehicle", "name": "Vehicle", "width": 170, "anchor": "w"},
            {"id": "litres", "name": "Quantity", "width": 80, "anchor": "e"},
            {"id": "price", "name": "Price / L", "width": 90, "anchor": "e"},
            {"id": "total", "name": "Total Cost", "width": 105, "anchor": "e"},
            {"id": "odometer", "name": "Odometer", "width": 110, "anchor": "e"},
            {"id": "mileage", "name": "Mileage (km/L)", "width": 110, "anchor": "center"},
            {"id": "station", "name": "Fuel Station", "width": 130, "anchor": "w"},
            {"id": "notes", "name": "Notes", "width": 140, "anchor": "w"}
        ]
        self.table = TableView(table_card, columns=columns)
        self.table.pack(fill="both", expand=True)

        self.empty_lbl = tk.Label(
            table_card,
            text="No fuel purchases recorded.\nClick '+ Record Fuel' to add your fuel refill.",
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            pady=40
        )

    def _create_mini_stat(self, parent, col, title, value, subtitle=""):
        f = tk.Frame(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"], highlightthickness=1, padx=14, pady=10)
        f.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(f, text=title, font=FONTS["card_title"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"], anchor="w").pack(fill="x")
        val_lbl = tk.Label(f, text=value, font=FONTS["header"], fg=COLORS["text_main"], bg=COLORS["card_bg"], anchor="w")
        val_lbl.pack(fill="x", pady=(2, 0))
        if subtitle:
            tk.Label(f, text=subtitle, font=FONTS["small"], fg=COLORS["text_muted"], bg=COLORS["card_bg"], anchor="w").pack(fill="x")
        return val_lbl

    def refresh_data(self):
        """Update vehicle dropdown and reload table records."""
        vehicles = database.get_all_vehicles()
        self.veh_filter_map = {"All Vehicles": None}
        for v in vehicles:
            name = f"{v['brand']} {v['model']} ({v['registration_number']})"
            self.veh_filter_map[name] = v["vehicle_id"]

        current_val = self.cmb_filter_veh.get()
        self.cmb_filter_veh["values"] = list(self.veh_filter_map.keys())

        if current_val in self.veh_filter_map:
            self.cmb_filter_veh.set(current_val)
        else:
            self.cmb_filter_veh.current(0)

        self.apply_filters()

    def apply_filters(self):
        currency = database.get_setting("currency", "₹")
        selected_veh_str = self.cmb_filter_veh.get()
        veh_id = self.veh_filter_map.get(selected_veh_str)

        start_date = self.ent_start_date.get().strip() or None
        end_date = self.ent_end_date.get().strip() or None

        # Fetch records
        records = database.get_fuel_records(vehicle_id=veh_id, start_date=start_date, end_date=end_date)

        # Precompute mileage per vehicle
        vehicle_ids_in_view = set(r["vehicle_id"] for r in records)
        mileage_cache: Dict[int, Dict[int, Optional[float]]] = {}
        for vid in vehicle_ids_in_view:
            mileage_cache[vid] = database.calculate_fuel_mileage_for_vehicle(vid)

        # Update mini stats
        total_spent = sum(r["total_cost"] for r in records)
        total_litres = sum(r["litres"] for r in records)
        avg_price = (total_spent / total_litres) if total_litres > 0 else 0.0

        self.stat_total_spent.config(text=format_currency(total_spent, currency))
        self.stat_total_litres.config(text=f"{total_litres:,.1f} L")
        self.stat_avg_price.config(text=f"{format_currency(avg_price, currency)} / L")

        # Overall mileage for filtered vehicle if single vehicle selected
        if veh_id:
            overall_mileage = database.calculate_overall_vehicle_mileage(veh_id)
            if overall_mileage is not None:
                self.stat_avg_mileage.config(text=f"{overall_mileage:.1f} km/L")
            else:
                self.stat_avg_mileage.config(text="N/A (need ≥ 2 refills)")
        else:
            self.stat_avg_mileage.config(text="Select 1 vehicle")

        # Populate table
        if records:
            self.empty_lbl.pack_forget()
            self.table.pack(fill="both", expand=True)

            rows = []
            ids = []
            for r in records:
                ids.append(r["fuel_id"])
                fid = r["fuel_id"]
                vid = r["vehicle_id"]

                # Get calculated mileage
                mil_val = mileage_cache.get(vid, {}).get(fid)
                if mil_val is not None:
                    mil_str = f"{mil_val:.1f} km/L"
                else:
                    mil_str = "— (N/A)"

                rows.append([
                    r["fuel_id"],
                    r["purchase_date"],
                    r["vehicle_name"],
                    f"{r['litres']:.2f} L",
                    format_currency(r["price_per_litre"], currency),
                    format_currency(r["total_cost"], currency),
                    format_odometer(r["odometer"]),
                    mil_str,
                    r["fuel_station"] or "—",
                    r["notes"] or ""
                ])
            self.table.insert_rows(rows, ids=ids)
            self.lbl_record_count.config(text=f"{len(records)} record{'s' if len(records) != 1 else ''}")
        else:
            self.table.clear()
            self.table.pack_forget()
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_record_count.config(text="0 records")

    def reset_filters(self):
        self.cmb_filter_veh.current(0)
        self.ent_start_date.delete(0, "end")
        self.ent_end_date.delete(0, "end")
        self.apply_filters()

    def open_add_dialog(self):
        vehicles = database.get_all_vehicles()
        if not vehicles:
            messagebox.showwarning("No Vehicles Found", "Please register at least one vehicle before recording fuel purchases.", parent=self)
            return

        selected_veh_str = self.cmb_filter_veh.get()
        default_vid = self.veh_filter_map.get(selected_veh_str)
        FuelFormDialog(self, default_vehicle_id=default_vid, on_success=self._on_record_saved)

    def open_edit_dialog(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Record", "Please select a fuel purchase record from the table to edit.", parent=self)
            return

        # Fetch record by querying
        records = database.get_fuel_records()
        target = next((r for r in records if r["fuel_id"] == int(sel_id)), None)
        if target:
            FuelFormDialog(self, fuel_record=dict(target), on_success=self._on_record_saved)

    def delete_selected(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Record", "Please select a fuel record to delete.", parent=self)
            return

        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this fuel purchase record?", icon="warning", parent=self)
        if confirm:
            database.delete_fuel_record(int(sel_id))
            messagebox.showinfo("Deleted", "Fuel purchase record deleted.", parent=self)
            self._on_record_saved()

    def _on_record_saved(self):
        self.apply_filters()
        if self.on_data_changed:
            self.on_data_changed()
