# ⚡ Command Center Pro

**A Modular Process Orchestration & Automation Dashboard**

Command Center Pro is a robust, GUI-based desktop environment designed to manage, monitor, and develop Python automation scripts from a single unified interface. Built to replace the chaos of running multiple terminal windows, it acts as a lightweight "mini-operating system" for your scripts, providing real-time resource monitoring, crash recovery, and integrated development tools.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Architecture & Under the Hood](#-architecture--under-the-hood)
3. [Installation](#%EF%B8%8F-installation)
4. [Usage Guide](#-usage-guide)
5. [Creating a Widget-Mode Script](#%EF%B8%8F-creating-a-widget-mode-script)
6. [Project Structure](#-project-structure)
7. [Tech Stack](#-tech-stack)

---

## 🚀 Key Features

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

## 🧠 Architecture & Under the Hood

This project is built using a strict **Model-View-Controller (MVC)** pattern to ensure stability:
* **The Backend (`script_manager.py`):** Handles process creation (`subprocess.Popen`), I/O piping, and multithreading. It uses `os.read` with unbuffered binary pipes to capture output byte-by-byte, preventing the dreaded Tkinter UI freeze when scripts ask for user input.
* **The Frontend (`dashboard.py`):** A fully threaded, High-DPI aware GUI built with `customtkinter`. UI updates from background threads are safely routed to the main thread event loop using `.after()` callbacks.

---

## 🛠️ Installation

**Prerequisites:** Python 3.8+ installed on your system.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/command-center-pro.git](https://github.com/yourusername/command-center-pro.git)
   cd command-center-pro