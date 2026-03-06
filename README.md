# Command Center Pro

**A Modular Process Orchestration & Automation Dashboard**

Command Center Pro is a robust, GUI-based desktop environment designed to manage, monitor, and develop Python automation scripts from a single unified interface. Built to replace the chaos of running multiple terminal windows, it acts as a lightweight "mini-operating system" for your scripts, providing real-time resource monitoring, crash recovery, and integrated development tools.

---

## Table of Contents
1. [Key Features](#-key-features)
2. [Architecture & Under the Hood](#-architecture--under-the-hood)
3. [Installation](#%EF%B8%8F-installation)
4. [Usage Guide](#-usage-guide)
5. [Creating a Widget-Mode Script](#%EF%B8%8F-creating-a-widget-mode-script)
6. [Project Structure](#-project-structure)
7. [Tech Stack](#-tech-stack)

---

## Key Features

### 1. Dual Execution Modes
* **CLI Mode:** Runs scripts in a headless background environment while routing `stdout` and `stdin` to a real-time, non-blocking terminal emulator built into the app's script cards.
* **Widget Mode:** Dynamically loads external Python scripts as modules, allowing them to inject custom GUI elements (buttons, graphs, labels) directly into the dashboard.

### 2. System Health & Resilience
* **Real-Time Resource Monitoring:** Utilizes `psutil` to track live CPU (%) and Memory (MB) consumption for every running script without blocking the main UI thread.
* **Self-Healing Watchdog:** Automatically monitors process exit codes. If a priority script crashes, the manager automatically restarts it.
* **Smart Dependency Resolver:** A background thread scans script logs using Regex. If a `ModuleNotFoundError` is detected, the UI instantly generates a one-click `pip install` button for the missing package.

### 3. Integrated Workspace
* **Built-in IDE:** Create, modify, and save Python scripts on the fly using the integrated code editor tab.
* **Pin to Sidebar:** Pin frequently used scripts to the navigation bar to give them a dedicated, focused workspace.
* **Collapsible UI & Global Scaling:** Scripts are contained in accordion-style tiles. The entire UI's font size and density can be scaled dynamically from the Settings tab.

### 4. Native OS Integration
* **System Tray Background Agent:** Minimizes to the taskbar to keep your desktop clean while automations run continuously.
* **Borderless Quick Controls:** Left-clicking the tray icon opens a sleek, floating mini-dashboard just above the Windows taskbar, allowing you to instantly view and stop active tasks.

---

## Architecture & Under the Hood

This project is built using a strict **Model-View-Controller (MVC)** pattern to ensure stability:
* **The Backend (`script_manager.py`):** Handles process creation (`subprocess.Popen`), I/O piping, and multithreading. It uses `os.read` with unbuffered binary pipes to capture output byte-by-byte, preventing the dreaded Tkinter UI freeze when scripts ask for user input.
* **The Frontend (`dashboard.py`):** A fully threaded, High-DPI aware GUI built with `customtkinter`. UI updates from background threads are safely routed to the main thread event loop using `.after()` callbacks.

---

## Installation

**Prerequisites:** Python 3.8+ installed on your system.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Jayantraj299/Command-Center-Pro.git
   cd command-center-pro

1. **Install the dependencies:**
   *(Required packages: `customtkinter`, `psutil`, `pystray`, `pillow`)*
   ```bash
   pip install -r requirements.txt
3. **Run the Application:**
    ```bash
    python dashboard.py
---

## Usage Guide

### Managing Scripts

1. Click **+ NEW** in the sidebar or go to the **Editor** tab.
2. Name your file (e.g., `server_ping.py`), write your code, and click **SAVE**.
3. Go to the **Scripts** tab to see your new script card. Toggle the switch to run it!

### Configuring Scripts

Click the **Gear Icon (⚙️)** on any script card to open its settings:

- **Display Mode:** Toggle between `cli` (terminal) and `widget` (GUI).
- **Priority:** Sorts your scripts (High priority scripts appear at the top).
- **Run on App Launch:** Start this script automatically when Command Center opens.
- **Auto-Restart:** Enable the Watchdog feature for crash recovery.
- **Pin to Sidebar:** Add a quick-access shortcut to the sidebar navigation.

---

## Creating a "Widget-Mode" Script

Want your script to have buttons and sliders instead of just printing text? Create a new script and define a `Widget` class that inherits from `ctk.CTkFrame`.

The dashboard will automatically find this class and render it inside the script card!

**Example `clock_widget.py`:**

Python

```python
import customtkinter as ctk
import time

class Widget(ctk.CTkFrame):
    def __init__(self, parent):
        # Initialize the frame inside the parent dashboard card
        super().__init__(parent, fg_color="transparent")
        
        # Build your UI
        self.lbl_time = ctk.CTkLabel(self, text="00:00:00", font=("Consolas", 40, "bold"), text_color="#3498db")
        self.lbl_time.pack(expand=True, pady=20)
        
        # Start the clock loop
        self.update_clock()

    def update_clock(self):
        current_time = time.strftime("%H:%M:%S")
        self.lbl_time.configure(text=current_time)
        self.after(1000, self.update_clock) # Update every 1 second
```

*Don't forget to change the script's display mode to `widget` in its settings!*

---

## Project Structure
```bash

📁 command-center-pro/
│
├── dashboard.py         # Main Frontend GUI & Event Loop
├── script_manager.py    # Backend Threading, Subprocesses & Logic
├── taskbar_tray.py      # Background System Tray Agent & Mini-Dash
├── requirements.txt     # Python dependencies
├── settings.json        # Global application state and styling
│
├── 📁 scripts/          # Directory for all user Python scripts
│   ├── example.py
│   └── example.json     # Auto-generated isolated config for example.py
│
└── 📁 logs/             # Persistent stdout/stderr logs for processes`
```
---

## Tech Stack

- **Language:** Python 3
- **GUI Framework:** CustomTkinter
- **Concurrency:** `threading`, non-blocking `os.read`
- **Process Management:** `subprocess`, `importlib`
- **System Monitoring:** `psutil`
- **Background Agent:** `pystray`, `Pillow`
