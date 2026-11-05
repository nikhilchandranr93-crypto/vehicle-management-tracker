"""
dashboard.py - Main Dashboard view for VehicleCare.
Presents high-level metrics, quick actions, recent activity feed,
and upcoming maintenance reminders.
"""

import tkinter as tk
from tkinter import ttk
from datetime import date
from typing import Callable, Optional
import database
from ui_common import COLORS, FONTS, StatCard, StyledButton, CardContainer, TableView, format_currency


class DashboardView(tk.Frame):
    def __init__(self, parent, nav_callback: Callable[[str], None],
                 action_callback: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_main"], **kwargs)
        self.nav_callback = nav_callback
        self.action_callback = action_callback

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Quick Actions & Header Banner
        top_frame = tk.Frame(self, bg=COLORS["bg_main"])
        top_frame.pack(fill="x", padx=24, pady=(20, 16))

        # Title & Date
        title_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="Dashboard Overview",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        today_str = date.today().strftime("%A, %d %B %Y")
        tk.Label(
            title_box,
            text=f"Today is {today_str}",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        # Action Buttons
        btn_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        btn_box.pack(side="right")

        StyledButton(
            btn_box,
            text="+ Add Vehicle",
            variant="outline",
            command=lambda: self._trigger_action("add_vehicle")
        ).pack(side="left", padx=4)

        StyledButton(
            btn_box,
            text="+ Record Fuel",
            variant="primary",
            command=lambda: self._trigger_action("add_fuel")
        ).pack(side="left", padx=4)

        StyledButton(
            btn_box,
            text="+ Add Service",
            variant="outline",
            command=lambda: self._trigger_action("add_service")
        ).pack(side="left", padx=4)

        StyledButton(
            btn_box,
            text="+ Add Expense",
            variant="outline",
            command=lambda: self._trigger_action("add_expense")
        ).pack(side="left", padx=4)

        # 2. Four Stat Cards Grid
        cards_frame = tk.Frame(self, bg=COLORS["bg_main"])
        cards_frame.pack(fill="x", padx=24, pady=(0, 20))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat_cards")

        self.card_vehicles = StatCard(
            cards_frame,
            title="Total Vehicles",
            value="0",
            subtitle="Registered cars & bikes",
            accent_color=COLORS["primary"]
        )
        self.card_vehicles.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.card_fuel = StatCard(
            cards_frame,
            title="Total Fuel Expenses",
            value="₹ 0.00",
            subtitle="Lifetime fuel spend",
            accent_color=COLORS["info"]
        )
        self.card_fuel.grid(row=0, column=1, sticky="nsew", padx=5)

        self.card_service = StatCard(
            cards_frame,
            title="Total Service Costs",
            value="₹ 0.00",
            subtitle="Maintenance & repairs",
            accent_color=COLORS["warning"]
        )
        self.card_service.grid(row=0, column=2, sticky="nsew", padx=5)

        self.card_total = StatCard(
            cards_frame,
            title="Total Expenses",
            value="₹ 0.00",
            subtitle="Fuel + Service + Other",
            accent_color=COLORS["success"]
        )
        self.card_total.grid(row=0, column=3, sticky="nsew", padx=(10, 0))

        # 3. Main Split View: Left = Recent Activity, Right = Upcoming Maintenance
        content_frame = tk.Frame(self, bg=COLORS["bg_main"])
        content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        content_frame.grid_columnconfigure(0, weight=6, uniform="dash_split")
        content_frame.grid_columnconfigure(1, weight=4, uniform="dash_split")
        content_frame.grid_rowconfigure(0, weight=1)

        # Left: Recent Activity Card
        recent_card = CardContainer(content_frame, padx=16, pady=16)
        recent_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        recent_header = tk.Frame(recent_card, bg=COLORS["card_bg"])
        recent_header.pack(fill="x", pady=(0, 12))

        tk.Label(
            recent_header,
            text="Recent Activity",
            font=FONTS["header"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"]
        ).pack(side="left")

        StyledButton(
            recent_header,
            text="View All Reports →",
            variant="outline",
            command=lambda: self.nav_callback("Reports")
        ).pack(side="right")

        # Activity Table
        activity_cols = [
            {"id": "date", "name": "Date", "width": 90, "anchor": "w"},
            {"id": "type", "name": "Type", "width": 75, "anchor": "center"},
            {"id": "vehicle", "name": "Vehicle", "width": 140, "anchor": "w"},
            {"id": "description", "name": "Details", "width": 170, "anchor": "w"},
            {"id": "amount", "name": "Amount", "width": 90, "anchor": "e"}
        ]
        self.activity_table = TableView(recent_card, columns=activity_cols)
        self.activity_table.pack(fill="both", expand=True)

        self.empty_recent_lbl = tk.Label(
            recent_card,
            text="No activity recorded yet.\nStart by registering a vehicle and recording fuel or service.",
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"]
        )

        # Right: Upcoming Maintenance Reminders Card
        reminders_card = CardContainer(content_frame, padx=16, pady=16)
        reminders_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        rem_header = tk.Frame(reminders_card, bg=COLORS["card_bg"])
        rem_header.pack(fill="x", pady=(0, 12))

        tk.Label(
            rem_header,
            text="Maintenance Alerts",
            font=FONTS["header"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"]
        ).pack(side="left")

        StyledButton(
            rem_header,
            text="Service History →",
            variant="outline",
            command=lambda: self.nav_callback("Service History")
        ).pack(side="right")

        # Scrollable reminder list container
        self.rem_canvas = tk.Canvas(reminders_card, bg=COLORS["card_bg"], highlightthickness=0)
        self.rem_scrollbar = ttk.Scrollbar(reminders_card, orient="vertical", command=self.rem_canvas.yview)
        self.rem_inner = tk.Frame(self.rem_canvas, bg=COLORS["card_bg"])

        self.rem_canvas.configure(yscrollcommand=self.rem_scrollbar.set)
        self.rem_window_id = self.rem_canvas.create_window((0, 0), window=self.rem_inner, anchor="nw")

        self.rem_inner.bind("<Configure>", lambda e: self.rem_canvas.configure(scrollregion=self.rem_canvas.bbox("all")))
        self.rem_canvas.bind("<Configure>", lambda e: self.rem_canvas.itemconfig(self.rem_window_id, width=e.width))

        self.rem_canvas.pack(side="left", fill="both", expand=True)
        self.rem_scrollbar.pack(side="right", fill="y")

    def _trigger_action(self, action_name: str):
        if self.action_callback:
            self.action_callback(action_name)
        else:
            # Fallback navigation
            if action_name == "add_vehicle":
                self.nav_callback("My Vehicles")
            elif action_name == "add_fuel":
                self.nav_callback("Fuel Tracker")
            elif action_name == "add_service":
                self.nav_callback("Service History")
            elif action_name == "add_expense":
                self.nav_callback("Expenses")

    def refresh_data(self):
        """Fetch latest database totals, recent activity, and maintenance reminders."""
        currency = database.get_setting("currency", "₹")
        lead_days = int(database.get_setting("reminder_days", "7"))

        # 1. Update summary cards
        summary = database.get_dashboard_summary()
        self.card_vehicles.update_data(
            str(summary["total_vehicles"]),
            f"{summary['total_vehicles']} active in garage"
        )
        self.card_fuel.update_data(
            format_currency(summary["total_fuel_expenses"], currency),
            "Direct fuel consumption"
        )
        self.card_service.update_data(
            format_currency(summary["total_service_costs"], currency),
            "Repairs and maintenance"
        )
        self.card_total.update_data(
            format_currency(summary["total_expenses"], currency),
            "Fuel + Service + Other"
        )

        # 2. Update Recent Activity
        activities = database.get_recent_activity(limit=9)
        if activities:
            self.empty_recent_lbl.pack_forget()
            self.activity_table.pack(fill="both", expand=True)
            rows = []
            for a in activities:
                rows.append([
                    a["date"],
                    a["type"],
                    a["vehicle"],
                    a["description"],
                    format_currency(a["amount"], currency)
                ])
            self.activity_table.insert_rows(rows)
        else:
            self.activity_table.pack_forget()
            self.empty_recent_lbl.pack(fill="both", expand=True, pady=40)

        # 3. Update Maintenance Reminders
        for widget in self.rem_inner.winfo_children():
            widget.destroy()

        reminders = database.get_upcoming_reminders(lead_days=lead_days)
        if not reminders:
            lbl_empty = tk.Label(
                self.rem_inner,
                text="No upcoming or overdue maintenance.\nAll vehicle services are up to date!",
                font=FONTS["body"],
                fg=COLORS["text_secondary"],
                bg=COLORS["card_bg"],
                justify="center",
                pady=40
            )
            lbl_empty.pack(fill="both", expand=True)
        else:
            for rem in reminders:
                self._build_reminder_item(rem)

    def _build_reminder_item(self, rem: dict):
        status = rem["status"]
        if status == "OVERDUE":
            badge_bg = COLORS["danger_light"]
            badge_fg = COLORS["danger"]
            border_col = COLORS["danger"]
        elif status == "DUE SOON":
            badge_bg = COLORS["warning_light"]
            badge_fg = COLORS["warning"]
            border_col = COLORS["warning"]
        else:
            badge_bg = COLORS["info_light"]
            badge_fg = COLORS["info"]
            border_col = COLORS["info"]

        item_card = tk.Frame(
            self.rem_inner,
            bg=COLORS["card_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=12,
            pady=10
        )
        item_card.pack(fill="x", pady=4, padx=2)

        # Top row: Vehicle Name + Status Pill
        row1 = tk.Frame(item_card, bg=COLORS["card_bg"])
        row1.pack(fill="x")

        tk.Label(
            row1,
            text=rem["vehicle_name"],
            font=FONTS["body_bold"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"],
            anchor="w"
        ).pack(side="left")

        status_lbl = tk.Label(
            row1,
            text=f" {status} ",
            font=FONTS["small_bold"],
            bg=badge_bg,
            fg=badge_fg,
            padx=6,
            pady=2
        )
        status_lbl.pack(side="right")

        # Category and Description
        tk.Label(
            item_card,
            text=f"{rem['category']} — {rem['description']}",
            font=FONTS["body"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"],
            anchor="w"
        ).pack(fill="x", pady=(3, 1))

        # Reason & Due details
        tk.Label(
            item_card,
            text=rem["reason"],
            font=FONTS["small"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            anchor="w"
        ).pack(fill="x")
