# -*- coding: utf-8 -*-
"""
Hyperthermia MINT — GUI Runner V2
Full-featured simulation workbench: code editor, image viewer, CSV table,
interactive charting (line/scatter/bar/heatmap), GIF animation, and runner.
White/light professional theme.
"""
import os
import sys
import re
import csv
import time
import signal
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import threading
import subprocess
import queue

# Optional imports with graceful fallback
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ======================================================================
# Constants
# ======================================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TITLE = "Hyperthermia MINT — Simulation Workbench"

# --- Light Professional Theme ---
BG_WHITE = "#FFFFFF"
BG_PANEL = "#F5F5F5"
BG_HOVER = "#E8F0FE"
BG_EDITOR = "#FAFAFA"
BG_TERMINAL = "#F8F8F8"
BG_SELECTED = "#D2E3FC"
FG_TEXT = "#333333"
FG_DIM = "#888888"
FG_DARK = "#1A1A1A"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
BORDER = "#D0D0D0"
BORDER_LIGHT = "#E5E5E5"
SUCCESS_COLOR = "#16A34A"
ERROR_COLOR = "#DC2626"
WARNING_COLOR = "#D97706"

# Syntax colors (light theme)
SYN_KEYWORD = "#7C3AED"
SYN_STRING = "#16A34A"
SYN_COMMENT = "#9CA3AF"
SYN_NUMBER = "#EA580C"
SYN_BUILTIN = "#2563EB"
SYN_OPERATOR = "#DC2626"

# File type icons
ICON_MAP = {
    ".py": "🐍", ".txt": "📄", ".md": "📝", ".csv": "📊",
    ".png": "🖼️", ".gif": "🎬", ".jpg": "🖼️", ".jpeg": "🖼️",
    ".log": "📋", ".json": "📦", ".xyz": "🔬",
}


# ======================================================================
# Main Application
# ======================================================================
class HyperthermiaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(TITLE)
        self.root.geometry("1500x900")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG_WHITE)

        # State
        self.tabs = {}  # tab_id -> {type, filepath, widget, ...}
        self.tab_counter = 0
        self.process = None
        self.output_queue = queue.Queue()
        self.is_running = False
        self.run_start_time = None

        # Fonts
        self.code_font = tkfont.Font(family="Consolas", size=11)
        self.ui_font = tkfont.Font(family="Segoe UI", size=10)
        self.ui_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        self.terminal_font = tkfont.Font(family="Consolas", size=10)
        self.header_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        # Style
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        # Build UI
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        # Bindings
        self.root.bind("<Control-s>", lambda e: self._save_current_tab())
        self.root.bind("<Control-o>", lambda e: self._open_file_dialog())
        self.root.bind("<F5>", lambda e: self._run_simulation())
        self.root.bind("<Control-Shift-P>", lambda e: self._stop_simulation())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Load defaults
        default_file = os.path.join(ROOT_DIR, "auto_run.py")
        if os.path.exists(default_file):
            self._open_file(default_file)
        self._refresh_file_tree()
        self._poll_output()

    # ==================================================================
    # Styles
    # ==================================================================
    def _configure_styles(self):
        s = self.style
        s.configure("White.TFrame", background=BG_WHITE)
        s.configure("Panel.TFrame", background=BG_PANEL)
        s.configure("White.TLabel", background=BG_WHITE, foreground=FG_TEXT, font=self.ui_font)
        s.configure("Panel.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=self.ui_font)
        s.configure("Header.TLabel", background=BG_PANEL, foreground=FG_DARK, font=self.header_font)
        s.configure("Dim.TLabel", background=BG_WHITE, foreground=FG_DIM, font=self.small_font)
        s.configure("Accent.TLabel", background=BG_PANEL, foreground=ACCENT, font=self.ui_bold)

        s.configure("Toolbar.TButton", background=BG_PANEL, foreground=FG_TEXT,
                     font=self.ui_font, borderwidth=1, relief="flat", padding=(10, 4))
        s.map("Toolbar.TButton",
              background=[("active", BG_HOVER), ("pressed", BG_SELECTED)])

        s.configure("Explorer.Treeview",
                     background=BG_WHITE, foreground=FG_TEXT, fieldbackground=BG_WHITE,
                     font=self.small_font, borderwidth=0, rowheight=24)
        s.map("Explorer.Treeview",
              background=[("selected", BG_SELECTED)],
              foreground=[("selected", ACCENT)])
        s.configure("Explorer.Treeview.Heading",
                     background=BG_PANEL, foreground=FG_DIM, font=self.small_font)

        s.configure("CSV.Treeview",
                     background=BG_WHITE, foreground=FG_TEXT, fieldbackground=BG_WHITE,
                     font=self.small_font, borderwidth=0, rowheight=22)
        s.map("CSV.Treeview",
              background=[("selected", BG_SELECTED)],
              foreground=[("selected", ACCENT)])
        s.configure("CSV.Treeview.Heading",
                     background=BG_PANEL, foreground=FG_DARK, font=self.small_font, relief="flat")

        s.configure("TNotebook", background=BG_PANEL, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_TEXT,
                     font=self.ui_font, padding=(12, 4))
        s.map("TNotebook.Tab",
              background=[("selected", BG_WHITE)],
              foreground=[("selected", ACCENT)])

    # ==================================================================
    # Toolbar
    # ==================================================================
    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg=BG_PANEL, height=40, bd=0,
                           highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        left = tk.Frame(toolbar, bg=BG_PANEL)
        left.pack(side=tk.LEFT, padx=6, pady=4)

        for text, cmd in [("📂 Open", self._open_file_dialog),
                          ("💾 Save", self._save_current_tab),
                          ("🔄 Refresh", self._refresh_file_tree)]:
            b = tk.Button(left, text=text, bg=BG_PANEL, fg=FG_TEXT, font=self.ui_font,
                          relief="flat", bd=0, padx=8, pady=2, cursor="hand2", command=cmd,
                          activebackground=BG_HOVER)
            b.pack(side=tk.LEFT, padx=2)

        sep = tk.Frame(left, width=1, bg=BORDER, height=24)
        sep.pack(side=tk.LEFT, padx=8, fill=tk.Y)

        tk.Label(left, text="Run:", bg=BG_PANEL, fg=FG_DIM, font=self.small_font).pack(side=tk.LEFT, padx=(4, 2))
        self.run_target_var = tk.StringVar(value="auto_run.py")
        combo = ttk.Combobox(left, textvariable=self.run_target_var,
                              values=["auto_run.py", "run.py", "Current File"],
                              width=14, state="readonly", font=self.small_font)
        combo.pack(side=tk.LEFT, padx=2)

        right = tk.Frame(toolbar, bg=BG_PANEL)
        right.pack(side=tk.RIGHT, padx=6, pady=4)

        self.layout_btn = tk.Button(right, text="Layout ▾", bg=BG_PANEL, fg=FG_TEXT,
                                     font=self.ui_font, relief="flat", padx=8, pady=2,
                                     cursor="hand2", bd=0, activebackground=BG_HOVER)
        self.layout_btn.pack(side=tk.RIGHT, padx=(10, 2))

        self.layout_menu = tk.Menu(self.root, tearoff=0, bg=BG_WHITE, fg=FG_TEXT,
                                   activebackground=BG_SELECTED, font=self.small_font)
        
        self.show_terminal_var = tk.BooleanVar(value=True)
        self.show_explorer_var = tk.BooleanVar(value=True)
        
        self.layout_menu.add_checkbutton(label="Bottom Panel (Terminal)", 
                                         variable=self.show_terminal_var,
                                         command=self._toggle_layout)
        self.layout_menu.add_checkbutton(label="Right Sidebar (Explorer)", 
                                         variable=self.show_explorer_var,
                                         command=self._toggle_layout)
                                         
        self.layout_btn.config(command=lambda: self.layout_menu.post(
            self.layout_btn.winfo_rootx(), 
            self.layout_btn.winfo_rooty() + self.layout_btn.winfo_height()))

        self.stop_btn = tk.Button(right, text="⏹ Stop", bg="#FEE2E2", fg=ERROR_COLOR,
                                   font=self.ui_bold, relief="flat", padx=12, pady=2,
                                   command=self._stop_simulation, state=tk.DISABLED,
                                   activebackground="#FECACA", cursor="hand2", bd=0)
        self.stop_btn.pack(side=tk.RIGHT, padx=2)

        self.run_btn = tk.Button(right, text="▶ Run", bg="#DCFCE7", fg=SUCCESS_COLOR,
                                  font=self.ui_bold, relief="flat", padx=14, pady=2,
                                  command=self._run_simulation,
                                  activebackground="#BBF7D0", cursor="hand2", bd=0)
        self.run_btn.pack(side=tk.RIGHT, padx=2)

    def _toggle_layout(self):
        if self.show_terminal_var.get():
            if str(self.terminal_frame) not in [str(p) for p in self.left_pane.panes()]:
                self.left_pane.add(self.terminal_frame, weight=1)
        else:
            if str(self.terminal_frame) in [str(p) for p in self.left_pane.panes()]:
                self.left_pane.forget(self.terminal_frame)
                
        if self.show_explorer_var.get():
            if str(self.explorer_frame) not in [str(p) for p in self.main_pane.panes()]:
                self.main_pane.add(self.explorer_frame, weight=1)
        else:
            if str(self.explorer_frame) in [str(p) for p in self.main_pane.panes()]:
                self.main_pane.forget(self.explorer_frame)

    # ==================================================================
    # Main Area
    # ==================================================================
    def _build_main_area(self):
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.left_pane = ttk.PanedWindow(self.main_pane, orient=tk.VERTICAL)
        self.main_pane.add(self.left_pane, weight=4)

        # -- Tab Notebook --
        nb_frame = tk.Frame(self.left_pane, bg=BG_WHITE)
        self.left_pane.add(nb_frame, weight=3)

        self.notebook = ttk.Notebook(nb_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        # Left-click to close tab
        self.notebook.bind("<Button-1>", self._on_tab_click_left)
        # Middle-click to close tab
        self.notebook.bind("<Button-2>", self._close_tab_click)

        # -- Terminal --
        self.terminal_frame = tk.Frame(self.left_pane, bg=BG_TERMINAL, bd=0,
                                   highlightbackground=BORDER, highlightthickness=1)
        self.left_pane.add(self.terminal_frame, weight=1)

        terminal_header = tk.Frame(self.terminal_frame, bg=BG_PANEL, height=26)
        terminal_header.pack(fill=tk.X)
        terminal_header.pack_propagate(False)
        tk.Label(terminal_header, text="⌘ Terminal Output", bg=BG_PANEL, fg=FG_DIM,
                 font=self.small_font, padx=8).pack(side=tk.LEFT)
        tk.Button(terminal_header, text="Clear", bg=BG_PANEL, fg=FG_DIM,
                   font=self.small_font, relief="flat", bd=0, padx=6,
                   command=self._clear_terminal, cursor="hand2",
                   activebackground=BG_HOVER).pack(side=tk.RIGHT, padx=4)

        t_scroll = tk.Scrollbar(self.terminal_frame, orient=tk.VERTICAL)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal = tk.Text(self.terminal_frame, bg=BG_TERMINAL, fg=FG_TEXT,
                                 font=self.terminal_font, state=tk.DISABLED, bd=0,
                                 highlightthickness=0, wrap=tk.WORD, padx=8, pady=4,
                                 yscrollcommand=t_scroll.set)
        self.terminal.pack(fill=tk.BOTH, expand=True)
        t_scroll.config(command=self.terminal.yview)
        for tag, color in [("info", FG_TEXT), ("success", SUCCESS_COLOR),
                           ("error", ERROR_COLOR), ("warning", WARNING_COLOR),
                           ("dim", FG_DIM), ("accent", ACCENT)]:
            self.terminal.tag_configure(tag, foreground=color)

        # -- File Explorer --
        self.explorer_frame = tk.Frame(self.main_pane, bg=BG_WHITE, bd=0,
                                   highlightbackground=BORDER, highlightthickness=1)
        self.main_pane.add(self.explorer_frame, weight=1)

        exp_header = tk.Frame(self.explorer_frame, bg=BG_PANEL, height=26)
        exp_header.pack(fill=tk.X)
        exp_header.pack_propagate(False)
        tk.Label(exp_header, text="📁 Explorer", bg=BG_PANEL, fg=FG_DIM,
                 font=self.small_font, padx=8).pack(side=tk.LEFT)
        
        self.sort_var = tk.StringVar(value="Date (Newest)")
        sort_combo = ttk.Combobox(exp_header, textvariable=self.sort_var,
                                  values=["Date (Newest)", "Name"],
                                  width=12, state="readonly", font=self.small_font)
        sort_combo.pack(side=tk.LEFT, padx=4)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_file_tree())
        
        tk.Button(exp_header, text="↻", bg=BG_PANEL, fg=FG_DIM,
                   font=self.small_font, relief="flat", bd=0, padx=6,
                   command=self._refresh_file_tree, cursor="hand2",
                   activebackground=BG_HOVER).pack(side=tk.RIGHT, padx=4)

        tree_scroll = tk.Scrollbar(self.explorer_frame, orient=tk.VERTICAL)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree = ttk.Treeview(self.explorer_frame, style="Explorer.Treeview",
                                       show="tree", selectmode="browse",
                                       yscrollcommand=tree_scroll.set)
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.file_tree.yview)
        self.file_tree.bind("<Double-1>", self._on_tree_double_click)
        self.file_tree.bind("<Button-3>", self._on_tree_right_click)

        # Context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0, bg=BG_WHITE, fg=FG_TEXT,
                                activebackground=BG_SELECTED, font=self.small_font)
        self.ctx_menu.add_command(label="Open", command=self._ctx_open)
        self.ctx_menu.add_command(label="Copy Path", command=self._ctx_copy_path)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Delete", command=self._ctx_delete)
        self._ctx_path = None

    # ==================================================================
    # Status Bar
    # ==================================================================
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=BG_PANEL, height=26,
                       highlightbackground=BORDER, highlightthickness=1)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)

        self.status_label = tk.Label(sb, text="Ready", bg=BG_PANEL, fg=FG_TEXT,
                                      font=self.small_font, padx=8, anchor="w")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_indicator = tk.Label(sb, text="● Idle", bg=BG_PANEL, fg=SUCCESS_COLOR,
                                          font=self.small_font, padx=8)
        self.status_indicator.pack(side=tk.RIGHT)

        self.timer_label = tk.Label(sb, text="", bg=BG_PANEL, fg=FG_DIM,
                                     font=self.small_font, padx=8)
        self.timer_label.pack(side=tk.RIGHT)

    # ==================================================================
    # Tab Management
    # ==================================================================
    def _create_tab(self, title, tab_type, filepath=None):
        """Create a new tab and return its frame + tab_id."""
        # Check if file already open
        if filepath:
            for tid, info in self.tabs.items():
                if info.get("filepath") == filepath:
                    self.notebook.select(info["frame"])
                    return tid, info["frame"]

        self.tab_counter += 1
        tid = f"tab_{self.tab_counter}"

        frame = tk.Frame(self.notebook, bg=BG_WHITE)
        self.notebook.add(frame, text=f"  {title}  ✕")
        self.notebook.select(frame)

        self.tabs[tid] = {"type": tab_type, "filepath": filepath,
                          "frame": frame, "title": title, "modified": False}
        return tid, frame

    def _on_tab_click_left(self, event):
        """Close tab on left-click on the 'X'."""
        try:
            element = self.notebook.identify(event.x, event.y)
            if "label" in element:
                idx = self.notebook.index(f"@{event.x},{event.y}")
                bbox = self.notebook.bbox(idx)
                # If click is within the rightmost 25 pixels of the tab
                if event.x > bbox[0] + bbox[2] - 25:
                    tab_frame = self.notebook.nametowidget(self.notebook.tabs()[idx])
                    self.root.after(10, lambda: self._close_tab_by_frame(tab_frame))
        except Exception:
            pass

    def _close_tab_click(self, event):
        """Close tab on middle-click."""
        try:
            idx = self.notebook.index(f"@{event.x},{event.y}")
            tab_frame = self.notebook.nametowidget(self.notebook.tabs()[idx])
            self._close_tab_by_frame(tab_frame)
        except Exception:
            pass

    def _close_tab_by_frame(self, frame):
        """Close a specific tab."""
        tid = None
        for t, info in self.tabs.items():
            if info["frame"] == frame:
                tid = t
                break
        if tid:
            info = self.tabs[tid]
            if info.get("modified") and info["type"] == "code":
                ans = messagebox.askyesnocancel("Save?", f"Save {info['title']}?")
                if ans is True:
                    self._save_tab(tid)
                elif ans is None:
                    return
            # Clean up matplotlib figures
            if "figure" in info:
                plt.close(info["figure"])
            self.notebook.forget(info["frame"])
            del self.tabs[tid]

    def _get_current_tab(self):
        """Return current tab id and info."""
        try:
            current_frame = self.notebook.nametowidget(self.notebook.select())
            for tid, info in self.tabs.items():
                if info["frame"] == current_frame:
                    return tid, info
        except Exception:
            pass
        return None, None

    def _on_tab_changed(self, event=None):
        tid, info = self._get_current_tab()
        if info:
            self._set_status(info.get("filepath", info["title"]))

    # ==================================================================
    # Code Editor Tab
    # ==================================================================
    def _open_code_tab(self, filepath, content):
        filename = os.path.basename(filepath)
        tid, frame = self._create_tab(filename, "code", filepath)

        # Check if already created
        if "editor" in self.tabs[tid]:
            return

        # Tab bar info
        info_bar = tk.Frame(frame, bg=BG_PANEL, height=24)
        info_bar.pack(fill=tk.X)
        info_bar.pack_propagate(False)
        path_label = tk.Label(info_bar, text=filepath, bg=BG_PANEL, fg=FG_DIM,
                               font=self.small_font, padx=8)
        path_label.pack(side=tk.LEFT)
        lc_label = tk.Label(info_bar, text="Ln 1, Col 1", bg=BG_PANEL, fg=FG_DIM,
                             font=self.small_font, padx=8)
        lc_label.pack(side=tk.RIGHT)

        # Editor area
        editor_container = tk.Frame(frame, bg=BG_EDITOR)
        editor_container.pack(fill=tk.BOTH, expand=True)

        line_nums = tk.Text(editor_container, width=5, bg=BG_PANEL, fg=FG_DIM,
                             font=self.code_font, state=tk.DISABLED, bd=0,
                             highlightthickness=0, padx=4, pady=4,
                             selectbackground=BG_PANEL, cursor="arrow", takefocus=0)
        line_nums.pack(side=tk.LEFT, fill=tk.Y)

        v_scroll = tk.Scrollbar(editor_container, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        editor = tk.Text(editor_container, bg=BG_EDITOR, fg=FG_TEXT, font=self.code_font,
                          insertbackground=ACCENT, selectbackground=BG_SELECTED,
                          selectforeground=FG_TEXT, bd=0, highlightthickness=0,
                          wrap=tk.NONE, undo=True, padx=8, pady=4, tabs="4c")
        editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def on_scroll(*args):
            editor.yview(*args)
            line_nums.yview(*args)

        def on_editor_yscroll(*args):
            v_scroll.set(*args)
            line_nums.yview_moveto(args[0])

        v_scroll.config(command=on_scroll)
        editor.config(yscrollcommand=on_editor_yscroll)

        h_scroll = tk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scroll.pack(fill=tk.X)
        h_scroll.config(command=editor.xview)
        editor.config(xscrollcommand=h_scroll.set)

        editor.insert("1.0", content)
        editor.edit_reset()

        # Syntax tags
        for tag, color in [("keyword", SYN_KEYWORD), ("string", SYN_STRING),
                           ("comment", SYN_COMMENT), ("number", SYN_NUMBER),
                           ("builtin", SYN_BUILTIN), ("operator", SYN_OPERATOR)]:
            editor.tag_configure(tag, foreground=color)

        def update_line_nums(event=None):
            line_nums.config(state=tk.NORMAL)
            line_nums.delete("1.0", tk.END)
            count = int(editor.index("end-1c").split(".")[0])
            line_nums.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
            line_nums.config(state=tk.DISABLED)

        def update_cursor(event=None):
            try:
                pos = editor.index(tk.INSERT)
                ln, col = pos.split(".")
                lc_label.config(text=f"Ln {ln}, Col {int(col)+1}")
            except Exception:
                pass

        def on_change(event=None):
            self.tabs[tid]["modified"] = True
            self.notebook.tab(frame, text=f"  ● {filename}  ✕")
            update_line_nums()
            self._apply_syntax(editor)
            update_cursor()

        editor.bind("<KeyRelease>", on_change)
        editor.bind("<ButtonRelease-1>", update_cursor)

        self.tabs[tid]["editor"] = editor
        self.tabs[tid]["line_nums"] = line_nums
        self.tabs[tid]["lc_label"] = lc_label

        update_line_nums()
        self._apply_syntax(editor)

    def _apply_syntax(self, editor):
        content = editor.get("1.0", tk.END)
        for tag in ("keyword", "string", "comment", "number", "builtin"):
            editor.tag_remove(tag, "1.0", tk.END)

        kw = r'\b(def|class|import|from|return|if|elif|else|for|while|in|not|and|or|is|try|except|finally|with|as|yield|lambda|pass|break|continue|raise|True|False|None|global|nonlocal|assert|del|async|await)\b'
        bi = r'\b(print|range|len|int|float|str|list|dict|tuple|set|open|os|sys|time|re|self|super|enumerate|zip|map|filter|type|isinstance|max|min|sum|abs|sorted)\b'

        for match in re.finditer(kw, content):
            editor.tag_add("keyword", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(bi, content):
            editor.tag_add("builtin", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', content):
            editor.tag_add("string", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(r'#[^\n]*', content):
            editor.tag_add("comment", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        for match in re.finditer(r'\b\d+\.?\d*(?:[eE][+-]?\d+)?\b', content):
            editor.tag_add("number", f"1.0+{match.start()}c", f"1.0+{match.end()}c")
        editor.tag_raise("string")
        editor.tag_raise("comment")

    # ==================================================================
    # Image Viewer Tab (PNG)
    # ==================================================================
    def _open_image_tab(self, filepath):
        if not HAS_PIL:
            messagebox.showerror("Missing Pillow", "pip install Pillow required for image viewing.")
            return

        filename = os.path.basename(filepath)
        tid, frame = self._create_tab(filename, "image", filepath)
        if "canvas" in self.tabs[tid]:
            return

        toolbar = tk.Frame(frame, bg=BG_PANEL, height=32)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        pil_img = Image.open(filepath)
        self.tabs[tid]["pil_image"] = pil_img
        self.tabs[tid]["zoom"] = 1.0

        tk.Label(toolbar, text=f"{pil_img.width}×{pil_img.height}px", bg=BG_PANEL,
                 fg=FG_DIM, font=self.small_font, padx=8).pack(side=tk.LEFT)

        def set_zoom(z):
            self.tabs[tid]["zoom"] = z
            render_image()

        for text, z in [("Fit", "fit"), ("100%", 1.0), ("50%", 0.5), ("200%", 2.0)]:
            tk.Button(toolbar, text=text, bg=BG_PANEL, fg=FG_TEXT, font=self.small_font,
                       relief="flat", bd=0, padx=8, cursor="hand2",
                       command=lambda zz=z: set_zoom(zz),
                       activebackground=BG_HOVER).pack(side=tk.LEFT, padx=2)

        canvas = tk.Canvas(frame, bg=BG_WHITE, bd=0, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        self.tabs[tid]["canvas"] = canvas

        def render_image(event=None):
            img = self.tabs[tid]["pil_image"]
            z = self.tabs[tid]["zoom"]
            if z == "fit":
                cw, ch = canvas.winfo_width(), canvas.winfo_height()
                if cw < 10:
                    cw, ch = 800, 600
                ratio = min(cw / img.width, ch / img.height, 1.0)
                new_w, new_h = int(img.width * ratio), int(img.height * ratio)
            else:
                new_w, new_h = int(img.width * z), int(img.height * z)
            resized = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(resized)
            canvas.delete("all")
            canvas.create_image(canvas.winfo_width()//2, canvas.winfo_height()//2,
                                anchor=tk.CENTER, image=tk_img)
            canvas.tk_img = tk_img  # keep reference

        canvas.bind("<Configure>", render_image)
        self.root.after(100, render_image)

    # ==================================================================
    # GIF Animation Tab
    # ==================================================================
    def _open_gif_tab(self, filepath):
        if not HAS_PIL:
            messagebox.showerror("Missing Pillow", "pip install Pillow required.")
            return

        filename = os.path.basename(filepath)
        tid, frame = self._create_tab(filename, "gif", filepath)
        if "canvas" in self.tabs[tid]:
            return

        pil_img = Image.open(filepath)
        frames = []
        try:
            while True:
                frames.append(pil_img.copy())
                pil_img.seek(pil_img.tell() + 1)
        except EOFError:
            pass

        total_frames = len(frames)
        self.tabs[tid]["frames"] = frames
        self.tabs[tid]["current_frame"] = 0
        self.tabs[tid]["playing"] = False
        self.tabs[tid]["speed"] = 1.0

        # Canvas
        canvas = tk.Canvas(frame, bg=BG_WHITE, bd=0, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        self.tabs[tid]["canvas"] = canvas

        # Controls bar
        ctrl = tk.Frame(frame, bg=BG_PANEL, height=40)
        ctrl.pack(fill=tk.X)
        ctrl.pack_propagate(False)

        frame_label = tk.Label(ctrl, text=f"Frame 1 / {total_frames}", bg=BG_PANEL,
                                fg=FG_TEXT, font=self.small_font, padx=8)
        frame_label.pack(side=tk.LEFT)

        def render_frame(idx):
            if idx < 0 or idx >= total_frames:
                return
            self.tabs[tid]["current_frame"] = idx
            img = frames[idx]
            cw, ch = canvas.winfo_width(), canvas.winfo_height()
            if cw < 10:
                cw, ch = 600, 400
            ratio = min(cw / img.width, ch / img.height, 1.0)
            new_w, new_h = int(img.width * ratio), int(img.height * ratio)
            resized = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(resized)
            canvas.delete("all")
            canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=tk_img)
            canvas.tk_img = tk_img
            frame_label.config(text=f"Frame {idx+1} / {total_frames}")
            slider.set(idx)

        def play():
            self.tabs[tid]["playing"] = True
            play_btn.config(text="⏸")
            animate()

        def pause():
            self.tabs[tid]["playing"] = False
            play_btn.config(text="▶")

        def toggle_play():
            if self.tabs[tid]["playing"]:
                pause()
            else:
                play()

        def animate():
            if tid not in self.tabs or not self.tabs[tid]["playing"]:
                return
            idx = (self.tabs[tid]["current_frame"] + 1) % total_frames
            render_frame(idx)
            speed = self.tabs[tid]["speed"]
            delay = max(10, int(100 / speed))
            self.root.after(delay, animate)

        def step_back():
            pause()
            idx = max(0, self.tabs[tid]["current_frame"] - 1)
            render_frame(idx)

        def step_fwd():
            pause()
            idx = min(total_frames - 1, self.tabs[tid]["current_frame"] + 1)
            render_frame(idx)

        def on_slider(val):
            pause()
            render_frame(int(float(val)))

        def set_speed(s):
            self.tabs[tid]["speed"] = s

        # Buttons
        tk.Button(ctrl, text="◀", bg=BG_PANEL, fg=FG_TEXT, font=self.ui_font,
                   relief="flat", bd=0, padx=6, command=step_back,
                   cursor="hand2").pack(side=tk.LEFT, padx=2)

        play_btn = tk.Button(ctrl, text="▶", bg=BG_PANEL, fg=ACCENT, font=self.ui_font,
                              relief="flat", bd=0, padx=6, command=toggle_play,
                              cursor="hand2")
        play_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(ctrl, text="▶", bg=BG_PANEL, fg=FG_TEXT, font=self.ui_font,
                   relief="flat", bd=0, padx=6, command=step_fwd,
                   cursor="hand2").pack(side=tk.LEFT, padx=2)

        # Slider
        slider = tk.Scale(ctrl, from_=0, to=total_frames - 1, orient=tk.HORIZONTAL,
                           bg=BG_PANEL, fg=FG_TEXT, troughcolor=BORDER, highlightthickness=0,
                           command=on_slider, showvalue=False, length=200)
        slider.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        # Speed
        tk.Label(ctrl, text="Speed:", bg=BG_PANEL, fg=FG_DIM,
                 font=self.small_font).pack(side=tk.LEFT, padx=(8, 2))
        for label, spd in [("0.5x", 0.5), ("1x", 1.0), ("2x", 2.0)]:
            tk.Button(ctrl, text=label, bg=BG_PANEL, fg=FG_TEXT, font=self.small_font,
                       relief="flat", bd=0, padx=4, cursor="hand2",
                       command=lambda s=spd: set_speed(s),
                       activebackground=BG_HOVER).pack(side=tk.LEFT, padx=1)

        canvas.bind("<Configure>", lambda e: render_frame(self.tabs[tid]["current_frame"]))
        self.root.after(100, lambda: render_frame(0))

    # ==================================================================
    # CSV Table + Chart Tab
    # ==================================================================
    def _open_csv_tab(self, filepath):
        filename = os.path.basename(filepath)
        tid, frame = self._create_tab(filename, "csv", filepath)
        if "tree" in self.tabs[tid]:
            return

        # Read CSV
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            headers = [h.strip() for h in headers]
            rows = [r for r in reader if r]

        self.tabs[tid]["headers"] = headers
        self.tabs[tid]["rows"] = rows
        self.tabs[tid]["sort_col"] = None
        self.tabs[tid]["sort_asc"] = True

        # Vertical split: table on top, chart config + chart on bottom
        pane = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True)

        # ---- Table Section ----
        table_frame = tk.Frame(pane, bg=BG_WHITE)
        pane.add(table_frame, weight=2)

        # Search bar
        search_bar = tk.Frame(table_frame, bg=BG_PANEL, height=30)
        search_bar.pack(fill=tk.X)
        search_bar.pack_propagate(False)
        tk.Label(search_bar, text="🔍", bg=BG_PANEL, fg=FG_DIM,
                 font=self.small_font, padx=4).pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_bar, textvariable=search_var, bg=BG_WHITE, fg=FG_TEXT,
                                 font=self.small_font, bd=1, relief="solid",
                                 highlightcolor=ACCENT, highlightthickness=1)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
        row_count_label = tk.Label(search_bar, text=f"{len(rows)} rows", bg=BG_PANEL,
                                    fg=FG_DIM, font=self.small_font, padx=8)
        row_count_label.pack(side=tk.RIGHT)

        # Treeview
        tree_container = tk.Frame(table_frame, bg=BG_WHITE)
        tree_container.pack(fill=tk.BOTH, expand=True)

        x_scroll = tk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        y_scroll = tk.Scrollbar(tree_container, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        tree = ttk.Treeview(tree_container, columns=headers, show="headings",
                             style="CSV.Treeview",
                             xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        tree.pack(fill=tk.BOTH, expand=True)
        x_scroll.config(command=tree.xview)
        y_scroll.config(command=tree.yview)

        for h in headers:
            tree.heading(h, text=h, command=lambda c=h: sort_column(c))
            tree.column(h, width=max(80, len(h) * 9), minwidth=60)

        def populate(data):
            tree.delete(*tree.get_children())
            for row in data:
                tree.insert("", "end", values=row)
            row_count_label.config(text=f"{len(data)} rows")

        def sort_column(col):
            asc = self.tabs[tid]["sort_asc"]
            if self.tabs[tid]["sort_col"] == col:
                asc = not asc
            else:
                asc = True
            self.tabs[tid]["sort_col"] = col
            self.tabs[tid]["sort_asc"] = asc
            idx = headers.index(col)
            data = list(rows)
            try:
                data.sort(key=lambda r: float(r[idx]) if r[idx] not in ("NaN", "PENDING", "") else float('inf'),
                          reverse=not asc)
            except (ValueError, IndexError):
                data.sort(key=lambda r: r[idx] if idx < len(r) else "", reverse=not asc)
            populate(data)

        def filter_rows(*args):
            q = search_var.get().lower()
            if not q:
                populate(rows)
            else:
                filtered = [r for r in rows if any(q in cell.lower() for cell in r)]
                populate(filtered)

        search_var.trace_add("write", filter_rows)
        populate(rows)
        self.tabs[tid]["tree"] = tree

        # ---- Chart Section ----
        chart_frame = tk.Frame(pane, bg=BG_WHITE)
        pane.add(chart_frame, weight=3)

        self._build_chart_panel(tid, chart_frame, headers, rows)

    # ==================================================================
    # Chart Configuration Panel (Jigsaw-style)
    # ==================================================================
    def _build_chart_panel(self, tid, parent, headers, rows):
        if not HAS_MPL:
            tk.Label(parent, text="⚠️ matplotlib not installed. Run: pip install matplotlib",
                     bg=BG_WHITE, fg=ERROR_COLOR, font=self.ui_font, pady=20).pack()
            return

        numeric_cols = []
        for i, h in enumerate(headers):
            try:
                vals = [float(r[i]) for r in rows[:5] if r[i] not in ("NaN", "PENDING", "")]
                if vals:
                    numeric_cols.append(h)
            except (ValueError, IndexError):
                pass

        h_pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        h_pane.pack(fill=tk.BOTH, expand=True)

        # Scrollable config frame
        config_container = tk.Frame(h_pane, bg=BG_PANEL, width=320)
        h_pane.add(config_container, weight=0)
        
        config_canvas = tk.Canvas(config_container, bg=BG_PANEL, highlightthickness=0)
        scrollbar = tk.Scrollbar(config_container, orient="vertical", command=config_canvas.yview)
        config_frame = tk.Frame(config_canvas, bg=BG_PANEL)
        
        def _update_scrollregion(*args):
            config_canvas.configure(scrollregion=config_canvas.bbox("all"))
            
        config_frame.bind("<Configure>", _update_scrollregion)
        canvas_window = config_canvas.create_window((0, 0), window=config_frame, anchor="nw")
        
        def _on_canvas_configure(e):
            config_canvas.itemconfig(canvas_window, width=e.width)
            
        config_canvas.bind("<Configure>", _on_canvas_configure)
        config_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mousewheel support
        def _on_mousewheel(e):
            config_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        config_canvas.bind("<Enter>", lambda e: config_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        config_canvas.bind("<Leave>", lambda e: config_canvas.unbind_all("<MouseWheel>"))
        
        config_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(config_frame, text="📊 Chart Configuration", bg=BG_PANEL, fg=FG_DARK,
                 font=self.header_font, padx=10, pady=6).pack(anchor="w")

        # --- Chart Type ---
        type_frame = tk.LabelFrame(config_frame, text="Chart Type", bg=BG_PANEL, fg=FG_TEXT,
                                    font=self.small_font, padx=8, pady=4)
        type_frame.pack(fill=tk.X, padx=8, pady=4)

        chart_type_var = tk.StringVar(value="scatter")
        for label, val in [("Line", "line"), ("Scatter", "scatter"),
                           ("Bar", "bar"), ("Heatmap", "heatmap")]:
            tk.Radiobutton(type_frame, text=label, variable=chart_type_var, value=val,
                            bg=BG_PANEL, fg=FG_TEXT, font=self.small_font,
                            selectcolor=BG_SELECTED, activebackground=BG_PANEL,
                            command=lambda: update_ui_visibility()).pack(side=tk.LEFT, padx=4)

        # --- Axis Config ---
        axis_frame = tk.LabelFrame(config_frame, text="Axis Configuration", bg=BG_PANEL,
                                    fg=FG_TEXT, font=self.small_font, padx=8, pady=4)
        axis_frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(axis_frame, text="X-Axis:", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font).grid(row=0, column=0, sticky="w")
        x_var = tk.StringVar(value=numeric_cols[0] if numeric_cols else "")
        ttk.Combobox(axis_frame, textvariable=x_var, values=numeric_cols, width=18, state="readonly").grid(row=0, column=1, pady=2, padx=4)

        tk.Label(axis_frame, text="Y-Axis (Primary):", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font).grid(row=1, column=0, sticky="nw", pady=2)
        
        y_listbox_frame = tk.Frame(axis_frame, bg=BG_PANEL)
        y_listbox_frame.grid(row=1, column=1, pady=2, padx=4, sticky="w")
        y_scroll = tk.Scrollbar(y_listbox_frame, orient=tk.VERTICAL)
        y_listbox = tk.Listbox(y_listbox_frame, selectmode=tk.MULTIPLE, exportselection=0,
                               width=20, height=4, font=self.small_font, yscrollcommand=y_scroll.set)
        y_scroll.config(command=y_listbox.yview)
        y_listbox.pack(side=tk.LEFT, fill=tk.BOTH)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        for col in numeric_cols:
            y_listbox.insert(tk.END, col)
        if len(numeric_cols) > 1:
            y_listbox.select_set(1)

        z_label = tk.Label(axis_frame, text="Z-Value (Heatmap):", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font)
        z_label.grid(row=2, column=0, sticky="w", pady=2)
        z_var = tk.StringVar(value=numeric_cols[2] if len(numeric_cols) > 2 else "")
        z_combo = ttk.Combobox(axis_frame, textvariable=z_var, values=numeric_cols, width=18, state="readonly")
        z_combo.grid(row=2, column=1, pady=2, padx=4)

        # --- Advanced Styling Toggle ---
        adv_btn = tk.Button(config_frame, text="Advanced Options ▾", bg=BG_PANEL, fg=ACCENT,
                            font=self.ui_bold, relief="flat", cursor="hand2", bd=0)
        adv_btn.pack(anchor="w", padx=8, pady=(8,0))
        
        adv_frame = tk.Frame(config_frame, bg=BG_PANEL)
        adv_visible = tk.BooleanVar(value=False)
        
        def toggle_adv():
            if adv_visible.get():
                adv_frame.pack_forget()
                adv_visible.set(False)
                adv_btn.config(text="Advanced Options ▸")
            else:
                adv_frame.pack(fill=tk.X, padx=8, pady=4, before=btn_frame)
                adv_visible.set(True)
                adv_btn.config(text="Advanced Options ▾")
            self.root.after(50, _update_scrollregion)
                
        adv_btn.config(command=toggle_adv)

        # Global Adv
        global_adv = tk.LabelFrame(adv_frame, text="Global Options", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font, padx=8, pady=4)
        global_adv.pack(fill=tk.X, pady=2)
        
        log_x_var = tk.BooleanVar(value=False)
        log_y_var = tk.BooleanVar(value=False)
        grid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(global_adv, text="Log X", variable=log_x_var, bg=BG_PANEL).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(global_adv, text="Log Y", variable=log_y_var, bg=BG_PANEL).grid(row=0, column=1, sticky="w")
        tk.Checkbutton(global_adv, text="Show Grid", variable=grid_var, bg=BG_PANEL).grid(row=0, column=2, sticky="w")

        # Line/Scatter Adv
        line_adv = tk.LabelFrame(adv_frame, text="Line/Scatter Options", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font, padx=8, pady=4)
        line_adv.pack(fill=tk.X, pady=2)
        
        tk.Label(line_adv, text="Marker Style:", bg=BG_PANEL, font=self.small_font).grid(row=0, column=0, sticky="w")
        marker_var = tk.StringVar(value="o")
        ttk.Combobox(line_adv, textvariable=marker_var, values=["o", "s", "^", "x", "None"], width=6, state="readonly").grid(row=0, column=1)
        
        tk.Label(line_adv, text="Size/Width:", bg=BG_PANEL, font=self.small_font).grid(row=0, column=2, sticky="w", padx=(5,0))
        size_var = tk.IntVar(value=30)
        tk.Scale(line_adv, from_=10, to=100, variable=size_var, orient=tk.HORIZONTAL, showvalue=0, length=60).grid(row=0, column=3)
        
        tk.Label(line_adv, text="Alpha:", bg=BG_PANEL, font=self.small_font).grid(row=1, column=0, sticky="w")
        alpha_var = tk.DoubleVar(value=0.7)
        tk.Scale(line_adv, from_=0.1, to=1.0, resolution=0.1, variable=alpha_var, orient=tk.HORIZONTAL, showvalue=0, length=60).grid(row=1, column=1)

        tk.Label(line_adv, text="Trendline:", bg=BG_PANEL, font=self.small_font).grid(row=1, column=2, sticky="w", padx=(5,0))
        fit_var = tk.StringVar(value="None")
        ttk.Combobox(line_adv, textvariable=fit_var, values=["None", "Linear", "Polynomial (2)", "Exponential", "Gaussian"], width=10, state="readonly").grid(row=1, column=3)

        # Heatmap Adv
        heat_adv = tk.LabelFrame(adv_frame, text="Heatmap Options", bg=BG_PANEL, fg=FG_TEXT, font=self.small_font, padx=8, pady=4)
        heat_adv.pack(fill=tk.X, pady=2)
        
        tk.Label(heat_adv, text="Colormap:", bg=BG_PANEL, font=self.small_font).grid(row=0, column=0, sticky="w")
        cmap_var = tk.StringVar(value="viridis")
        ttk.Combobox(heat_adv, textvariable=cmap_var, values=["viridis", "plasma", "inferno", "coolwarm", "jet"], width=10, state="readonly").grid(row=0, column=1)
        
        tk.Label(heat_adv, text="Interpolation:", bg=BG_PANEL, font=self.small_font).grid(row=1, column=0, sticky="w")
        interp_var = tk.StringVar(value="nearest")
        ttk.Combobox(heat_adv, textvariable=interp_var, values=["nearest", "bicubic", "gaussian", "bilinear"], width=10, state="readonly").grid(row=1, column=1)

        tk.Label(heat_adv, text="Cell Size (px):", bg=BG_PANEL, font=self.small_font).grid(row=2, column=0, sticky="w")
        cell_size_var = tk.StringVar(value="Auto")
        ttk.Combobox(heat_adv, textvariable=cell_size_var, values=["Auto", "5", "10", "15", "20", "30", "50"], width=10).grid(row=2, column=1)

        def update_ui_visibility():
            ct = chart_type_var.get()
            if ct == "heatmap":
                z_label.grid()
                z_combo.grid()
                line_adv.pack_forget()
                heat_adv.pack(fill=tk.X, pady=2)
            else:
                z_label.grid_remove()
                z_combo.grid_remove()
                heat_adv.pack_forget()
                line_adv.pack(fill=tk.X, pady=2)
            self.root.after(50, _update_scrollregion)

        # Generate / Save buttons
        btn_frame = tk.Frame(config_frame, bg=BG_PANEL)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)

        tk.Button(btn_frame, text="▶ Generate Chart", bg="#DCFCE7", fg=SUCCESS_COLOR,
                   font=self.ui_bold, relief="flat", bd=0, padx=12, pady=4,
                   cursor="hand2", command=lambda: generate_chart(),
                   activebackground="#BBF7D0").pack(fill=tk.X, pady=2)

        tk.Button(btn_frame, text="💾 Save as PNG", bg=BG_WHITE, fg=FG_TEXT,
                   font=self.ui_font, relief="flat", bd=1, padx=12, pady=4,
                   cursor="hand2", command=lambda: save_chart(),
                   activebackground=BG_HOVER).pack(fill=tk.X, pady=2)

        toggle_adv() # start open
        update_ui_visibility()

        # --- Chart Canvas Container ---
        chart_container = tk.Frame(h_pane, bg=BG_WHITE)
        h_pane.add(chart_container, weight=1)
        
        toolbar_frame = tk.Frame(chart_container, bg=BG_WHITE)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        chart_scroll_canvas = tk.Canvas(chart_container, bg=BG_WHITE, highlightthickness=0)
        chart_v_scroll = tk.Scrollbar(chart_container, orient=tk.VERTICAL, command=chart_scroll_canvas.yview)
        chart_h_scroll = tk.Scrollbar(chart_container, orient=tk.HORIZONTAL, command=chart_scroll_canvas.xview)
        
        chart_canvas_frame = tk.Frame(chart_scroll_canvas, bg=BG_WHITE)
        
        chart_scroll_canvas.configure(yscrollcommand=chart_v_scroll.set, xscrollcommand=chart_h_scroll.set)
        
        chart_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        chart_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        chart_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_window = chart_scroll_canvas.create_window((0, 0), window=chart_canvas_frame, anchor="nw")
        
        fig = Figure(figsize=(8, 5), dpi=100, facecolor=BG_WHITE)
        fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.12)
        canvas = FigureCanvasTkAgg(fig, master=chart_canvas_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        nav_toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        nav_toolbar.update()
        
        def _on_chart_resize(event):
            if cell_size_var.get() == "Auto":
                chart_scroll_canvas.itemconfig(canvas_window, width=event.width, height=event.height)
        chart_scroll_canvas.bind("<Configure>", _on_chart_resize)
        
        def _update_chart_scrollregion(*args):
            chart_scroll_canvas.configure(scrollregion=chart_scroll_canvas.bbox("all"))
        chart_canvas_frame.bind("<Configure>", _update_chart_scrollregion)

        self.tabs[tid]["figure"] = fig
        self.tabs[tid]["chart_canvas"] = canvas
        ax_holder = [None]
        annot_holder = [None]

        def generate_chart():
            fig.clear()
            ct = chart_type_var.get()
            x_col = x_var.get()
            
            y_indices = y_listbox.curselection()
            if not x_col or (not y_indices and ct != "heatmap"):
                messagebox.showwarning("Missing", "Select X and Y axis columns.")
                return

            xi = headers.index(x_col)
            
            if ct == "heatmap":
                z_col = z_var.get()
                if not z_col or not y_indices:
                    messagebox.showwarning("Missing", "Select Y and Z columns for heatmap.")
                    return
                yi = headers.index(y_listbox.get(y_indices[0]))
                zi = headers.index(z_col)
                self._render_heatmap(fig, rows, xi, yi, zi, x_col, y_listbox.get(y_indices[0]), z_col,
                                     cmap_var.get(), interp_var.get(), tid, cell_size_var.get())
            else:
                ax = fig.add_subplot(111)
                ax.set_facecolor(BG_WHITE)
                ax.set_xlabel(x_col, fontsize=10)
                
                if log_x_var.get(): ax.set_xscale("log")
                if log_y_var.get(): ax.set_yscale("log")
                if grid_var.get(): ax.grid(True, alpha=0.3, color=BORDER)

                colors = [ACCENT, ERROR_COLOR, WARNING_COLOR, "#8B5CF6", "#14B8A6", "#F43F5E"]
                sc_data = [] # for hover
                
                # Multiple Y series
                for idx, y_sel in enumerate(y_indices):
                    y_col = y_listbox.get(y_sel)
                    yi = headers.index(y_col)
                    xdata, ydata = [], []
                    for r in rows:
                        try:
                            xdata.append(float(r[xi]))
                            ydata.append(float(r[yi]))
                        except (ValueError, IndexError):
                            continue
                            
                    color = colors[idx % len(colors)]
                    marker = marker_var.get() if marker_var.get() != "None" else ""
                    size = size_var.get()
                    alpha = alpha_var.get()

                    if ct == "line":
                        paired = sorted(zip(xdata, ydata))
                        xs, ys = zip(*paired) if paired else ([], [])
                        ax.plot(xs, ys, linestyle="-", marker=marker, color=color, 
                                markersize=size/5, linewidth=2, alpha=alpha, label=y_col, picker=5)
                        sc_data.extend(paired)
                    elif ct == "scatter":
                        ax.scatter(xdata, ydata, c=color, marker=marker if marker else "o", 
                                   s=size, alpha=alpha, edgecolors="white", linewidth=0.5, label=y_col, picker=5)
                        sc_data.extend(zip(xdata, ydata))
                    elif ct == "bar":
                        width = (max(xdata)-min(xdata))/len(xdata)*0.8 if xdata else 1
                        ax.bar(xdata, ydata, width=width, color=color, alpha=alpha, label=y_col)
                        sc_data.extend(zip(xdata, ydata))
                        
                    # Trendline
                    fit = fit_var.get()
                    if fit != "None" and len(xdata) > 1:
                        try:
                            xs_fit = np.linspace(min(xdata), max(xdata), 100)
                            if fit == "Linear":
                                p = np.polyfit(xdata, ydata, 1)
                                ys_fit = np.polyval(p, xs_fit)
                            elif fit == "Polynomial (2)":
                                p = np.polyfit(xdata, ydata, 2)
                                ys_fit = np.polyval(p, xs_fit)
                            elif fit == "Exponential":
                                p = np.polyfit(xdata, np.log(np.maximum(ydata, 1e-10)), 1)
                                ys_fit = np.exp(p[1]) * np.exp(p[0] * xs_fit)
                            elif fit == "Gaussian":
                                from scipy.optimize import curve_fit
                                def gauss(x, a, x0, sigma): return a * np.exp(-(x - x0)**2 / (2 * sigma**2))
                                popt, _ = curve_fit(gauss, xdata, ydata, p0=[max(ydata), np.median(xdata), np.std(xdata)])
                                ys_fit = gauss(xs_fit, *popt)
                                
                            ax.plot(xs_fit, ys_fit, "--", color=color, linewidth=1.5, alpha=0.8, label=f"{y_col} ({fit})")
                        except Exception as e:
                            print(f"Fit error: {e}")

                ax.set_ylabel(", ".join([y_listbox.get(i) for i in y_indices]), fontsize=10)
                ax.set_title(f"Multiple Y vs {x_col}" if len(y_indices)>1 else f"{y_listbox.get(y_indices[0])} vs {x_col}", fontsize=12, fontweight="bold")
                ax.legend(loc="best", fontsize=8)
                ax_holder[0] = ax

                # Hover tooltip
                annot = ax.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                                     bbox=dict(boxstyle="round,pad=0.4", fc=BG_WHITE, ec=BORDER, alpha=0.95),
                                     fontsize=9, color=FG_TEXT)
                annot.set_visible(False)

                def on_move(event):
                    if event.inaxes != ax or not sc_data:
                        if annot.get_visible():
                            annot.set_visible(False)
                            canvas.draw_idle()
                        return
                    ex, ey = event.xdata, event.ydata
                    if ex is None or ey is None: return
                    
                    try:
                        x_range = max([p[0] for p in sc_data]) - min([p[0] for p in sc_data]) or 1
                        y_range = max([p[1] for p in sc_data]) - min([p[1] for p in sc_data]) or 1
                        dists = [((px - ex)/x_range)**2 + ((py - ey)/y_range)**2 for px, py in sc_data]
                        min_idx = dists.index(min(dists))
                        if min(dists) < 0.01:
                            px, py = sc_data[min_idx]
                            annot.xy = (px, py)
                            annot.set_text(f"X: {px:g}\nY: {py:g}")
                            annot.set_visible(True)
                            canvas.draw_idle()
                        else:
                            if annot.get_visible():
                                annot.set_visible(False)
                                canvas.draw_idle()
                    except: pass

                fig.canvas.mpl_connect("motion_notify_event", on_move)
            canvas.draw()

        def save_chart():
            path = filedialog.asksaveasfilename(
                defaultextension=".png", initialdir=ROOT_DIR,
                filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
            if path:
                fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG_WHITE)
                self._set_status(f"Chart saved: {path}")

    # ==================================================================
    # Heatmap Renderer
    # ==================================================================
    def _render_heatmap(self, fig, rows, xi, yi, zi, x_label, y_label, z_label, cmap, interp, tid, cell_size_str="Auto"):
        ax = fig.add_subplot(111)
        ax.set_facecolor(BG_WHITE)

        data_points = []
        for r in rows:
            try:
                xv = float(r[xi])
                yv = float(r[yi])
                zv = float(r[zi])
                data_points.append((xv, yv, zv))
            except (ValueError, IndexError):
                continue

        if not data_points:
            ax.text(0.5, 0.5, "No valid data", ha="center", va="center", fontsize=14)
            return

        xs = sorted(set(p[0] for p in data_points))
        ys = sorted(set(p[1] for p in data_points))

        z_grid = np.full((len(ys), len(xs)), np.nan)
        x_idx = {v: i for i, v in enumerate(xs)}
        y_idx = {v: i for i, v in enumerate(ys)}
        for xv, yv, zv in data_points:
            if xv in x_idx and yv in y_idx:
                z_grid[y_idx[yv]][x_idx[xv]] = zv

        im = ax.imshow(z_grid, aspect="auto", origin="lower", cmap=cmap,
                         extent=[min(xs), max(xs), min(ys), max(ys)],
                         interpolation=interp)
        fig.colorbar(im, ax=ax, label=z_label, shrink=0.8)
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        ax.set_title(f"Heatmap: {z_label}", fontsize=12, fontweight="bold")

        annot = ax.annotate("", xy=(0, 0), xytext=(15, 15),
                             textcoords="offset points",
                             bbox=dict(boxstyle="round,pad=0.4", fc=BG_WHITE,
                                       ec=BORDER, alpha=0.95),
                             fontsize=9, color=FG_TEXT)
        annot.set_visible(False)
        vline = ax.axvline(x=min(xs), color=FG_DIM, linewidth=0.5, linestyle="--", visible=False)
        hline = ax.axhline(y=min(ys), color=FG_DIM, linewidth=0.5, linestyle="--", visible=False)

        def on_move(event):
            if event.inaxes != ax:
                annot.set_visible(False)
                vline.set_visible(False)
                hline.set_visible(False)
                self.tabs[tid]["chart_canvas"].draw_idle()
                return
            ex, ey = event.xdata, event.ydata
            if ex is None or ey is None: return

            nearest_x = min(xs, key=lambda v: abs(v - ex))
            nearest_y = min(ys, key=lambda v: abs(v - ey))
            ix = x_idx[nearest_x]
            iy = y_idx[nearest_y]
            zv = z_grid[iy][ix]

            annot.xy = (nearest_x, nearest_y)
            if not np.isnan(zv):
                annot.set_text(f"{x_label}: {nearest_x:g}\n{y_label}: {nearest_y:g}\n{z_label}: {zv:g}")
            else:
                annot.set_text(f"{x_label}: {nearest_x:g}\n{y_label}: {nearest_y:g}\n{z_label}: N/A")
            annot.set_visible(True)
            vline.set_xdata([nearest_x])
            vline.set_visible(True)
            hline.set_ydata([nearest_y])
            hline.set_visible(True)
            self.tabs[tid]["chart_canvas"].draw_idle()

        if cell_size_str != "Auto":
            try:
                cell_px = int(cell_size_str)
                dpi = fig.dpi
                fig_w = (len(xs) * cell_px) / (dpi * 0.83)
                fig_h = (len(ys) * cell_px) / (dpi * 0.80)
                
                fig_w = min(fig_w, 200)
                fig_h = min(fig_h, 200)
                
                fig.set_size_inches(fig_w, fig_h)
                canvas_widget = self.tabs[tid]["chart_canvas"].get_tk_widget()
                canvas_widget.config(width=int(fig_w*dpi), height=int(fig_h*dpi))
            except ValueError:
                pass
        else:
            fig.set_size_inches(8, 5)
            # When back to Auto, the widget shouldn't have explicit size
            canvas_widget = self.tabs[tid]["chart_canvas"].get_tk_widget()
            canvas_widget.config(width="", height="")
            vline.set_xdata([nearest_x])
            vline.set_visible(True)
            hline.set_ydata([nearest_y])
            hline.set_visible(True)
            self.tabs[tid]["chart_canvas"].draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_move)

    # ==================================================================
    # File Operations
    # ==================================================================
    def _open_file_dialog(self):
        filepath = filedialog.askopenfilename(
            initialdir=ROOT_DIR,
            filetypes=[("All Supported", "*.py *.txt *.md *.csv *.png *.gif *.log"),
                       ("Python", "*.py"), ("CSV", "*.csv"), ("Images", "*.png *.gif *.jpg"),
                       ("Text", "*.txt *.md *.log"), ("All", "*.*")])
        if filepath:
            self._open_file(filepath)

    def _open_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()

        if ext in (".png", ".jpg", ".jpeg"):
            self._open_image_tab(filepath)
        elif ext == ".gif":
            self._open_gif_tab(filepath)
        elif ext == ".csv":
            self._open_csv_tab(filepath)
        elif ext in (".py", ".txt", ".md", ".log", ".json", ".cfg", ".ini", ".yaml", ".yml", ".toml", ""):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self._open_code_tab(filepath, content)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file:\n{e}")
        else:
            self._set_status(f"Unsupported file type: {ext}")

    def _save_current_tab(self):
        tid, info = self._get_current_tab()
        if tid:
            self._save_tab(tid)

    def _save_tab(self, tid):
        info = self.tabs[tid]
        if info["type"] != "code" or not info.get("filepath"):
            return
        try:
            content = info["editor"].get("1.0", tk.END)
            if content.endswith("\n"):
                content = content[:-1]
            with open(info["filepath"], "w", encoding="utf-8") as f:
                f.write(content)
            info["modified"] = False
            self.notebook.tab(info["frame"], text=f"  {info['title']}  ✕")
            self._set_status(f"Saved: {info['filepath']}")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot save:\n{e}")

    # ==================================================================
    # File Explorer
    # ==================================================================
    def _refresh_file_tree(self):
        self.file_tree.delete(*self.file_tree.get_children())
        self._populate_tree("", ROOT_DIR)

    def _get_folder_info(self, path):
        total_size = 0
        file_count = 0
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "venv", ".venv", ".gemini"]]
                for f in files:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        try:
                            total_size += os.path.getsize(fp)
                            file_count += 1
                        except OSError:
                            pass
        except OSError:
            pass
        
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
            
        return file_count, size_str

    def _populate_tree(self, parent, path):
        try:
            items = os.listdir(path)
        except PermissionError:
            return

        sort_by = getattr(self, 'sort_var', None)
        sort_mode = sort_by.get() if sort_by else "Date (Newest)"
        
        def sort_key(entry):
            full_path = os.path.join(path, entry)
            is_dir = os.path.isdir(full_path)
            ext = os.path.splitext(entry)[1].lower()
            
            if ext in (".txt", ".csv"):
                type_order = 0
            elif is_dir:
                type_order = 1
            else:
                type_order = 2
                
            if sort_mode == "Date (Newest)":
                try:
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    mtime = 0
                return (type_order, -mtime, entry.lower())
            else:
                return (type_order, 0, entry.lower())

        entries = sorted(items, key=sort_key)
        
        for entry in entries:
            full = os.path.join(path, entry)
            if entry.startswith(".") or entry == "__pycache__":
                continue
            if os.path.isdir(full):
                file_count, size_str = self._get_folder_info(full)
                text = f"  📁 {entry} ({file_count} files, {size_str})"
                node = self.file_tree.insert(parent, "end", text=text, values=(full,))
                self.file_tree.insert(node, "end", text="...")
                self.file_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
            else:
                ext = os.path.splitext(entry)[1].lower()
                icon = ICON_MAP.get(ext, "📄")
                try:
                    sz = os.path.getsize(full)
                    if sz < 1024: s_str = f"{sz} B"
                    elif sz < 1024*1024: s_str = f"{sz/1024:.1f} KB"
                    else: s_str = f"{sz/(1024*1024):.1f} MB"
                except OSError:
                    s_str = ""
                self.file_tree.insert(parent, "end", text=f"  {icon} {entry}  [{s_str}]", values=(full,))

    def _on_tree_expand(self, event):
        node = self.file_tree.focus()
        children = self.file_tree.get_children(node)
        if len(children) == 1 and self.file_tree.item(children[0], "text").strip() == "...":
            self.file_tree.delete(children[0])
            vals = self.file_tree.item(node, "values")
            if vals:
                self._populate_tree(node, vals[0])

    def _on_tree_double_click(self, event):
        node = self.file_tree.focus()
        vals = self.file_tree.item(node, "values")
        if vals and os.path.isfile(vals[0]):
            self._open_file(vals[0])

    def _on_tree_right_click(self, event):
        node = self.file_tree.identify_row(event.y)
        if node:
            self.file_tree.selection_set(node)
            vals = self.file_tree.item(node, "values")
            if vals:
                self._ctx_path = vals[0]
                self.ctx_menu.post(event.x_root, event.y_root)

    def _ctx_open(self):
        if self._ctx_path and os.path.isfile(self._ctx_path):
            self._open_file(self._ctx_path)

    def _ctx_copy_path(self):
        if self._ctx_path:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._ctx_path)
            self._set_status(f"Copied: {self._ctx_path}")

    def _ctx_delete(self):
        if self._ctx_path:
            if messagebox.askyesno("Delete", f"Delete {os.path.basename(self._ctx_path)}?"):
                try:
                    os.remove(self._ctx_path)
                    self._refresh_file_tree()
                    self._set_status(f"Deleted: {self._ctx_path}")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

    # ==================================================================
    # Terminal
    # ==================================================================
    def _write_terminal(self, text, tag="info"):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, text, tag)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def _clear_terminal(self):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)

    # ==================================================================
    # Run / Stop
    # ==================================================================
    def _run_simulation(self):
        target = self.run_target_var.get()
        if target == "Current File":
            tid, info = self._get_current_tab()
            if info and info.get("filepath"):
                self._run_script(info["filepath"])
            else:
                messagebox.showwarning("No File", "No file open.")
        else:
            self._run_script(target)

    def _run_script(self, script_path):
        if self.is_running:
            messagebox.showwarning("Running", "A process is already running.")
            return

        # Auto-save current code tab
        tid, info = self._get_current_tab()
        if info and info.get("modified") and info["type"] == "code":
            self._save_tab(tid)

        if not os.path.isabs(script_path):
            script_path = os.path.join(ROOT_DIR, script_path)
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Not found:\n{script_path}")
            return

        self.is_running = True
        self.run_start_time = time.time()
        self._update_run_ui(True)
        self._clear_terminal()

        name = os.path.basename(script_path)
        self._write_terminal(f"{'─'*60}\n", "dim")
        self._write_terminal(f"  ▶ Running: {name}\n", "accent")
        self._write_terminal(f"  Dir: {ROOT_DIR}\n", "dim")
        self._write_terminal(f"{'─'*60}\n\n", "dim")

        threading.Thread(target=self._run_process, args=(script_path,), daemon=True).start()
        self._update_timer()

    def _run_process(self, script_path):
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=ROOT_DIR,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
            for line in self.process.stdout:
                self.output_queue.put(("output", line))
            self.process.wait()
            self.output_queue.put(("done", self.process.returncode))
        except Exception as e:
            self.output_queue.put(("error", str(e)))

    def _poll_output(self):
        try:
            while True:
                msg_type, data = self.output_queue.get_nowait()
                if msg_type == "output":
                    tag = "info"
                    low = data.lower()
                    if "error" in low or "failed" in low:
                        tag = "error"
                    elif "success" in low or "finished" in low or "completed" in low:
                        tag = "success"
                    elif "warning" in low:
                        tag = "warning"
                    elif data.startswith("[") or data.startswith("==="):
                        tag = "accent"
                    self._write_terminal(data, tag)
                elif msg_type == "done":
                    elapsed = time.time() - self.run_start_time if self.run_start_time else 0
                    m, s = divmod(int(elapsed), 60)
                    self._write_terminal(f"\n{'─'*60}\n", "dim")
                    if data == 0:
                        self._write_terminal(f"  ✓ Done (exit 0) — {m}m {s}s\n", "success")
                    else:
                        self._write_terminal(f"  ✗ Exit code {data} — {m}m {s}s\n", "error")
                    self._write_terminal(f"{'─'*60}\n", "dim")
                    self.is_running = False
                    self.process = None
                    self._update_run_ui(False)
                    self._refresh_file_tree()
                elif msg_type == "error":
                    self._write_terminal(f"\n[ERROR] {data}\n", "error")
                    self.is_running = False
                    self.process = None
                    self._update_run_ui(False)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_output)

    def _stop_simulation(self):
        if self.process and self.is_running:
            try:
                stop_file = os.path.join(ROOT_DIR, "emergency_stop.txt")
                with open(stop_file, "w") as f:
                    f.write("GUI stop")
                self._write_terminal("\n[STOP] Emergency stop requested...\n", "warning")
                if sys.platform == "win32":
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.process.terminate()
                def force_kill():
                    if self.process and self.process.poll() is None:
                        self.process.kill()
                        self._write_terminal("[STOP] Force killed.\n", "error")
                self.root.after(5000, force_kill)
            except Exception as e:
                self._write_terminal(f"[STOP] Error: {e}\n", "error")
                try:
                    self.process.kill()
                except Exception:
                    pass

    def _update_run_ui(self, running):
        if running:
            self.run_btn.config(state=tk.DISABLED, bg=BORDER)
            self.stop_btn.config(state=tk.NORMAL, bg="#FEE2E2")
            self.status_indicator.config(text="● Running", fg=WARNING_COLOR)
            self._set_status("Running...")
        else:
            self.run_btn.config(state=tk.NORMAL, bg="#DCFCE7")
            self.stop_btn.config(state=tk.DISABLED, bg=BORDER)
            self.status_indicator.config(text="● Idle", fg=SUCCESS_COLOR)
            self.timer_label.config(text="")
            self._set_status("Ready")

    def _update_timer(self):
        if self.is_running and self.run_start_time:
            elapsed = time.time() - self.run_start_time
            m, s = divmod(int(elapsed), 60)
            h, m = divmod(m, 60)
            self.timer_label.config(text=f"⏱ {h}h {m}m {s}s" if h else f"⏱ {m}m {s}s")
            self.root.after(1000, self._update_timer)

    # ==================================================================
    # Utils
    # ==================================================================
    def _set_status(self, text):
        self.status_label.config(text=text)

    def _on_close(self):
        # Check for unsaved tabs
        for tid, info in list(self.tabs.items()):
            if info.get("modified") and info["type"] == "code":
                ans = messagebox.askyesnocancel("Save?", f"Save {info['title']}?")
                if ans is True:
                    self._save_tab(tid)
                elif ans is None:
                    return
        if self.is_running:
            if not messagebox.askyesno("Running", "Stop running process and close?"):
                return
            self._stop_simulation()
        # Cleanup matplotlib
        for tid, info in self.tabs.items():
            if "figure" in info:
                plt.close(info["figure"])
        self.root.destroy()


def main():
    root = tk.Tk()
    app = HyperthermiaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
