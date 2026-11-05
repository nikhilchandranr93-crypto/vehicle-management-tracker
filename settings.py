"""
settings.py - Application Settings and Database Administration for VehicleCare.
Provides currency preferences, reminder lead-time configuration,
safe live database backup and restore, and optional sample demo data.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import Optional, Callable
import database
from ui_common import (
    COLORS, FONTS, StyledButton, CardContainer
)

CURRENCY_OPTIONS = [
    ("₹ INR (Indian Rupee)", "₹"),
    ("$ USD (US Dollar)", "$"),
    ("€ EUR (Euro)", "€"),
    ("£ GBP (British Pound)", "£"),
    ("C$ CAD (Canadian Dollar)", "C$"),
    ("A$ AUD (Australian Dollar)", "A$"),
    ("¥ JPY (Japanese Yen)", "¥"),
    ("AED (UAE Dirham)", "AED"),
    ("Rs (South Asian Rupee)", "Rs")
]

REMINDER_LEAD_OPTIONS = [
    ("3 Days before due date", "3"),
    ("7 Days before due date (Recommended)", "7"),
    ("14 Days before due date", "14"),
    ("30 Days before due date", "30")
]


class SettingsView(tk.Frame):
    def __init__(self, parent, on_settings_changed: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_main"], **kwargs)
        self.on_settings_changed = on_settings_changed

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        # 1. Header
        top_frame = tk.Frame(self, bg=COLORS["bg_main"])
        top_frame.pack(fill="x", padx=24, pady=(20, 16))

        title_box = tk.Frame(top_frame, bg=COLORS["bg_main"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="Settings & Preferences",
            font=FONTS["title"],
            fg=COLORS["text_main"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Configure application preferences, currency formatting, and database backup & restore",
            font=FONTS["subtitle"],
            fg=COLORS["text_secondary"],
            bg=COLORS["bg_main"]
        ).pack(anchor="w", pady=(2, 0))

        # Main scrollable canvas container for settings panels
        canvas_card = tk.Frame(self, bg=COLORS["bg_main"])
        canvas_card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        canvas = tk.Canvas(canvas_card, bg=COLORS["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_card, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_main"])

        canvas.configure(yscrollcommand=scrollbar.set)
        win_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Section 1: General Preferences Card
        pref_card = CardContainer(scrollable_frame, padx=20, pady=18)
        pref_card.pack(fill="x", pady=(0, 16))

        tk.Label(pref_card, text="General Display Preferences", font=FONTS["header"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 4))
        tk.Label(pref_card, text="Customize the active currency symbol and maintenance alert triggers.", font=FONTS["small"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 16))

        grid_pref = tk.Frame(pref_card, bg=COLORS["card_bg"])
        grid_pref.pack(fill="x")
        grid_pref.grid_columnconfigure(1, weight=1)

        # Currency
        tk.Label(grid_pref, text="Currency Symbol:", font=FONTS["body_bold"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).grid(row=0, column=0, sticky="w", pady=8)
        self.currency_dict = {label: sym for label, sym in CURRENCY_OPTIONS}
        self.cmb_currency = ttk.Combobox(grid_pref, values=list(self.currency_dict.keys()), state="readonly", font=FONTS["body"], width=30)
        self.cmb_currency.grid(row=0, column=1, sticky="w", padx=14, pady=8)

        # Reminder Lead Time
        tk.Label(grid_pref, text="Reminder Advance Warning:", font=FONTS["body_bold"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).grid(row=1, column=0, sticky="w", pady=8)
        self.lead_dict = {label: val for label, val in REMINDER_LEAD_OPTIONS}
        self.cmb_lead = ttk.Combobox(grid_pref, values=list(self.lead_dict.keys()), state="readonly", font=FONTS["body"], width=30)
        self.cmb_lead.grid(row=1, column=1, sticky="w", padx=14, pady=8)

        StyledButton(pref_card, text="Save Preferences", variant="primary", command=self.save_preferences).pack(anchor="w", pady=(16, 0))

        # Section 2: Database Management & Backup Card
        db_card = CardContainer(scrollable_frame, padx=20, pady=18)
        db_card.pack(fill="x", pady=(0, 16))

        tk.Label(db_card, text="Database Administration", font=FONTS["header"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 4))
        tk.Label(db_card, text="Create complete backups of your records, or restore from a previous backup file.", font=FONTS["small"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 14))

        db_loc_box = tk.Frame(db_card, bg="#F8FAFC", highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=8)
        db_loc_box.pack(fill="x", pady=(0, 14))
        tk.Label(db_loc_box, text="Current Database Location:", font=FONTS["small_bold"], fg=COLORS["text_secondary"], bg="#F8FAFC").pack(anchor="w")
        self.lbl_db_path = tk.Label(db_loc_box, text=database.get_db_path(), font=FONTS["small"], fg=COLORS["primary"], bg="#F8FAFC", wraplength=700, justify="left")
        self.lbl_db_path.pack(anchor="w", pady=(2, 0))

        btn_row_db = tk.Frame(db_card, bg=COLORS["card_bg"])
        btn_row_db.pack(fill="x", pady=(0, 8))

        StyledButton(btn_row_db, text="💾 Backup Database", variant="primary", command=self.backup_database).pack(side="left", padx=(0, 10))
        StyledButton(btn_row_db, text="🔄 Restore Database", variant="outline", command=self.restore_database).pack(side="left")

        # Section 3: Demo Data & Reset (Optional with explicit confirmation)
        demo_card = CardContainer(scrollable_frame, padx=20, pady=18)
        demo_card.pack(fill="x", pady=(0, 16))

        tk.Label(demo_card, text="Data Management Tools", font=FONTS["header"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 4))
        tk.Label(demo_card, text="Load realistic test data for evaluation or reset the database cleanly.", font=FONTS["small"], fg=COLORS["text_secondary"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 14))

        demo_btns = tk.Frame(demo_card, bg=COLORS["card_bg"])
        demo_btns.pack(fill="x")

        StyledButton(demo_btns, text="Load Sample Demo Data", variant="secondary", command=self.load_demo_data).pack(side="left", padx=(0, 10))
        StyledButton(demo_btns, text="Reset All Records", variant="danger", command=self.reset_all_data).pack(side="left")

        # Section 4: About VehicleCare Card
        about_card = CardContainer(scrollable_frame, padx=20, pady=18)
        about_card.pack(fill="x", pady=(0, 16))

        tk.Label(about_card, text="About VehicleCare", font=FONTS["header"], fg=COLORS["text_main"], bg=COLORS["card_bg"]).pack(anchor="w", pady=(0, 4))
        tk.Label(
            about_card,
            text=(
                "VehicleCare — Vehicle Management Tracker v1.0.0\n"
                "A clean, reliable, offline-first desktop application designed for vehicle owners.\n"
                "Built with Python, Tkinter & SQLite.\n"
                "Runs 100% locally with zero cloud dependencies or web server requirements."
            ),
            font=FONTS["body"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            justify="left",
            pady=4
        ).pack(anchor="w")

    def refresh_data(self):
        """Fetch current settings from database and update comboboxes."""
        curr = database.get_setting("currency", "₹")
        lead = database.get_setting("reminder_days", "7")

        for label, sym in self.currency_dict.items():
            if sym == curr:
                self.cmb_currency.set(label)
                break

        for label, val in self.lead_dict.items():
            if val == lead:
                self.cmb_lead.set(label)
                break

        self.lbl_db_path.config(text=database.get_db_path())

    def save_preferences(self):
        curr_label = self.cmb_currency.get()
        lead_label = self.cmb_lead.get()

        sym = self.currency_dict.get(curr_label, "₹")
        days = self.lead_dict.get(lead_label, "7")

        database.set_setting("currency", sym)
        database.set_setting("reminder_days", days)

        messagebox.showinfo("Preferences Saved", f"Preferences saved successfully!\nActive Currency: {sym}\nReminder Lead Time: {days} days", parent=self)

        if self.on_settings_changed:
            self.on_settings_changed()

    def backup_database(self):
        today_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"VehicleCare_Backup_{today_tag}.db"

        dest_file = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".db",
            filetypes=[("SQLite Database Files", "*.db"), ("All Files", "*.*")],
            title="Choose Backup Destination",
            parent=self
        )

        if not dest_file:
            return

        success = database.backup_database(dest_file)
        if success:
            messagebox.showinfo("Backup Successful", f"Database successfully backed up to:\n{dest_file}", parent=self)
        else:
            messagebox.showerror("Backup Failed", "Unable to create backup copy of database.", parent=self)

    def restore_database(self):
        confirm = messagebox.askyesno(
            "Confirm Database Restore",
            "Restoring a database will replace all current vehicle, fuel, service, and expense records with the backup file.\n\n"
            "An automatic safety backup of your current database will be saved before restore.\n\n"
            "Do you wish to proceed?",
            icon="warning",
            parent=self
        )
        if not confirm:
            return

        source_file = filedialog.askopenfilename(
            filetypes=[("SQLite Database Files", "*.db;*.sqlite;*.sqlite3"), ("All Files", "*.*")],
            title="Select VehicleCare Database Backup to Restore",
            parent=self
        )

        if not source_file:
            return

        success, msg = database.restore_database(source_file)
        if success:
            messagebox.showinfo("Restore Successful", f"Database restored successfully!\n{msg}", parent=self)
            self.refresh_data()
            if self.on_settings_changed:
                self.on_settings_changed()
        else:
            messagebox.showerror("Restore Failed", f"Could not restore database:\n{msg}", parent=self)

    def load_demo_data(self):
        confirm = messagebox.askyesno(
            "Load Sample Demo Data",
            "This action will insert sample vehicles (Car & Bike), realistic fuel purchases, service history, and expenses for demonstration purposes.\n\n"
            "Would you like to load demo records?",
            icon="question",
            parent=self
        )
        if confirm:
            try:
                database.load_demo_data()
                messagebox.showinfo("Demo Data Loaded", "Sample vehicles, fuel logs, and service records have been added successfully!", parent=self)
                if self.on_settings_changed:
                    self.on_settings_changed()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load demo data: {str(e)}", parent=self)

    def reset_all_data(self):
        confirm = messagebox.askyesno(
            "Reset Database",
            "WARNING: This will permanently delete ALL vehicles, fuel records, service history, and expenses!\n\n"
            "Are you absolutely certain you want to proceed?",
            icon="warning",
            parent=self
        )
        if confirm:
            database.clear_all_data()
            messagebox.showinfo("Database Reset", "All records have been cleared from the database.", parent=self)
            if self.on_settings_changed:
                self.on_settings_changed()
