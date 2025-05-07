import tkinter as tk
from tkinter import ttk

def apply_style():
    """Apply modern style to the application"""
    style = ttk.Style()
    
    # Color palette
    PRIMARY = "#3A59D1"      # Deep blue - main accent
    SECONDARY = "#3D90D7"    # Medium blue - secondary accent
    TERTIARY = "#7AC6D2"     # Light blue - highlights
    BACKGROUND = "#B5FCCD"   # Mint - background
    TEXT = "#333333"         # Dark gray - text
    
    # Configure main theme
    style.configure(".",
        background=BACKGROUND,
        foreground=TEXT,
        font=("Segoe UI", 9)
    )
    
    # Frame style
    style.configure("Modern.TFrame",
        background="#ffffff"
    )
    
    # Label style
    style.configure("Modern.TLabel",
        background="#ffffff",
        foreground=TEXT,
        padding=(5, 5),
        font=("Segoe UI", 9)
    )
    
    # Entry style
    style.configure("Modern.TEntry",
        fieldbackground="#ffffff",
        padding=(5, 5)
    )
    
    # Button style
    style.configure("Modern.TButton",
        background=PRIMARY,
        foreground="#ffffff",
        padding=(10, 5),
        font=("Segoe UI", 9, "bold")
    )
    
    style.map("Modern.TButton",
        background=[
            ("pressed", TERTIARY),
            ("active", SECONDARY),
            ("disabled", TERTIARY)
        ],
        foreground=[
            ("disabled", "#ffffff")
        ],
        relief=[
            ("pressed", "sunken"),
            ("!pressed", "raised")
        ]
    )
    
    # Progress bar style
    style.configure("Modern.Horizontal.TProgressbar",
        background=PRIMARY,
        troughcolor="#ffffff",
        borderwidth=0,
        thickness=10
    )
    
    # Combobox style
    style.configure("Modern.TCombobox",
        background="#ffffff",
        fieldbackground="#ffffff",
        selectbackground=PRIMARY,
        selectforeground="#ffffff",
        padding=(5, 5)
    )
    
    # Radio button style
    style.configure("Modern.TRadiobutton",
        background="#ffffff",
        foreground=TEXT,
        font=("Segoe UI", 9)
    )
    style.map("Modern.TRadiobutton",
        background=[("active", BACKGROUND)],
        foreground=[("active", PRIMARY)]
    )
    
    # LabelFrame style
    style.configure("Modern.TLabelframe",
        background="#ffffff",
        foreground=TEXT,
        padding=10
    )
    style.configure("Modern.TLabelframe.Label",
        background="#ffffff",
        foreground=PRIMARY,
        font=("Segoe UI", 9, "bold")
    )

class ModernButton(ttk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, style="Modern.TButton", **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, e):
        """Handle mouse enter event"""
        if str(self["state"]) != "disabled":
            self.configure(cursor="hand2")
    
    def _on_leave(self, e):
        """Handle mouse leave event"""
        if str(self["state"]) != "disabled":
            self.configure(cursor="")

def create_custom_widgets():
    """Create custom widget styles"""
    return {
        "ModernButton": ModernButton
    }
