"""
expenses.py - General Vehicle Expenses Module for VehicleCare.
Manages vehicle-related costs not represented by fuel or service records,
such as insurance, taxes, accessories, tolls, and parking.
Prevents double-counting by keeping general expenses in a dedicated table.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from typing import Optional, Callable, Dict, Any, List
import database
from ui_common import (
    COLORS, FONTS, StyledButton, CardContainer, TableView,
    FormDialog, format_currency
)


class ExpenseFormDialog(FormDialog):
    """Modal dialog for logging or editing other vehicle expenses."""
    def __init__(self, parent, expense_record: Optional[dict] = None,
                 default_vehicle_id: Optional[int] = None,
                 on_success: Optional[Callable] = None):
        title = "Edit Expense" if expense_record else "Add Other Expense"
        super().__init__(parent, title=title, width=520, height=480)
        self.expense_record = expense_record
        self.default_vehicle_id = default_vehicle_id
        self.on_success = on_success

        self._vehicles = [dict(v) for v in database.get_all_vehicles()]
        self._build_form()

    def _build_form(self):
        body = self.body_card

        # Vehicle
        tk.Label(body, text="Select Vehicle *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.vehicle_options = {
            f"{v['brand']} {v['model']} ({v['registration_number']})": v["vehicle_id"]
            for v in self._vehicles
        }
        self.cmb_vehicle = ttk.Combobox(body, values=list(self.vehicle_options.keys()), state="readonly", font=FONTS["body"])
        self.cmb_vehicle.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        if self.expense_record:
            for name, vid in self.vehicle_options.items():
                if vid == self.expense_record["vehicle_id"]:
                    self.cmb_vehicle.set(name)
                    break
        elif self.default_vehicle_id:
            for name, vid in self.vehicle_options.items():
                if vid == self.default_vehicle_id:
                    self.cmb_vehicle.set(name)
                    break
        elif self.vehicle_options:
            self.cmb_vehicle.current(0)

        # Category
        tk.Label(body, text="Expense Category *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.cmb_category = ttk.Combobox(body, values=database.EXPENSE_CATEGORIES, state="readonly", font=FONTS["body"])
        self.cmb_category.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        if self.expense_record:
            self.cmb_category.set(self.expense_record["category"])
        else:
            self.cmb_category.current(0)

        # Date & Amount
        currency = database.get_setting("currency", "₹")
        tk.Label(body, text="Date * (YYYY-MM-DD)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.ent_date = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_date.grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(0, 10), ipady=4)
        if self.expense_record:
            self.ent_date.insert(0, self.expense_record["expense_date"])
        else:
            self.ent_date.insert(0, date.today().strftime("%Y-%m-%d"))

        tk.Label(body, text=f"Amount ({currency}) *", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=4, column=1, sticky="w", pady=(0, 2))
        self.ent_amount = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_amount.grid(row=5, column=1, sticky="ew", padx=(6, 0), pady=(0, 10), ipady=4)
        if self.expense_record:
            self.ent_amount.insert(0, str(self.expense_record["amount"]))

        # Description
        tk.Label(body, text="Description / Purpose (e.g. Annual policy renewal)", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.ent_desc = tk.Entry(body, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1)
        self.ent_desc.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=4)
        if self.expense_record and self.expense_record.get("description"):
            self.ent_desc.insert(0, self.expense_record["description"])

        body.grid_columnconfigure((0, 1), weight=1)

    def on_submit(self):
        veh_name = self.cmb_vehicle.get()
        if not veh_name or veh_name not in self.vehicle_options:
            messagebox.showerror("Validation Error", "Please select a registered vehicle.", parent=self)
            return

        vehicle_id = self.vehicle_options[veh_name]
        category = self.cmb_category.get().strip()
        e_date = self.ent_date.get().strip()
        amt_str = self.ent_amount.get().strip()
        desc = self.ent_desc.get().strip()

        if not category:
            messagebox.showerror("Validation Error", "Please select an expense category.", parent=self)
            return

        # Date validation
        try:
            datetime.strptime(e_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Date must follow YYYY-MM-DD format (e.g. 2024-03-25).", parent=self)
            return

        # Amount validation
        try:
            amount = float(amt_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Amount must be a positive number greater than 0.", parent=self)
            return

        try:
            if self.expense_record:
                database.update_expense(
                    expense_id=self.expense_record["expense_id"],
                    vehicle_id=vehicle_id,
                    expense_date=e_date,
                    category=category,
                    amount=amount,
                    description=desc if desc else None
                )
            else:
                database.add_expense(
                    vehicle_id=vehicle_id,
                    expense_date=e_date,
                    category=category,
                    amount=amount,
                    description=desc if desc else None
                )

            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save expense: {str(e)}", parent=self)


class ExpensesView(tk.Frame):
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
            text="Other Vehicle Expenses",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Record insurance, taxes, parking, tolls, accessories, and other non-fuel/non-service costs",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        btn_box.pack(side="right")

        StyledButton(
            btn_box,
            text="+ Add Expense",
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

        # 2. Filter Bar
        filter_card = CardContainer(self, padx=16, pady=10)
        filter_card.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(filter_card, text="Vehicle:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        self.cmb_filter_veh = ttk.Combobox(filter_card, state="readonly", font=FONTS["body"], width=22)
        self.cmb_filter_veh.pack(side="left", padx=(0, 10))
        self.cmb_filter_veh.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(filter_card, text="Category:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        cat_values = ["All"] + database.EXPENSE_CATEGORIES
        self.cmb_filter_cat = ttk.Combobox(filter_card, values=cat_values, state="readonly", font=FONTS["body"], width=18)
        self.cmb_filter_cat.pack(side="left", padx=(0, 10))
        self.cmb_filter_cat.current(0)
        self.cmb_filter_cat.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(filter_card, text="Date Range:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        self.ent_start_date = tk.Entry(filter_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=10)
        self.ent_start_date.pack(side="left", padx=(0, 4), ipady=2)
        tk.Label(filter_card, text="to", font=FONTS["body"], fg=COLORS["text_muted"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        self.ent_end_date = tk.Entry(filter_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=10)
        self.ent_end_date.pack(side="left", padx=(0, 6), ipady=2)

        StyledButton(filter_card, text="Apply Filter", variant="primary", command=self.apply_filters).pack(side="left", padx=4)
        StyledButton(filter_card, text="Reset", variant="secondary", command=self.reset_filters).pack(side="left", padx=4)

        self.lbl_record_count = tk.Label(filter_card, text="0 records", font=FONTS["small"], fg=COLORS["text_muted"], bg=COLORS["card_bg"])
        self.lbl_record_count.pack(side="right")

        # 3. Main Records Table
        table_card = CardContainer(self, padx=16, pady=16)
        table_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        columns = [
            {"id": "id", "name": "ID", "width": 50, "anchor": "center"},
            {"id": "date", "name": "Date", "width": 100, "anchor": "center"},
            {"id": "vehicle", "name": "Vehicle", "width": 180, "anchor": "w"},
            {"id": "category", "name": "Category", "width": 160, "anchor": "w"},
            {"id": "amount", "name": "Amount", "width": 120, "anchor": "e"},
            {"id": "description", "name": "Description / Purpose", "width": 300, "anchor": "w"}
        ]
        self.table = TableView(table_card, columns=columns)
        self.table.pack(fill="both", expand=True)

        self.empty_lbl = tk.Label(
            table_card,
            text="No miscellaneous expenses logged.\nClick '+ Add Expense' to record insurance, taxes, tolls, or accessories.",
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            pady=40
        )

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

        category = self.cmb_filter_cat.get()
        start_date = self.ent_start_date.get().strip() or None
        end_date = self.ent_end_date.get().strip() or None

        records = database.get_expenses(
            vehicle_id=veh_id,
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        if records:
            self.empty_lbl.pack_forget()
            self.table.pack(fill="both", expand=True)

            rows = []
            ids = []
            total_amt = 0.0
            for r in records:
                ids.append(r["expense_id"])
                total_amt += r["amount"]
                rows.append([
                    r["expense_id"],
                    r["expense_date"],
                    r["vehicle_name"],
                    r["category"],
                    format_currency(r["amount"], currency),
                    r["description"] or "—"
                ])
            self.table.insert_rows(rows, ids=ids)
            self.lbl_record_count.config(text=f"{len(records)} record{'s' if len(records) != 1 else ''} | Total: {format_currency(total_amt, currency)}")
        else:
            self.table.clear()
            self.table.pack_forget()
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_record_count.config(text="0 records")

    def reset_filters(self):
        self.cmb_filter_veh.current(0)
        self.cmb_filter_cat.current(0)
        self.ent_start_date.delete(0, "end")
        self.ent_end_date.delete(0, "end")
        self.apply_filters()

    def open_add_dialog(self):
        vehicles = database.get_all_vehicles()
        if not vehicles:
            messagebox.showwarning("No Vehicles Found", "Please register at least one vehicle before adding expenses.", parent=self)
            return

        selected_veh_str = self.cmb_filter_veh.get()
        default_vid = self.veh_filter_map.get(selected_veh_str)
        ExpenseFormDialog(self, default_vehicle_id=default_vid, on_success=self._on_record_saved)

    def open_edit_dialog(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Record", "Please select an expense record from the table to edit.", parent=self)
            return

        records = database.get_expenses()
        target = next((r for r in records if r["expense_id"] == int(sel_id)), None)
        if target:
            ExpenseFormDialog(self, expense_record=dict(target), on_success=self._on_record_saved)

    def delete_selected(self):
        sel_id = self.table.get_selected_id()
        if not sel_id:
            messagebox.showwarning("Select Record", "Please select an expense record to delete.", parent=self)
            return

        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this expense record?", icon="warning", parent=self)
        if confirm:
            database.delete_expense(int(sel_id))
            messagebox.showinfo("Deleted", "Expense record deleted.", parent=self)
            self._on_record_saved()

    def _on_record_saved(self):
        self.apply_filters()
        if self.on_data_changed:
            self.on_data_changed()
