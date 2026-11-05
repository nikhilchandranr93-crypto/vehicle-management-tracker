"""
main.py - Main Entry Point for VehicleCare — Vehicle Management Tracker.
Initializes the SQLite database, configures the modern design system,
sets up the persistent navigation sidebar and page routing.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
from ui_common import (
    COLORS, FONTS, setup_ttk_styles
)
from dashboard import DashboardView
from vehicles import VehiclesView
from fuel import FuelView
from service import ServiceView
from expenses import ExpensesView
from reports import ReportsView
from settings import SettingsView


class VehicleCareApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("VehicleCare — Vehicle Management Tracker")
        self.geometry("1100x700")
        self.minsize(850, 580)
        self.configure(bg=COLORS["bg_main"])

        # Initialize SQLite database schema
        database.init_db()

        # Configure modern TTK styles
        self.ttk_style = setup_ttk_styles(self)

        # Application state
        self._nav_buttons: Dict[str, tk.Frame] = {}
        self._current_page: str = "Dashboard"

        self._build_main_layout()
        self.show_page("Dashboard")

    def _build_main_layout(self):
        # 1. Left Persistent Sidebar
        self.sidebar = tk.Frame(self, bg=COLORS["bg_sidebar"], width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand header inside sidebar
        brand_frame = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"], padx=20, pady=24)
        brand_frame.pack(fill="x")

        # Visual logo pill
        logo_row = tk.Frame(brand_frame, bg=COLORS["bg_sidebar"])
        logo_row.pack(anchor="w")

        icon_label = tk.Label(
            logo_row,
            text=" ⚙ ",
            font=(FONTS["title"][0], 14, "bold"),
            fg=COLORS["text_white"],
            bg=COLORS["primary"],
            padx=4,
            pady=2
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_col = tk.Frame(logo_row, bg=COLORS["bg_sidebar"])
        title_col.pack(side="left")

        tk.Label(
            title_col,
            text="VehicleCare",
            font=FONTS["header"],
            fg=COLORS["text_white"],
            bg=COLORS["bg_sidebar"]
        ).pack(anchor="w")

        tk.Label(
            title_col,
            text="Vehicle Tracker",
            font=FONTS["small"],
            fg="#94A3B8",
            bg=COLORS["bg_sidebar"]
        ).pack(anchor="w")

        # Thin separator in sidebar
        tk.Frame(self.sidebar, bg="#233352", height=1).pack(fill="x", padx=16, pady=(8, 16))

        # Navigation items
        nav_items = [
            ("Dashboard", "📊  Dashboard"),
            ("My Vehicles", "🚗  My Vehicles"),
            ("Fuel Tracker", "⛽  Fuel Tracker"),
            ("Service History", "🔧  Service History"),
            ("Expenses", "💳  Expenses"),
            ("Reports", "📈  Reports"),
            ("Settings", "⚙  Settings")
        ]

        self.nav_container = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"])
        self.nav_container.pack(fill="x", padx=10)

        for key, display_text in nav_items:
            self._create_nav_button(key, display_text)

        # Sidebar footer
        sidebar_footer = tk.Frame(self.sidebar, bg=COLORS["bg_sidebar"], padx=20, pady=16)
        sidebar_footer.pack(side="bottom", fill="x")

        self.lbl_currency_indicator = tk.Label(
            sidebar_footer,
            text=f"Currency: {database.get_setting('currency', '₹')}",
            font=FONTS["small"],
            fg="#94A3B8",
            bg=COLORS["bg_sidebar"],
            anchor="w"
        )
        self.lbl_currency_indicator.pack(fill="x")

        tk.Label(
            sidebar_footer,
            text="v1.0.0 • SQLite Offline",
            font=FONTS["small"],
            fg="#64748B",
            bg=COLORS["bg_sidebar"],
            anchor="w"
        ).pack(fill="x", pady=(2, 0))

        # 2. Main Content Host Area
        self.content_area = tk.Frame(self, bg=COLORS["bg_main"])
        self.content_area.pack(side="right", fill="both", expand=True)

        # Pages instantiation dictionary
        self.pages: Dict[str, Any] = {
            "Dashboard": DashboardView(
                self.content_area,
                nav_callback=self.show_page,
                action_callback=self._handle_quick_action
            ),
            "My Vehicles": VehiclesView(
                self.content_area,
                on_data_changed=self._on_data_modified
            ),
            "Fuel Tracker": FuelView(
                self.content_area,
                on_data_changed=self._on_data_modified
            ),
            "Service History": ServiceView(
                self.content_area,
                on_data_changed=self._on_data_modified
            ),
            "Expenses": ExpensesView(
                self.content_area,
                on_data_changed=self._on_data_modified
            ),
            "Reports": ReportsView(
                self.content_area
            ),
            "Settings": SettingsView(
                self.content_area,
                on_settings_changed=self._on_settings_modified
            )
        }

    def _create_nav_button(self, key: str, display_text: str):
        btn_frame = tk.Frame(self.nav_container, bg=COLORS["bg_sidebar"], cursor="hand2")
        btn_frame.pack(fill="x", pady=2)

        # Active indicator strip (blue line on left when selected)
        indicator = tk.Frame(btn_frame, bg=COLORS["bg_sidebar"], width=4)
        indicator.pack(side="left", fill="y")

        lbl = tk.Label(
            btn_frame,
            text=display_text,
            font=FONTS["sidebar"],
            fg="#CBD5E1",
            bg=COLORS["bg_sidebar"],
            padx=14,
            pady=10,
            anchor="w"
        )
        lbl.pack(side="left", fill="both", expand=True)

        # Click and hover bindings
        def on_click(e):
            self.show_page(key)

        def on_enter(e):
            if self._current_page != key:
                btn_frame.config(bg=COLORS["bg_sidebar_hover"])
                lbl.config(bg=COLORS["bg_sidebar_hover"], fg=COLORS["text_white"])

        def on_leave(e):
            if self._current_page != key:
                btn_frame.config(bg=COLORS["bg_sidebar"])
                lbl.config(bg=COLORS["bg_sidebar"], fg="#CBD5E1")

        btn_frame.bind("<Button-1>", on_click)
        lbl.bind("<Button-1>", on_click)
        indicator.bind("<Button-1>", on_click)

        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)
        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)

        self._nav_buttons[key] = {
            "frame": btn_frame,
            "label": lbl,
            "indicator": indicator
        }

    def show_page(self, page_name: str):
        """Navigate to the requested view and update sidebar active state."""
        if page_name not in self.pages:
            return

        self._current_page = page_name

        # Update sidebar styling
        for key, widgets in self._nav_buttons.items():
            if key == page_name:
                widgets["frame"].config(bg=COLORS["bg_sidebar_active"])
                widgets["label"].config(
                    bg=COLORS["bg_sidebar_active"],
                    fg=COLORS["text_white"],
                    font=FONTS["sidebar_active"]
                )
                widgets["indicator"].config(bg=COLORS["primary"])
            else:
                widgets["frame"].config(bg=COLORS["bg_sidebar"])
                widgets["label"].config(
                    bg=COLORS["bg_sidebar"],
                    fg="#CBD5E1",
                    font=FONTS["sidebar"]
                )
                widgets["indicator"].config(bg=COLORS["bg_sidebar"])

        # Hide all pages and show current
        for name, view in self.pages.items():
            if name == page_name:
                view.pack(fill="both", expand=True)
                if hasattr(view, "refresh_data"):
                    view.refresh_data()
            else:
                view.pack_forget()

    def _handle_quick_action(self, action_name: str):
        """Route quick action requests from dashboard directly to target module dialogs."""
        if action_name == "add_vehicle":
            self.show_page("My Vehicles")
            self.pages["My Vehicles"].open_add_dialog()
        elif action_name == "add_fuel":
            self.show_page("Fuel Tracker")
            self.pages["Fuel Tracker"].open_add_dialog()
        elif action_name == "add_service":
            self.show_page("Service History")
            self.pages["Service History"].open_add_dialog()
        elif action_name == "add_expense":
            self.show_page("Expenses")
            self.pages["Expenses"].open_add_dialog()

    def _on_data_modified(self):
        """Refresh dashboard and other views when records are added, edited, or deleted."""
        # Refresh dashboard if initialized
        if "Dashboard" in self.pages and hasattr(self.pages["Dashboard"], "refresh_data"):
            self.pages["Dashboard"].refresh_data()

    def _on_settings_modified(self):
        """Refresh all views when currency or reminder settings are updated."""
        curr = database.get_setting("currency", "₹")
        self.lbl_currency_indicator.config(text=f"Currency: {curr}")

        for view in self.pages.values():
            if hasattr(view, "refresh_data"):
                view.refresh_data()


def main():
    """Application launcher."""
    try:
        app = VehicleCareApp()
        app.mainloop()
    except Exception as e:
        print(f"Error launching VehicleCare: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
