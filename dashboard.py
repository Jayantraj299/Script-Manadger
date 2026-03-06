# -*- coding: utf-8 -*-
# dashboard.py
import customtkinter as ctk
import os
import json
import platform
import subprocess
import threading
from tkinter import messagebox, TclError
from PIL import Image
import pystray 

from script_manager import ScriptManager, PRIORITY_MAP, REV_PRIORITY_MAP, SCRIPTS_FOLDER
from taskbar_tray import SystemTray

# ================= UI CONFIGURATION =================
SETTINGS_FILE = "settings.json"

CLI_COLORS = {
    "Hacker Green": "#00ff00", "Cyber Cyan": "#00ffff", 
    "Retro Amber": "#ffbf00", "Pure White": "#ffffff", "Error Red": "#ff5555"
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CODE EDITOR WINDOW ---
class ScriptEditor(ctk.CTkToplevel):
    def __init__(self, parent, manager, script_name=None):
        super().__init__(parent)
        self.manager = manager
        self.title(f"Editor - {script_name if script_name else 'New Script'}")
        self.geometry("800x600")
        
        self.filename = script_name
        self.is_new = script_name is None

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=5)
        
        if self.is_new:
            self.name_entry = ctk.CTkEntry(top_frame, placeholder_text="filename.py", width=200)
            self.name_entry.pack(side="left")
        else:
            ctk.CTkLabel(top_frame, text=script_name, font=("Consolas", 14, "bold")).pack(side="left")

        ctk.CTkButton(top_frame, text="SAVE", width=80, fg_color="#2ecc71", command=self.save_file).pack(side="right")

        self.text_area = ctk.CTkTextbox(self, font=("Consolas", 13), wrap="none")
        self.text_area.pack(fill="both", expand=True, padx=10, pady=5)

        if not self.is_new:
            content = self.manager.read_script_content(script_name)
            self.text_area.insert("0.0", content)

    def save_file(self):
        content = self.text_area.get("0.0", "end")
        if self.is_new:
            name = self.name_entry.get().strip()
            if not name: return
            if not name.endswith(".py"): name += ".py"
            if os.path.exists(os.path.join(SCRIPTS_FOLDER, name)):
                messagebox.showerror("Error", "File exists!")
                return
            self.manager.create_script(name)
            self.manager.save_script_content(name, content)
            self.master.refresh_list()
            self.destroy()
        else:
            self.manager.save_script_content(self.filename, content)
            messagebox.showinfo("Saved", f"Updated {self.filename}")

# --- SETTINGS EDITOR ---
class ConfigEditor(ctk.CTkToplevel):
    def __init__(self, dashboard, manager, script_name):
        super().__init__(dashboard)
        self.dashboard = dashboard
        self.manager = manager
        self.script_name = script_name
        self.title(f"Settings: {script_name}")
        self.geometry("400x650")
        self.attributes("-topmost", True)

        self.data = self.manager.read_config(script_name)
        
        ctk.CTkLabel(self, text="Display Mode:", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
        self.mode_var = ctk.StringVar(value=self.data.get("mode", "cli"))
        ctk.CTkSegmentedButton(self, values=["cli", "widget"], variable=self.mode_var).pack(pady=5)

        ctk.CTkLabel(self, text="Priority:", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
        self.priority_var = ctk.StringVar(value=REV_PRIORITY_MAP.get(self.data.get("priority", 3), "Low"))
        ctk.CTkOptionMenu(self, variable=self.priority_var, values=["High", "Medium", "Low"]).pack(pady=5)
        
        ctk.CTkLabel(self, text="Behavior:", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
        
        self.pin_switch = ctk.CTkSwitch(self, text="Pin to Sidebar")
        if self.data.get("pinned", False): self.pin_switch.select()
        else: self.pin_switch.deselect()
        self.pin_switch.pack(pady=5)

        self.startup_switch = ctk.CTkSwitch(self, text="Run on App Launch")
        if self.data.get("startup", False): self.startup_switch.select()
        else: self.startup_switch.deselect()
        self.startup_switch.pack(pady=5)
        
        self.restart_switch = ctk.CTkSwitch(self, text="Auto-Restart on Crash")
        if self.data.get("auto_restart", False): self.restart_switch.select()
        else: self.restart_switch.deselect()
        self.restart_switch.pack(pady=5)

        ctk.CTkLabel(self, text="Window Size (Height):", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
        self.current_height = self.data.get("cli_height", 100)
        self.lbl_height = ctk.CTkLabel(self, text=f"{self.current_height} px")
        self.lbl_height.pack()
        self.height_slider = ctk.CTkSlider(self, from_=50, to=500, number_of_steps=9, command=self.update_height_label)
        self.height_slider.set(self.current_height)
        self.height_slider.pack(pady=5)

        ctk.CTkButton(self, text="SAVE SETTINGS", fg_color="#2ecc71", command=self.save_all).pack(side="bottom", pady=20, fill="x", padx=20)

    def update_height_label(self, value):
        self.lbl_height.configure(text=f"{int(value)} px")

    def save_all(self):
        content = self.manager.read_config(self.script_name)
        content["mode"] = self.mode_var.get()
        content["priority"] = PRIORITY_MAP[self.priority_var.get()]
        content["startup"] = bool(self.startup_switch.get())
        content["auto_restart"] = bool(self.restart_switch.get())
        content["pinned"] = bool(self.pin_switch.get()) 
        content["cli_height"] = int(self.height_slider.get())

        if self.manager.save_config(self.script_name, content):
            self.dashboard.setup_sidebar() 
            self.dashboard.refresh_list()
            self.destroy()
        else:
            messagebox.showerror("Error", "Could not save config.")

# --- MAIN APP ---
class DashboardApp(ctk.CTk):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.title("Command Center Pro")
        self.geometry("1000x650")

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.script_widgets = {}
        self.current_view_mode = "all"
        self.app_settings = self.load_app_settings()
        self.current_cli_color = self.app_settings.get("cli_color", "#00ff00")
        self.expanded_states = self.app_settings.get("expanded_states", {}) 
        
        self.global_font_size = self.app_settings.get("font_size", 12)
        self.global_tile_height = self.app_settings.get("tile_height", 28)

        ctk.set_appearance_mode(self.app_settings.get("theme", "Dark"))
        
        self.sidebar_expanded = self.app_settings.get("sidebar_expanded", True)
        self.sidebar_width_expanded = 140
        self.sidebar_width_collapsed = 48
        
        self.tray = SystemTray(self)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_sidebar()
        self.setup_main_frames()
        
        self.after(500, self.refresh_list) 
        self.after(1500, self.run_startup_scripts)
        self.select_view("Scripts")
        self.after(2000, self.update_resources)

    def load_app_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: pass
        # [NEW] Added script_order to store manual tile arrangement
        return {"cli_color": "#00ff00", "theme": "Dark", "sidebar_expanded": True, "minimize_to_tray": False, "expanded_states": {}, "font_size": 12, "tile_height": 28, "script_order": []}

    def save_app_settings(self):
        self.app_settings["expanded_states"] = self.expanded_states
        self.app_settings["font_size"] = self.global_font_size
        self.app_settings["tile_height"] = self.global_tile_height
        with open(SETTINGS_FILE, "w") as f: json.dump(self.app_settings, f, indent=4)

    def run_startup_scripts(self):
        startup_list = self.manager.get_available_scripts(filter_startup=True)
        for script in startup_list:
            if not self.manager.is_running(script):
                if script in self.script_widgets:
                    self.script_widgets[script]['switch'].select()
                    self.toggle_script(script)

    def update_resources(self):
        for script_name, widgets in self.script_widgets.items():
            if self.manager.is_running(script_name):
                if 'stats_label' in widgets:
                    try:
                        cpu, mem = self.manager.get_resource_usage(script_name)
                        widgets['stats_label'].configure(text=f"CPU: {cpu:.0f}% RAM: {mem:.0f}MB")
                    except: pass
            else:
                if 'stats_label' in widgets:
                     widgets['stats_label'].configure(text="")
        self.after(1000, self.update_resources)

    # --- SIDEBAR ---
    def setup_sidebar(self):
        width = self.sidebar_width_expanded if self.sidebar_expanded else self.sidebar_width_collapsed
        self.sidebar = ctk.CTkFrame(self, width=width, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.draw_sidebar_widgets()

    def draw_sidebar_widgets(self):
        for widget in self.sidebar.winfo_children(): widget.destroy()

        self.btn_menu = ctk.CTkButton(self.sidebar, text="☰", width=30, height=30,
                                      fg_color="transparent", hover_color=("gray70", "gray30"),
                                      font=("Segoe UI", 18), command=self.toggle_sidebar)
        self.btn_menu.pack(anchor="w", padx=9, pady=10)

        self.create_nav_btn("⚡", "Scripts", lambda: self.select_view("Scripts"))
        self.create_nav_btn("🚀", "Startup", lambda: self.select_view("Startup"))
        self.create_nav_btn("📝", "Editor", lambda: self.select_view("Editor"))
        self.create_nav_btn("📜", "Logs", lambda: self.select_view("Logs"))
        
        if self.sidebar_expanded:
            ctk.CTkLabel(self.sidebar, text="PINNED", font=("Segoe UI", 10, "bold"), text_color="gray").pack(anchor="w", padx=15, pady=(10, 0))
        else:
            ctk.CTkLabel(self.sidebar, text="-", font=("Segoe UI", 10, "bold"), text_color="gray").pack(pady=(10, 0))

        all_scripts = self.manager.get_available_scripts()
        for script in all_scripts:
            conf = self.manager.read_config(script)
            if conf.get("pinned", False):
                display = script.replace(".py", "")[:12]
                icon = "📌" 
                self.create_nav_btn(icon, display, lambda s=script: self.select_view(s))

        ctk.CTkLabel(self.sidebar, text="").pack(expand=True)
        
        self.create_nav_btn("⚙", "Settings", lambda: self.select_view("Settings"))

        btn_text = "+ NEW" if self.sidebar_expanded else "+"
        self.btn_new = ctk.CTkButton(self.sidebar, text=btn_text, fg_color="#2ecc71", hover_color="#27ae60",
                                     width=30 if not self.sidebar_expanded else 120,
                                     command=lambda: ScriptEditor(self, self.manager))
        self.btn_new.pack(fill="x" if self.sidebar_expanded else "none", padx=8, pady=20)

    def create_nav_btn(self, icon, text, command):
        full_text = f" {icon}   {text}"
        cfg = {"text": full_text if self.sidebar_expanded else icon, 
               "font": ("Segoe UI", 12, "bold") if self.sidebar_expanded else ("Segoe UI", 18),
               "anchor": "w" if self.sidebar_expanded else "center",
               "width": 120 if self.sidebar_expanded else 30}
        
        ctk.CTkButton(self.sidebar, command=command, fg_color="transparent", 
                      text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), 
                      height=35, **cfg).pack(fill="x", padx=5, pady=2)

    def toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        target_width = self.sidebar_width_expanded if self.sidebar_expanded else self.sidebar_width_collapsed
        self.sidebar.configure(width=target_width)
        self.draw_sidebar_widgets()
        self.app_settings["sidebar_expanded"] = self.sidebar_expanded
        self.save_app_settings()

    # --- MAIN FRAMES ---
    def setup_main_frames(self):
        self.frame_list_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self.header_frame = ctk.CTkFrame(self.frame_list_container, height=40, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=5)
        self.header_label = ctk.CTkLabel(self.header_frame, text="All Scripts", font=("Segoe UI", 18, "bold"))
        self.header_label.pack(side="left")
        ctk.CTkButton(self.header_frame, text="Refresh", width=60, height=25, command=self.refresh_list).pack(side="right")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame_list_container, label_text="")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.frame_editor = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        editor_head = ctk.CTkFrame(self.frame_editor, height=40, fg_color="transparent")
        editor_head.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(editor_head, text="Script Editor", font=("Segoe UI", 18, "bold")).pack(side="left")
        self.editor_filename = ctk.CTkEntry(editor_head, placeholder_text="script_name.py", width=200)
        self.editor_filename.pack(side="left", padx=10)
        ctk.CTkButton(editor_head, text="Load", width=60, command=self.editor_load).pack(side="left", padx=2)
        ctk.CTkButton(editor_head, text="Save", width=60, fg_color="#2ecc71", command=self.editor_save).pack(side="left", padx=2)
        self.editor_text = ctk.CTkTextbox(self.frame_editor, font=("Consolas", 13), wrap="none")
        self.editor_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.frame_logs = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(self.frame_logs, text="System Logs", font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=20, pady=20)
        self.sys_log_box = ctk.CTkTextbox(self.frame_logs, font=("Consolas", 12))
        self.sys_log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.sys_log_box.configure(state="disabled")

        self.frame_settings = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        ctk.CTkLabel(self.frame_settings, text="Settings", font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=20, pady=20)
        
        set_card = ctk.CTkFrame(self.frame_settings)
        set_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(set_card, text="Appearance Mode:", font=("Segoe UI", 14)).pack(side="left", padx=20, pady=20)
        ctk.CTkOptionMenu(set_card, values=["System", "Dark", "Light"], command=self.change_appearance_mode).pack(side="right", padx=20)

        color_card = ctk.CTkFrame(self.frame_settings)
        color_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(color_card, text="Console Text Color:", font=("Segoe UI", 14)).pack(side="left", padx=20, pady=20)
        self.color_var = ctk.StringVar(value="Hacker Green")
        ctk.CTkOptionMenu(color_card, values=list(CLI_COLORS.keys()), command=self.change_cli_color, variable=self.color_var).pack(side="right", padx=20)

        style_card = ctk.CTkFrame(self.frame_settings)
        style_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(style_card, text="Font Size:", font=("Segoe UI", 14)).pack(side="left", padx=20, pady=20)
        self.font_slider = ctk.CTkSlider(style_card, from_=8, to=24, number_of_steps=16, command=self.update_font_size)
        self.font_slider.set(self.global_font_size)
        self.font_slider.pack(side="right", padx=20, fill="x", expand=True)

        size_card = ctk.CTkFrame(self.frame_settings)
        size_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(size_card, text="Tile Height:", font=("Segoe UI", 14)).pack(side="left", padx=20, pady=20)
        self.tile_slider = ctk.CTkSlider(size_card, from_=20, to=60, number_of_steps=20, command=self.update_tile_size)
        self.tile_slider.set(self.global_tile_height)
        self.tile_slider.pack(side="right", padx=20, fill="x", expand=True)

        folder_card = ctk.CTkFrame(self.frame_settings)
        folder_card.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(folder_card, text="Scripts Location:", font=("Segoe UI", 14)).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(folder_card, text="Open Folder", command=self.open_scripts_folder).pack(side="right", padx=20)
        
        tray_card = ctk.CTkFrame(self.frame_settings)
        tray_card.pack(fill="x", padx=20, pady=10)
        self.tray_switch = ctk.CTkSwitch(tray_card, text="Minimize to Tray", command=self.toggle_tray_mode)
        if self.app_settings.get("minimize_to_tray", False): self.tray_switch.select()
        self.tray_switch.pack(anchor="w", padx=20, pady=10)

    def update_font_size(self, value):
        self.global_font_size = int(value)
        self.save_app_settings()
        self.refresh_list()

    def update_tile_size(self, value):
        self.global_tile_height = int(value)
        self.save_app_settings()
        self.refresh_list()

    def toggle_tray_mode(self):
        self.app_settings["minimize_to_tray"] = bool(self.tray_switch.get())
        self.save_app_settings()

    def select_view(self, name):
        self.frame_list_container.grid_forget()
        self.frame_editor.grid_forget()
        self.frame_logs.grid_forget()
        self.frame_settings.grid_forget()

        if name == "Scripts":
            self.frame_list_container.grid(row=0, column=1, sticky="nsew")
            self.header_label.configure(text="All Scripts")
            self.current_view_mode = "all"
            self.refresh_list()
        elif name == "Startup":
            self.frame_list_container.grid(row=0, column=1, sticky="nsew")
            self.header_label.configure(text="Startup Scripts")
            self.current_view_mode = "startup"
            self.refresh_list()
        elif name == "Editor":
            self.frame_editor.grid(row=0, column=1, sticky="nsew")
        elif name == "Logs":
            self.frame_logs.grid(row=0, column=1, sticky="nsew")
        elif name == "Settings":
            self.frame_settings.grid(row=0, column=1, sticky="nsew")
        else:
            self.frame_list_container.grid(row=0, column=1, sticky="nsew")
            self.header_label.configure(text=f"Script: {name}")
            self.current_view_mode = name 
            self.refresh_list()

    def open_editor_tab(self, script_name):
        self.select_view("Editor")
        self.editor_filename.delete(0, "end")
        self.editor_filename.insert(0, script_name)
        self.editor_load()

    def editor_load(self):
        name = self.editor_filename.get().strip()
        if not name: return
        content = self.manager.read_script_content(name)
        self.editor_text.delete("0.0", "end")
        self.editor_text.insert("0.0", content)

    def editor_save(self):
        name = self.editor_filename.get().strip()
        if not name: return
        content = self.editor_text.get("0.0", "end")
        if not os.path.exists(os.path.join(SCRIPTS_FOLDER, name)):
             if not name.endswith(".py"): name += ".py"
             self.manager.create_script(name)
        if self.manager.save_script_content(name, content):
            messagebox.showinfo("Saved", f"Saved {name}")
            self.refresh_list()
        else: messagebox.showerror("Error", "Failed to save")

    # =================================================================
    # --- DYNAMIC SORTING LOGIC ---
    # =================================================================
    
    def move_script(self, script_name, direction):
        """Moves a script up (-1) or down (1) in the custom array."""
        order = self.app_settings.get("script_order", [])
        if script_name not in order: return
        
        idx = order.index(script_name)
        new_idx = idx + direction
        
        # Ensure we stay within bounds
        if 0 <= new_idx < len(order):
            # Swap items
            order[idx], order[new_idx] = order[new_idx], order[idx]
            self.app_settings["script_order"] = order
            self.save_app_settings()
            self.refresh_list() # Redraw UI in new order

    def refresh_list(self):
        if self.current_view_mode == "startup":
            target_scripts = self.manager.get_available_scripts(filter_startup=True)
        elif self.current_view_mode == "all":
            target_scripts = self.manager.get_available_scripts(filter_startup=False)
        else:
            target_scripts = [self.current_view_mode]

        # [NEW] Sync and Update Custom Order
        all_avail = self.manager.get_available_scripts()
        current_order = self.app_settings.get("script_order", [])
        
        # 1. Remove deleted scripts from saved order
        current_order = [s for s in current_order if s in all_avail]
        # 2. Append any new scripts to the bottom of the list
        for s in all_avail:
            if s not in current_order:
                current_order.append(s)
                
        self.app_settings["script_order"] = current_order
        
        # Filter the ordered list down to what we actually want to show
        display_scripts = [s for s in current_order if s in target_scripts]

        # Hide old UI cards so we can repack them in the exact order
        for script_name in list(self.script_widgets.keys()):
            widget_data = self.script_widgets[script_name]
            if script_name not in target_scripts:
                 priority = self.manager.get_script_priority(script_name)
                 if priority == 1: widget_data['frame'].pack_forget()
                 else:
                     if not self.manager.is_running(script_name):
                         widget_data['frame'].destroy()
                         del self.script_widgets[script_name]
                     else: widget_data['frame'].pack_forget()
            else:
                 # Hide the frame so it can be re-packed in the new sorted order
                 widget_data['frame'].pack_forget() 

                 # Apply live size updates
                 conf = self.manager.read_config(script_name)
                 new_height = conf.get("cli_height", 100)
                 if widget_data.get('content_area'): widget_data['content_area'].configure(height=new_height)
                 if widget_data.get('console'): widget_data['console'].configure(height=new_height)

        # Draw / Re-pack the UI cards based on the Custom Sorted List
        for script in display_scripts:
            if script in self.script_widgets:
                self.script_widgets[script]['frame'].pack(fill="x", pady=2, padx=20) 
                sw = self.script_widgets[script]['switch']
                if self.manager.is_running(script): sw.select()
                else: sw.deselect()
                
                w = self.script_widgets[script]
                w['head'].configure(height=self.global_tile_height)
                
                if self.current_view_mode not in ["all", "startup"] and not self.expanded_states.get(script, False):
                    self.toggle_details(script)
            else:
                self.create_script_card(script)
                if self.current_view_mode not in ["all", "startup"]:
                    if not self.expanded_states.get(script, False):
                        self.toggle_details(script)

        if not target_scripts:
            for c in self.scroll_frame.winfo_children(): 
                if isinstance(c, ctk.CTkLabel): c.destroy()
            ctk.CTkLabel(self.scroll_frame, text="No scripts found.").pack(pady=40)

    def create_script_card(self, script_name):
        display = script_name.replace(".py", "").replace("_", " ").upper()
        conf = self.manager.read_config(script_name)
        prio = conf.get("priority", 3)
        mode = conf.get("mode", "cli")
        cli_height = conf.get("cli_height", 100)
        
        is_expanded = self.expanded_states.get(script_name, False)
        border_col = "#2ecc71" if prio == 1 else None 
        
        card = ctk.CTkFrame(self.scroll_frame, fg_color=("#EBEBEB", "#2b2b2b"), border_width=1 if prio==1 else 0, border_color=border_col)
        card.pack(fill="x", pady=2, padx=20) 

        head = ctk.CTkFrame(card, fg_color="transparent", height=self.global_tile_height)
        head.pack(fill="x", padx=5, pady=0)
        
        icon_char = "▼" if is_expanded else "▶"
        icon_lbl = ctk.CTkLabel(head, text=icon_char, font=("Arial", self.global_font_size - 2), width=15, height=self.global_tile_height)
        icon_lbl.pack(side="left")
        
        name_lbl = ctk.CTkLabel(head, text=display, font=("Segoe UI", self.global_font_size, "bold"), height=self.global_tile_height)
        name_lbl.pack(side="left", padx=5)
        
        if prio == 1: ctk.CTkLabel(head, text="[HIGH]", text_color="#2ecc71", font=("Segoe UI", self.global_font_size-4), height=self.global_tile_height).pack(side="left", padx=2)
        if mode == "widget": ctk.CTkLabel(head, text="[GUI]", text_color="#3498db", font=("Segoe UI", self.global_font_size-4), height=self.global_tile_height).pack(side="left", padx=2)
        
        stats_lbl = ctk.CTkLabel(head, text="", text_color="gray", font=("Consolas", self.global_font_size-3), height=self.global_tile_height)
        stats_lbl.pack(side="left", padx=10)

        btns = ctk.CTkFrame(head, fg_color="transparent", height=self.global_tile_height)
        btns.pack(side="right")
        
        dep_frame = ctk.CTkFrame(btns, fg_color="transparent", height=self.global_tile_height)
        dep_frame.pack(side="left", padx=2)

        btn_s = self.global_font_size + 8
        
        # [NEW] Move Up / Move Down Buttons
        ctk.CTkButton(btns, text="▲", width=20, height=btn_s-2, fg_color="#555", font=("Arial", self.global_font_size-2),
                      command=lambda s=script_name: self.move_script(s, -1)).pack(side="left", padx=1)
        ctk.CTkButton(btns, text="▼", width=20, height=btn_s-2, fg_color="#555", font=("Arial", self.global_font_size-2),
                      command=lambda s=script_name: self.move_script(s, 1)).pack(side="left", padx=1)

        ctk.CTkButton(btns, text="✏️", width=btn_s, height=btn_s-2, fg_color="#555", font=("Arial", self.global_font_size-2),
                      command=lambda s=script_name: self.open_editor_tab(s)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="⚙️", width=btn_s, height=btn_s-2, fg_color="#555", font=("Arial", self.global_font_size-2),
                      command=lambda s=script_name: self.open_config(s)).pack(side="left", padx=2)
        
        switch = ctk.CTkSwitch(btns, text="", width=btn_s+10, height=btn_s-6, switch_width=btn_s+10, switch_height=btn_s-8, command=lambda s=script_name: self.toggle_script(s))
        switch.pack(side="left", padx=5)
        if self.manager.is_running(script_name): switch.select()

        body = ctk.CTkFrame(card, fg_color="transparent")
        
        content_area = ctk.CTkFrame(body, fg_color="transparent", height=cli_height)
        content_area.pack(fill="x", padx=5, pady=2)
        if mode == "widget": content_area.pack_propagate(False)

        console = None
        if mode == "cli":
            console = ctk.CTkTextbox(content_area, height=cli_height, fg_color="#000000", text_color=self.current_cli_color, font=("Consolas", self.global_font_size))
            console.pack(fill="both", expand=True)
            console.configure(state="disabled")

            input_row = ctk.CTkFrame(body, fg_color="transparent", height=self.global_tile_height)
            input_row.pack(fill="x", padx=5, pady=(0, 5))
            entry = ctk.CTkEntry(input_row, placeholder_text="Command...", border_width=0, height=self.global_tile_height-2, font=("Segoe UI", self.global_font_size))
            entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            entry.bind("<Return>", lambda e, s=script_name, en=entry: self.send_command(s, en))
            ctk.CTkButton(input_row, text="➤", width=btn_s, height=btn_s-2, fg_color="#444", 
                          command=lambda s=script_name, en=entry: self.send_command(s, en)).pack(side="right")

        for w in [head, name_lbl, icon_lbl]:
            w.bind("<Button-1>", lambda e, s=script_name: self.toggle_details(s))

        if is_expanded:
            body.pack(fill="x", expand=True)
        
        self.script_widgets[script_name] = {
            "frame": card, "head": head, "body": body, "icon": icon_lbl,
            "switch": switch, "console": console, 
            "content_area": content_area, "stats_label": stats_lbl,
            "dep_frame": dep_frame
        }

    def toggle_details(self, script_name):
        widgets = self.script_widgets.get(script_name)
        if not widgets: return
        body = widgets['body']
        icon = widgets['icon']
        if body.winfo_ismapped():
            body.pack_forget()
            icon.configure(text="▶")
            self.expanded_states[script_name] = False
        else:
            body.pack(fill="x", expand=True)
            icon.configure(text="▼")
            self.expanded_states[script_name] = True
        self.save_app_settings()

    def toggle_script(self, script_name):
        widgets = self.script_widgets.get(script_name)
        if not widgets: return
        
        if widgets['switch'].get() == 1:
            if not self.manager.is_running(script_name):
                self.manager.start_script(
                    script_name, 
                    self.update_console, 
                    self.on_process_exit, 
                    widgets['content_area'],
                    self.on_missing_dependency 
                )
        else:
            if self.manager.is_running(script_name):
                self.manager.stop_script(script_name)
                for child in widgets['content_area'].winfo_children():
                    if child != widgets.get('console'): child.destroy()

    def on_missing_dependency(self, script_name, package_name):
        self.after(0, lambda: self._show_install_button(script_name, package_name))

    def _show_install_button(self, script_name, package_name):
        widgets = self.script_widgets.get(script_name)
        if not widgets: return
        for w in widgets['dep_frame'].winfo_children(): w.destroy()
        btn = ctk.CTkButton(widgets['dep_frame'], text=f"Install '{package_name}'", fg_color="#e67e22", text_color="white", height=20, width=80, font=("Segoe UI", 10),
                            command=lambda: self.run_install(script_name, package_name))
        btn.pack()
        messagebox.showwarning("Dependency Missing", f"Script '{script_name}' needs '{package_name}'")

    def run_install(self, script_name, package_name):
        self.update_console(script_name, f"\n[SYSTEM] Starting installation of {package_name}...\n")
        self.manager.install_package(package_name, lambda msg: self.update_console(script_name, msg))
        widgets = self.script_widgets.get(script_name)
        if widgets:
            for w in widgets['dep_frame'].winfo_children(): w.destroy()

    def on_process_exit(self, script_name):
        self.after(0, lambda: self._handle_exit_ui(script_name))

    def _handle_exit_ui(self, script_name):
        if script_name in self.script_widgets:
            try:
                self.script_widgets[script_name]['switch'].deselect()
                self.script_widgets[script_name]['stats_label'].configure(text="")
            except: pass

    def on_closing(self):
        if self.app_settings.get("minimize_to_tray", False):
            self.withdraw()
            self.tray.run() 
        else:
            self.quit_app_fully()

    def restore_window(self):
        self.deiconify()

    def quit_app_fully(self):
        self.destroy()

    def open_config(self, s): ConfigEditor(self, self.manager, s)
    
    def send_command(self, s, entry):
        self.manager.send_input(s, entry.get())
        self.update_console(s, f"> {entry.get()}\n")
        entry.delete(0, "end")

    def update_console(self, script_name, text):
        if script_name in self.script_widgets:
            c = self.script_widgets[script_name]['console']
            if c: 
                try:
                    if not c.winfo_exists(): return
                    def _u():
                        try:
                            c.configure(state="normal")
                            c.insert("end", text)
                            c.see("end")
                            c.configure(state="disabled")
                        except TclError: pass
                    self.after(0, _u)
                except: pass

    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.app_settings["theme"] = new_mode
        self.save_app_settings()

    def change_cli_color(self, color_name):
        new_hex = CLI_COLORS[color_name]
        self.app_settings["cli_color"] = new_hex
        self.save_app_settings()
        for w in self.script_widgets.values():
            if w['console']: w["console"].configure(text_color=new_hex)

    def open_scripts_folder(self):
        if platform.system() == "Windows": os.startfile(SCRIPTS_FOLDER)
        elif platform.system() == "Darwin": subprocess.Popen(["open", SCRIPTS_FOLDER])
        else: subprocess.Popen(["xdg-open", SCRIPTS_FOLDER])

    # =================================================================
    # --- MINI TRAY DASHBOARD LOGIC ---
    # =================================================================
    
    def show_mini_dashboard(self):
        if hasattr(self, "mini_dash") and self.mini_dash and self.mini_dash.winfo_exists():
            self.mini_dash.destroy()
            return

        self.mini_dash = ctk.CTkToplevel(self)
        self.mini_dash.title("Quick Controls")
        
        self.mini_dash.overrideredirect(True) 
        self.mini_dash.attributes("-topmost", True)
        self.mini_dash.configure(fg_color=("#EBEBEB", "#2b2b2b"), border_width=1, border_color="#555")

        width = 280
        height = 350
        x_pos = self.winfo_screenwidth() - width - 20
        y_pos = self.winfo_screenheight() - height - 60
        self.mini_dash.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

        head = ctk.CTkFrame(self.mini_dash, corner_radius=0, fg_color=("gray80", "gray15"))
        head.pack(fill="x")
        ctk.CTkLabel(head, text="Active Automations", font=("Segoe UI", 14, "bold")).pack(pady=10)

        scroll = ctk.CTkScrollableFrame(self.mini_dash, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        running_scripts = [s for s in self.manager.get_available_scripts() if self.manager.is_running(s)]

        if not running_scripts:
            ctk.CTkLabel(scroll, text="No scripts running right now.", text_color="gray").pack(pady=20)
        else:
            for script in running_scripts:
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(fill="x", pady=2)

                ctk.CTkLabel(row, text="🟢", text_color="#2ecc71", font=("Arial", 10)).pack(side="left")
                display_name = script.replace(".py", "")[:18]
                ctk.CTkLabel(row, text=display_name, font=("Segoe UI", 12)).pack(side="left", padx=5)

                ctk.CTkButton(row, text="Stop", width=40, height=20, fg_color="#e74c3c", hover_color="#c0392b",
                              command=lambda s=script: self.stop_from_mini(s)).pack(side="right")

        btn_frame = ctk.CTkFrame(self.mini_dash, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Open Full Dashboard", fg_color="#3498db", 
                      command=self.restore_from_mini).pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Close Menu", fg_color="#555", 
                      command=self.mini_dash.destroy).pack(fill="x", pady=2)

    def stop_from_mini(self, script_name):
        self.manager.stop_script(script_name)
        self.after(200, self.show_mini_dashboard)
        if script_name in self.script_widgets:
            self.script_widgets[script_name]['switch'].deselect()

    def restore_from_mini(self):
        if hasattr(self, "mini_dash") and self.mini_dash:
            self.mini_dash.destroy()
        self.tray.stop()
        self.deiconify()

if __name__ == "__main__":
    app_manager = ScriptManager()
    app = DashboardApp(app_manager)
    app.mainloop()