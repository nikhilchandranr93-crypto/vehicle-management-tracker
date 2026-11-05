"""
ui_common.py - Common UI Design System, Styles, and Reusable Widgets for VehicleCare.
Provides colors, fonts, custom widget wrappers (cards, tables, forms, buttons)
to guarantee a cohesive, modern desktop feel.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List

# =====================================================================
# DESIGN SYSTEM COLOR PALETTE
# =====================================================================
COLORS = {
    "bg_main": "#F3F5F9",
    "bg_sidebar": "#172238",
    "bg_sidebar_hover": "#233352",
    "bg_sidebar_active": "#1E3A8A",
    "card_bg": "#FFFFFF",
    "border": "#E0E5ED",
    "border_light": "#EDF1F7",
    "text_main": "#202B3C",
    "text_secondary": "#7B8798",
    "text_muted": "#94A3B8",
    "text_white": "#FFFFFF",
    "primary": "#3478F6",
    "primary_hover": "#2563EB",
    "primary_light": "#EFF6FF",
    "success": "#10B981",
    "success_light": "#ECFDF5",
    "warning": "#F59E0B",
    "warning_light": "#FFFBEB",
    "danger": "#EF4444",
    "danger_light": "#FEF2F2",
    "info": "#0284C7",
    "info_light": "#F0F9FF"
}

# =====================================================================
# TYPOGRAPHY
# =====================================================================
FONT_FAMILY = "Segoe UI"
FALLBACK_FONT = "Helvetica"

FONTS = {
    "title": (FONT_FAMILY, 18, "bold"),
    "subtitle": (FONT_FAMILY, 10),
    "header": (FONT_FAMILY, 13, "bold"),
    "subheader": (FONT_FAMILY, 11, "bold"),
    "body": (FONT_FAMILY, 10),
    "body_bold": (FONT_FAMILY, 10, "bold"),
    "small": (FONT_FAMILY, 9),
    "small_bold": (FONT_FAMILY, 9, "bold"),
    "card_title": (FONT_FAMILY, 10, "bold"),
    "card_value": (FONT_FAMILY, 20, "bold"),
    "button": (FONT_FAMILY, 10, "bold"),
    "sidebar": (FONT_FAMILY, 10),
    "sidebar_active": (FONT_FAMILY, 10, "bold"),
}


def setup_ttk_styles(root: tk.Tk) -> ttk.Style:
    """Configure modern ttk styles for Treeview, Buttons, Frames, and Scrollbars."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Treeview Styling
    style.configure(
        "Treeview",
        background=COLORS["card_bg"],
        foreground=COLORS["text_main"],
        fieldbackground=COLORS["card_bg"],
        font=FONTS["body"],
        rowheight=32,
        borderwidth=0
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["primary_light"])],
        foreground=[("selected", COLORS["primary"])]
    )

    style.configure(
        "Treeview.Heading",
        background="#F8FAFC",
        foreground=COLORS["text_secondary"],
        font=FONTS["small_bold"],
        relief="flat",
        borderwidth=0,
        padding=[10, 8]
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#F1F5F9")],
        foreground=[("active", COLORS["text_main"])]
    )

    # Scrollbars
    style.configure(
        "Vertical.TScrollbar",
        gripcount=0,
        background=COLORS["border"],
        troughcolor=COLORS["bg_main"],
        bordercolor=COLORS["bg_main"],
        arrowcolor=COLORS["text_secondary"],
        relief="flat"
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["card_bg"],
        background=COLORS["card_bg"],
        foreground=COLORS["text_main"],
        font=FONTS["body"],
        arrowsize=14,
        padding=5
    )

    return style


# =====================================================================
# FORMATTING HELPERS
# =====================================================================

def format_currency(amount: Optional[float], currency: str = "₹") -> str:
    """Format numeric amount into display string with currency."""
    if amount is None:
        return f"{currency} 0.00"
    return f"{currency} {amount:,.2f}"


def format_odometer(odo: Optional[float]) -> str:
    """Format odometer value with comma separator and km suffix."""
    if odo is None:
        return "0 km"
    return f"{odo:,.0f} km"


# =====================================================================
# REUSABLE WIDGETS
# =====================================================================

class StatCard(tk.Frame):
    """
    A summary card component with top accent bar, category title,
    prominent numeric value, and descriptive footer.
    """
    def __init__(self, parent, title: str, value: str, subtitle: str = "",
                 accent_color: str = COLORS["primary"], **kwargs):
        super().__init__(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"],
                         highlightthickness=1, bd=0, padx=16, pady=14, **kwargs)

        # Top accent indicator line
        accent_strip = tk.Frame(self, bg=accent_color, height=3)
        accent_strip.pack(fill="x", side="top", pady=(0, 10))

        # Title Label
        self.lbl_title = tk.Label(
            self,
            text=title.upper(),
            font=FONTS["card_title"],
            fg=COLORS["text_secondary"],
            bg=COLORS["card_bg"],
            anchor="w"
        )
        self.lbl_title.pack(fill="x")

        # Value Label
        self.lbl_value = tk.Label(
            self,
            text=value,
            font=FONTS["card_value"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"],
            anchor="w"
        )
        self.lbl_value.pack(fill="x", pady=(4, 2))

        # Subtitle Label
        self.lbl_subtitle = tk.Label(
            self,
            text=subtitle,
            font=FONTS["small"],
            fg=COLORS["text_muted"],
            bg=COLORS["card_bg"],
            anchor="w"
        )
        self.lbl_subtitle.pack(fill="x")

    def update_data(self, value: str, subtitle: Optional[str] = None):
        """Update displayed card figures."""
        self.lbl_value.config(text=value)
        if subtitle is not None:
            self.lbl_subtitle.config(text=subtitle)


class StyledButton(tk.Button):
    """Modern flat button with clean hover states and rounded feel."""
    def __init__(self, parent, text: str, command=None, variant: str = "primary", **kwargs):
        if variant == "primary":
            bg = COLORS["primary"]
            fg = COLORS["text_white"]
            active_bg = COLORS["primary_hover"]
        elif variant == "secondary":
            bg = "#E2E8F0"
            fg = COLORS["text_main"]
            active_bg = "#CBD5E1"
        elif variant == "danger":
            bg = COLORS["danger"]
            fg = COLORS["text_white"]
            active_bg = "#DC2626"
        elif variant == "success":
            bg = COLORS["success"]
            fg = COLORS["text_white"]
            active_bg = "#059669"
        elif variant == "outline":
            bg = COLORS["card_bg"]
            fg = COLORS["primary"]
            active_bg = COLORS["primary_light"]
        else:
            bg = COLORS["border"]
            fg = COLORS["text_main"]
            active_bg = "#CBD5E1"

        super().__init__(
            parent,
            text=text,
            command=command,
            font=FONTS["button"],
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=7,
            **kwargs
        )
        self._default_bg = bg
        self._hover_bg = active_bg
        self.bind("<Enter>", lambda e: self.config(bg=self._hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self._default_bg))


class CardContainer(tk.Frame):
    """Standard white container card with subtle border and padding."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=COLORS["card_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
            **kwargs
        )


class TableView(tk.Frame):
    """
    Enhanced ttk.Treeview wrapper with header, integrated vertical scrollbar,
    striped rows, and click handling.
    """
    def __init__(self, parent, columns: List[Dict[str, Any]], on_select: Optional[Callable] = None, **kwargs):
        super().__init__(parent, bg=COLORS["card_bg"], **kwargs)
        self.columns_meta = columns
        self.on_select = on_select

        col_ids = [c["id"] for c in columns]
        self.tree = ttk.Treeview(self, columns=col_ids, show="headings", selectmode="browse")

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        for col in columns:
            cid = col["id"]
            heading = col.get("name", cid.title())
            width = col.get("width", 100)
            anchor = col.get("anchor", "w")
            self.tree.heading(cid, text=heading, anchor=anchor)
            self.tree.column(cid, width=width, anchor=anchor, minwidth=60)

        self.tree.tag_configure("even", background=COLORS["card_bg"])
        self.tree.tag_configure("odd", background="#F8FAFC")

        self.tree.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        if self.on_select:
            self.tree.bind("<<TreeviewSelect>>", self._handle_selection)

    def _handle_selection(self, event):
        selected_item = self.get_selected_row()
        if selected_item and self.on_select:
            self.on_select(selected_item)

    def clear(self):
        """Clear all rows."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def insert_rows(self, rows: List[List[Any]], ids: Optional[List[Any]] = None):
        """Populate treeview with rows and alternate coloring tags."""
        self.clear()
        for idx, row in enumerate(rows):
            tag = "even" if idx % 2 == 0 else "odd"
            iid = str(ids[idx]) if ids and idx < len(ids) else None
            if iid is not None:
                self.tree.insert("", "end", iid=iid, values=row, tags=(tag,))
            else:
                self.tree.insert("", "end", values=row, tags=(tag,))

    def get_selected_id(self) -> Optional[str]:
        """Return selected item iid."""
        selection = self.tree.selection()
        return selection[0] if selection else None

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Return dict of column values for selected item."""
        selection = self.tree.selection()
        if not selection:
            return None
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        res = {"_id": item_id}
        for col, val in zip(self.columns_meta, values):
            res[col["id"]] = val
        return res


class FormDialog(tk.Toplevel):
    """
    Standard modal dialog with clean styling, title, entry form grid,
    and Save/Cancel buttons.
    """
    def __init__(self, parent, title: str, width: int = 500, height: int = 450):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(420, 360)
        self.configure(bg=COLORS["bg_main"])
        self.transient(parent)
        self.grab_set()

        # Center dialog relative to parent
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self.result = None

        # Dialog header
        header_frame = tk.Frame(self, bg=COLORS["card_bg"], padx=20, pady=14,
                                highlightbackground=COLORS["border"], highlightthickness=1)
        header_frame.pack(fill="x", side="top")
        tk.Label(
            header_frame,
            text=title,
            font=FONTS["header"],
            fg=COLORS["text_main"],
            bg=COLORS["card_bg"]
        ).pack(side="left")

        # Scrollable / padded body
        self.body_card = tk.Frame(self, bg=COLORS["card_bg"], padx=20, pady=16,
                                  highlightbackground=COLORS["border"], highlightthickness=1)
        self.body_card.pack(fill="both", expand=True, padx=20, pady=16)

        # Footer with action buttons
        footer_frame = tk.Frame(self, bg=COLORS["bg_main"], padx=20, pady=12)
        footer_frame.pack(fill="x", side="bottom")

        self.btn_cancel = StyledButton(footer_frame, text="Cancel", variant="secondary", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_save = StyledButton(footer_frame, text="Save Record", variant="primary", command=self.on_submit)
        self.btn_save.pack(side="right")

    def on_submit(self):
        """Override in subclasses to perform validation and save."""
        pass
