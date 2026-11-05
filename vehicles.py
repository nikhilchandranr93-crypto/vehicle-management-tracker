"""
vehicles.py - Vehicle Management Module for VehicleCare.
Allows viewing, adding, editing, searching, and deleting vehicles
with full field validation and cascading delete safety checks.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, Callable
import database
from ui_common import (
    COLORS, FONTS, StyledButton, CardContainer, TableView,
    FormDialog, format_odometer
)

VEHICLE_TYPES = ["Car", "Bike", "Scooter", "Commercial Truck", "SUV", "Other"]


class VehicleFormDialog(FormDialog):
    """Modal dialog for creating or modifying a vehicle."""
    def __init__(self, parent, vehicle: Optional[dict] = None, on_success: Optional[Callable] = None):
        title = "Edit Vehicle" if vehicle else "Register New Vehicle"
        super().__init__(parent, title=title, width=540, height=520)
        self.vehicle = vehicle
        self.on_success = on_success

        self._build_form()

    def _build_form(self):
        body = self.body_card

        # Vehicle Type
        tk.Label(body, text="Vehicle Type *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.cmb_type = ttk.Combobox(body, values=VEHICLE_TYPES, state="readonly", font=FONTS["body"])
        self.cmb_type.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.cmb_type.set(self.vehicle["vehicle_type"] if self.vehicle else "Car")

        # Brand
        tk.Label(body, text="Brand / Make * (e.g. Honda, Hyundai, Royal Enfield)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.ent_brand = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_brand.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=4)
        if self.vehicle:
            self.ent_brand.insert(0, self.vehicle["brand"])

        # Model
        tk.Label(body, text="Model Name / Variant * (e.g. City ZX, Creta SX)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.ent_model = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_model.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=4)
        if self.vehicle:
            self.ent_model.insert(0, self.vehicle["model"])

        # Registration Number
        tk.Label(body, text="Registration / License Plate * (Unique)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.ent_reg = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_reg.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=4)
        if self.vehicle:
            self.ent_reg.insert(0, self.vehicle["registration_number"])

        # Purchase Date & Odometer side by side
        tk.Label(body, text="Purchase Date (YYYY-MM-DD)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=8, column=0, sticky="w", pady=(0, 2))
        self.ent_date = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_date.grid(row=9, column=0, sticky="ew", padx=(0, 6), pady=(0, 10), ipady=4)
        if self.vehicle and self.vehicle.get("purchase_date"):
            self.ent_date.insert(0, self.vehicle["purchase_date"])

        tk.Label(body, text="Current Odometer (km) *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=8, column=1, sticky="w", pady=(0, 2))
        self.ent_odo = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_odo.grid(row=9, column=1, sticky="ew", padx=(6, 0), pady=(0, 10), ipady=4)
        if self.vehicle:
            self.ent_odo.insert(0, str(self.vehicle.get("current_odometer", 0.0)))
        else:
            self.ent_odo.insert(0, "0")

        # Notes
        tk.Label(body, text="Optional Notes / Description", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=10, column=0, sticky="w", pady=(0, 2))
        self.ent_notes = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_notes.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 5), ipady=4)
        if self.vehicle and self.vehicle.get("notes"):
            self.ent_notes.insert(0, self.vehicle["notes"])

        body.grid_columnconfigure((0, 1), weight=1)

    def on_submit(self):
        v_type = self.cmb_type.get().strip()
        brand = self.ent_brand.get().strip()
        model = self.ent_model.get().strip()
        reg_number = self.ent_reg.get().strip().upper()
        purchase_date = self.ent_date.get().strip()
        odo_str = self.ent_odo.get().strip()
        notes = self.ent_notes.get().strip()

        # Validation
        if not v_type or not brand or not model or not reg_number:
            messagebox.showerror("Validation Error", "Vehicle Type, Brand, Model, and Registration Number are required.", parent=self)
            return

        # Check duplicate registration
        exclude_id = self.vehicle["vehicle_id"] if self.vehicle else None
        duplicate = database.get_vehicle_by_registration(reg_number, exclude_id=exclude_id)
        if duplicate:
            messagebox.showerror("Duplicate Registration", f"A vehicle with registration number '{reg_number}' already exists.", parent=self)
            return

        # Validate Odometer
        try:
            odometer = float(odo_str)
            if odometer < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Current odometer must be a non-negative number.", parent=self)
            return

        # Validate Date format if provided
        if purchase_date:
            try:
                datetime.strptime(purchase_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Validation Error", "Purchase date must follow the format YYYY-MM-DD (e.g. 2023-05-15).", parent=self)
                return

        # Perform save
        try:
            if self.vehicle:
                database.update_vehicle(
                    vehicle_id=self.vehicle["vehicle_id"],
                    vehicle_type=v_type,
                    brand=brand,
                    model=model,
                    registration_number=reg_number,
                    purchase_date=purchase_date if purchase_date else None,
                    current_odometer=odometer,
                    notes=notes if notes else None
                )
            else:
                database.add_vehicle(
                    vehicle_type=v_type,
                    brand=brand,
                    model=model,
                    registration_number=reg_number,
                    purchase_date=purchase_date if purchase_date else None,
                    current_odometer=odometer,
                    notes=notes if notes else None
                )

            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save vehicle: {str(e)}", parent=self)


class VehiclesView(tk.Frame):
    def __init__(self, parent, on_data_changed: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_main"], **kwargs)
        self.on_data_changed = on_data_changed
        self._vehicles_cache = []

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Top Header & Action Buttons
        top_frame = tk.Frame(self, bg=COLORS["bg_main"])
        top_frame.pack(fill="x", padx=24, pady=(20, 16))

        title_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="My Vehicles",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Manage registered bikes, cars, and odometer readings",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        btn_box.pack(side="right")

        StyledButton(
            btn_box,
            text="+ Register Vehicle",
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

        # 2. Search & Filter Bar
        filter_card = CardContainer(self, padx=16, pady=12)
        filter_card.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(filter_card, text="Search Vehicles:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 8))

        self.ent_search = tk.Entry(filter_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=30)
        self.ent_search.pack(side="left", padx=(0, 10), ipady=3)
        self.ent_search.bind("<KeyRelease>", lambda e: self.filter_table())

        StyledButton(filter_card, text="Clear", variant="secondary", command=self.clear_search).pack(side="left")

        self.lbl_count = tk.Label(filter_card, text="0 vehicles found", font=FONTS["small"], fg=COLORS["text_muted"], bg=COLORS["card_bg"])
        self.lbl_count.pack(side="right")

        # 3. Main Vehicles Table
        table_card = CardContainer(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        columns = [
            {"id": "id", "name": "ID", "width": 50, "anchor": "center"},
            {"id": "type", "name": "Type", "width": 80, "anchor": "center"},
            {"id": "brand", "name": "Brand", "width": 140, "anchor": "w"},
            {"id": "model", "name": "Model", "width": 150, "anchor": "w"},
            {"id": "reg", "name": "Registration No.", "width": 140, "anchor": "w"},
            {"id": "purchase_date", "name": "Purchase Date", "width": 110, "anchor": "center"},
            {"id": "odometer", "name": "Current Odometer", "width": 130, "anchor": "e"},
            {"id": "notes", "name": "Notes", "width": 200, "anchor": "w"}
        ]
        self.table = TableView(table_card, columns=columns)
        self.table.pack(fill="both", expand=True)

        self.empty_lbl = tk.Label(
            table_card,
            text="No vehicles registered yet.\nClick '+ Register Vehicle' to add your first bike or car.",
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            pady=40
        )

    def refresh_data(self):
        """Fetch all vehicles from the database and populate the table."""
        self._vehicles_cache = [dict(v) for v in database.get_all_vehicles()]
        self.filter_table()

    def filter_table(self):
        query = self.ent_search.get().strip().lower()
        filtered = []

        for v in self._vehicles_cache:
            if not query or (
                query in v["registration_number"].lower() or
                query in v["brand"].lower() or
                query in v["model"].lower() or
                query in v["vehicle_type"].lower()
            ):
                filtered.append(v)

        if filtered:
            self.empty_lbl.pack_forget()
            self.table.pack(fill="both", expand=True)

            rows = []
            ids = []
            for v in filtered:
                ids.append(v["vehicle_id"])
                rows.append([
                    v["vehicle_id"],
                    v["vehicle_type"],
                    v["brand"],
                    v["model"],
                    v["registration_number"],
                    v["purchase_date"] or "—",
                    format_odometer(v["current_odometer"]),
                    v["notes"] or ""
                ])
            self.table.insert_rows(rows, ids=ids)
            self.lbl_count.config(text=f"{len(filtered)} vehicle{'s' if len(filtered) != 1 else ''} registered")
        else:
            self.table.clear()
            self.table.pack_forget()
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_count.config(text="0 vehicles found")

    def clear_search(self):
        self.ent_search.delete(0, "end")
        self.filter_table()

    def open_add_dialog(self):
        VehicleFormDialog(self, on_success=self._on_vehicle_saved)

    def open_edit_dialog(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Vehicle", "Please select a vehicle from the table to edit.", parent=self)
            return

        vehicle = database.get_vehicle_by_id(int(sel_id))
        if vehicle:
            VehicleFormDialog(self, vehicle=dict(vehicle), on_success=self._on_vehicle_saved)

    def delete_selected(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Vehicle", "Please select a vehicle from the table to delete.", parent=self)
            return

        v_id = int(sel_id)
        vehicle = database.get_vehicle_by_id(v_id)
        if not vehicle:
            return

        v_name = f"{vehicle['brand']} {vehicle['model']} ({vehicle['registration_number']})"
        counts = database.get_vehicle_dependent_counts(v_id)

        msg = f"Are you sure you want to delete '{v_name}'?"
        if counts["total"] > 0:
            msg += (
                f"\n\nWARNING: This vehicle has {counts['total']} linked records:\n"
                f"  • {counts['fuel']} fuel purchase(s)\n"
                f"  • {counts['service']} service record(s)\n"
                f"  • {counts['expenses']} other expense(s)\n\n"
                f"Deleting this vehicle will permanently delete ALL linked records!"
            )

        confirm = messagebox.askyesno("Confirm Vehicle Deletion", msg, icon="warning", parent=self)
        if confirm:
            database.delete_vehicle(v_id)
            messagebox.showinfo("Deleted", f"Vehicle '{v_name}' has been deleted.", parent=self)
            self._on_vehicle_saved()

    def _on_vehicle_saved(self):
        self.refresh_data()
        if self.on_data_changed:
            self.on_data_changed()
