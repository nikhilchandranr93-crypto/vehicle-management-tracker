"""
reports.py - Financial & Vehicle Analysis Reports for VehicleCare.
Provides aggregations by vehicle, monthly breakdowns, comprehensive activity logs,
and standard CSV file export.
"""

import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta
from typing import Optional, Callable, Dict, Any, List
import database
from ui_common import (
    COLORS, FONTS, StyledButton, CardContainer, TableView,
    format_currency, format_odometer
)


class ReportsView(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_main"], **kwargs)

        self._current_report_data: List[List[Any]] = []
        self._current_report_headers: List[str] = []

        self._build_ui()
        self.generate_report()

    def _build_ui(self):
        # 1. Header & Actions
        top_frame = tk.Frame(self, bg=COLORS["bg_main"])
        top_frame.pack(fill="x", padx=24, pady=(20, 16))

        title_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="Reports & Financial Analytics",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Analyze lifetime ownership costs, monthly spend trends, and export CSV reports",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        btn_box.pack(side="right")

        StyledButton(
            btn_box,
            text="📥 Export to CSV",
            variant="success",
            command=self.export_csv
        ).pack(side="left", padx=4)

        # 2. Controls & Filter Card
        controls_card = CardContainer(self, padx=16, pady=12)
        controls_card.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(controls_card, text="Report Type:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 6))

        self.report_types = [
            "Expenses by Vehicle",
            "Monthly Expense Breakdown",
            "Comprehensive Activity Log"
        ]
        self.cmb_report_type = ttk.Combobox(controls_card, values=self.report_types, state="readonly", font=FONTS["body"], width=26)
        self.cmb_report_type.pack(side="left", padx=(0, 14))
        self.cmb_report_type.current(0)
        self.cmb_report_type.bind("<<ComboboxSelected>>", lambda e: self.generate_report())

        tk.Label(controls_card, text="Date Range:", font=FONTS["body_bold"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        self.ent_start_date = tk.Entry(controls_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=10)
        self.ent_start_date.pack(side="left", padx=(0, 4), ipady=2)
        tk.Label(controls_card, text="to", font=FONTS["body"], fg=COLORS["text_muted"], bg=COLORS["card_bg"]).pack(side="left", padx=(0, 4))
        self.ent_end_date = tk.Entry(controls_card, font=FONTS["body"], bg="#F8FAFC", relief="solid", bd=1, width=10)
        self.ent_end_date.pack(side="left", padx=(0, 8), ipady=2)

        StyledButton(controls_card, text="Generate", variant="primary", command=self.generate_report).pack(side="left", padx=3)
        StyledButton(controls_card, text="All Time", variant="secondary", command=self.set_all_time).pack(side="left", padx=3)
        StyledButton(controls_card, text="This Year", variant="secondary", command=self.set_this_year).pack(side="left", padx=3)

        self.lbl_report_status = tk.Label(controls_card, text="", font=FONTS["small_bold"], fg=COLORS["primary"], bg=COLORS["card_bg"])
        self.lbl_report_status.pack(side="right")

        # 3. Report Data Table Card
        self.table_card = CardContainer(self, padx=16, pady=16)
        self.table_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self.table_frame = tk.Frame(self.table_card, bg=COLORS["card_bg"])
        self.table_frame.pack(fill="both", expand=True)

        self.empty_lbl = tk.Label(
            self.table_card,
            text="No data available for the selected report and date range.",
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            pady=40
        )

    def refresh_data(self):
        """Called by tab switcher."""
        self.generate_report()

    def set_all_time(self):
        self.ent_start_date.delete(0, "end")
        self.ent_end_date.delete(0, "end")
        self.generate_report()

    def set_this_year(self):
        today = date.today()
        self.ent_start_date.delete(0, "end")
        self.ent_start_date.insert(0, f"{today.year}-01-01")
        self.ent_end_date.delete(0, "end")
        self.ent_end_date.insert(0, f"{today.year}-12-31")
        self.generate_report()

    def generate_report(self):
        currency = database.get_setting("currency", "₹")
        start_date = self.ent_start_date.get().strip() or None
        end_date = self.ent_end_date.get().strip() or None
        rep_type = self.cmb_report_type.get()

        # Clear existing table widget
        for w in self.table_frame.winfo_children():
            w.destroy()

        if rep_type == "Expenses by Vehicle":
            self._render_vehicle_expenses_report(start_date, end_date, currency)
        elif rep_type == "Monthly Expense Breakdown":
            self._render_monthly_breakdown_report(start_date, end_date, currency)
        else:
            self._render_comprehensive_log_report(start_date, end_date, currency)

    def _render_vehicle_expenses_report(self, start_date, end_date, currency):
        data = database.get_report_expenses_by_vehicle(start_date=start_date, end_date=end_date)
        cols = [
            {"id": "name", "name": "Vehicle Name", "width": 200, "anchor": "w"},
            {"id": "type", "name": "Type", "width": 80, "anchor": "center"},
            {"id": "fuel", "name": "Fuel Expense", "width": 120, "anchor": "e"},
            {"id": "litres", "name": "Fuel Litres", "width": 90, "anchor": "e"},
            {"id": "service", "name": "Service Cost", "width": 120, "anchor": "e"},
            {"id": "other", "name": "Other Expenses", "width": 120, "anchor": "e"},
            {"id": "total", "name": "Total Spend", "width": 130, "anchor": "e"},
            {"id": "odo", "name": "Current Odometer", "width": 120, "anchor": "e"}
        ]
        self._current_report_headers = [c["name"] for c in cols]
        self._current_report_data = []

        if not data:
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_report_status.config(text="0 records")
            return

        self.empty_lbl.pack_forget()
        table = TableView(self.table_frame, columns=cols)
        table.pack(fill="both", expand=True)

        rows = []
        tot_all = 0.0
        for d in data:
            tot_all += d["total_expense"]
            row = [
                d["vehicle_name"],
                d["type"],
                format_currency(d["fuel_expense"], currency),
                f"{d['total_litres']:,.1f} L",
                format_currency(d["service_expense"], currency),
                format_currency(d["other_expense"], currency),
                format_currency(d["total_expense"], currency),
                format_odometer(d["current_odometer"])
            ]
            rows.append(row)
            self._current_report_data.append(row)

        table.insert_rows(rows)
        self.lbl_report_status.config(text=f"Total: {format_currency(tot_all, currency)}")

    def _render_monthly_breakdown_report(self, start_date, end_date, currency):
        data = database.get_report_monthly_breakdown(start_date=start_date, end_date=end_date)
        cols = [
            {"id": "month", "name": "Month", "width": 110, "anchor": "center"},
            {"id": "fuel", "name": "Fuel Cost", "width": 140, "anchor": "e"},
            {"id": "service", "name": "Service Cost", "width": 140, "anchor": "e"},
            {"id": "other", "name": "Other Expenses", "width": 140, "anchor": "e"},
            {"id": "total", "name": "Monthly Total", "width": 160, "anchor": "e"}
        ]
        self._current_report_headers = [c["name"] for c in cols]
        self._current_report_data = []

        if not data:
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_report_status.config(text="0 months")
            return

        self.empty_lbl.pack_forget()
        table = TableView(self.table_frame, columns=cols)
        table.pack(fill="both", expand=True)

        rows = []
        tot_all = 0.0
        for d in data:
            tot_all += d["total_cost"]
            row = [
                d["month"],
                format_currency(d["fuel_cost"], currency),
                format_currency(d["service_cost"], currency),
                format_currency(d["other_cost"], currency),
                format_currency(d["total_cost"], currency)
            ]
            rows.append(row)
            self._current_report_data.append(row)

        table.insert_rows(rows)
        self.lbl_report_status.config(text=f"Grand Total: {format_currency(tot_all, currency)}")

    def _render_comprehensive_log_report(self, start_date, end_date, currency):
        activities = database.get_recent_activity(limit=500)
        if start_date:
            activities = [a for a in activities if a["date"] >= start_date]
        if end_date:
            activities = [a for a in activities if a["date"] <= end_date]

        cols = [
            {"id": "date", "name": "Date", "width": 100, "anchor": "center"},
            {"id": "type", "name": "Category Type", "width": 110, "anchor": "center"},
            {"id": "vehicle", "name": "Vehicle", "width": 190, "anchor": "w"},
            {"id": "desc", "name": "Description / Work", "width": 260, "anchor": "w"},
            {"id": "amount", "name": "Amount", "width": 120, "anchor": "e"}
        ]
        self._current_report_headers = [c["name"] for c in cols]
        self._current_report_data = []

        if not activities:
            self.empty_lbl.pack(fill="both", expand=True)
            self.lbl_report_status.config(text="0 transactions")
            return

        self.empty_lbl.pack_forget()
        table = TableView(self.table_frame, columns=cols)
        table.pack(fill="both", expand=True)

        rows = []
        tot_all = 0.0
        for a in activities:
            tot_all += a["amount"]
            row = [
                a["date"],
                a["type"],
                a["vehicle"],
                a["description"],
                format_currency(a["amount"], currency)
            ]
            rows.append(row)
            self._current_report_data.append(row)

        table.insert_rows(rows)
        self.lbl_report_status.config(text=f"{len(activities)} items | {format_currency(tot_all, currency)}")

    def export_csv(self):
        """Export current report preview to a standard CSV file."""
        if not self._current_report_data:
            messagebox.showwarning("Export CSV", "No report data available to export.", parent=self)
            return

        today_tag = date.today().strftime("%Y%m%d")
        default_filename = f"VehicleCare_{self.cmb_report_type.get().replace(' ', '_')}_{today_tag}.csv"

        filepath = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV (Comma delimited)", "*.csv"), ("All Files", "*.*")],
            title="Save VehicleCare Report as CSV",
            parent=self
        )

        if not filepath:
            return  # Cancelled dialog

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self._current_report_headers)
                writer.writerows(self._current_report_data)

            messagebox.showinfo(
                "Export Successful",
                f"Report successfully saved to:\n{filepath}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error",
                f"Failed to write CSV file: {str(e)}",
                parent=self
            )
