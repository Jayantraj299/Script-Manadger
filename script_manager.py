# script_manager.py
import subprocess
import sys
import threading
import os
import glob
import json
import datetime
import time
import psutil
import importlib.util
import re 

# --- BACKEND CONFIGURATION ---
SCRIPTS_FOLDER = "scripts"
LOGS_FOLDER = "logs"

PRIORITY_MAP = {"High": 1, "Medium": 2, "Low": 3}
REV_PRIORITY_MAP = {1: "High", 2: "Medium", 3: "Low"}

class ScriptManager:
    def __init__(self):
        self.processes = {} 
        self.monitors = {} # NEW: Cache for psutil process objects
        self.widgets = {}
        
        if not os.path.exists(SCRIPTS_FOLDER): os.makedirs(SCRIPTS_FOLDER)
        if not os.path.exists(LOGS_FOLDER): os.makedirs(LOGS_FOLDER)

    # --- FILE OPERATIONS ---
    def create_script(self, name):
        if not name.endswith(".py"): name += ".py"
        path = os.path.join(SCRIPTS_FOLDER, name)
        if os.path.exists(path): return False, "File exists"
        with open(path, "w", encoding="utf-8") as f:
            f.write("# New Script\nimport time\n\nwhile True:\n    print('Running...')\n    time.sleep(1)\n")
        return True, path

    def read_script_content(self, name):
        path = os.path.join(SCRIPTS_FOLDER, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return f.read()
        return ""

    def save_script_content(self, name, content):
        path = os.path.join(SCRIPTS_FOLDER, name)
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(content)
            return True
        except: return False

    # --- CONFIG ---
    def get_config_path(self, script_name):
        base_name = os.path.splitext(script_name)[0]
        return os.path.join(SCRIPTS_FOLDER, f"{base_name}.json")

    def read_config(self, script_name):
        path = self.get_config_path(script_name)
        if not os.path.exists(path): return {}
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}

    def save_config(self, script_name, data):
        path = self.get_config_path(script_name)
        try:
            with open(path, "w", encoding="utf-8") as f: 
                json.dump(data, f, indent=4)
            return True
        except: return False

    def get_script_priority(self, script_name):
        return self.read_config(script_name).get("priority", 3)

    def is_startup_script(self, script_name):
        return self.read_config(script_name).get("startup", False)

    def get_available_scripts(self, filter_startup=False):
        files = glob.glob(os.path.join(SCRIPTS_FOLDER, "*.py"))
        scripts = [os.path.basename(f) for f in files]
        if filter_startup:
            scripts = [s for s in scripts if self.is_startup_script(s)]
        scripts.sort(key=self.get_script_priority)
        return scripts

    # --- EXECUTION ---
    def is_running(self, script_name):
        proc = self.processes.get(script_name)
        if proc and proc.poll() is None: return True
        if self.widgets.get(script_name): return True
        return False

    def start_script(self, script_name, output_callback, exit_callback=None, widget_frame=None, dep_callback=None):
        config = self.read_config(script_name)
        mode = config.get("mode", "cli")

        if self.is_running(script_name): return False, "Already running"

        if mode == "widget":
            return self._start_widget(script_name, widget_frame)
        else:
            return self._start_cli(script_name, output_callback, exit_callback, config, dep_callback)

    def _start_widget(self, script_name, parent_frame):
        try:
            path = os.path.join(SCRIPTS_FOLDER, script_name)
            spec = importlib.util.spec_from_file_location(script_name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[script_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "Widget"):
                widget_instance = module.Widget(parent_frame)
                widget_instance.pack(fill="both", expand=True)
                self.widgets[script_name] = widget_instance
                return True, "Widget Loaded"
            else:
                return False, "Missing 'class Widget(ctk.CTkFrame)'"
        except Exception as e:
            return False, str(e)

    def _start_cli(self, script_name, output_callback, exit_callback, config, dep_callback):
        path = os.path.join(SCRIPTS_FOLDER, script_name)
        try:
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = "utf-8"
            my_env["PYTHONUNBUFFERED"] = "1" 

            proc = subprocess.Popen(
                [sys.executable, "-u", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=False,
                bufsize=0,
                env=my_env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.processes[script_name] = proc
            
            # [FIX] Initialize psutil monitor here to capture history
            try:
                self.monitors[script_name] = psutil.Process(proc.pid)
            except: pass
            
            auto_restart = config.get("auto_restart", False)

            threading.Thread(target=self._monitor_output, 
                             args=(script_name, proc, output_callback, exit_callback, auto_restart, dep_callback), 
                             daemon=True).start()
            return True, f"PID: {proc.pid}"
        except Exception as e:
            return False, str(e)

    def stop_script(self, script_name):
        proc = self.processes.get(script_name)
        if proc:
            proc.terminate()
            if script_name in self.monitors: del self.monitors[script_name] # Cleanup
            return True
        
        widget = self.widgets.get(script_name)
        if widget:
            try:
                widget.destroy()
                del self.widgets[script_name]
                if script_name in sys.modules: del sys.modules[script_name]
                return True
            except: pass
        return False

    def send_input(self, script_name, text):
        proc = self.processes.get(script_name)
        if proc and proc.stdin:
            try:
                input_bytes = (text + "\n").encode("utf-8")
                proc.stdin.write(input_bytes)
                proc.stdin.flush()
                return True
            except: return False
        return False

    def get_resource_usage(self, script_name):
        # [FIX] Use cached monitor to get accurate CPU %
        if script_name in self.monitors:
            try:
                p = self.monitors[script_name]
                # Check if still running
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    # interval=None calculates since last call
                    cpu = p.cpu_percent(interval=None) 
                    mem = p.memory_info().rss / (1024 * 1024) 
                    return cpu, mem
            except: pass
        return 0, 0

    # --- DEPENDENCY INSTALLER ---
    def install_package(self, package_name, output_callback):
        def _install():
            try:
                output_callback(f"Installing {package_name}...\n")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                output_callback(f"Successfully installed {package_name}!\n")
            except Exception as e:
                output_callback(f"Failed to install: {e}\n")
        
        threading.Thread(target=_install, daemon=True).start()

    def _monitor_output(self, name, proc, callback, exit_callback, auto_restart, dep_callback):
        log_file_path = os.path.join(LOGS_FOLDER, f"{os.path.splitext(name)[0]}.log")
        
        try:
            with open(log_file_path, "ab") as log_file:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"\n--- SESSION STARTED: {timestamp} ---\n".encode("utf-8"))
                
                while True:
                    try:
                        data = os.read(proc.stdout.fileno(), 1024)
                    except OSError: break

                    if not data:
                        if proc.poll() is not None: break
                        continue

                    text_chunk = data.decode("utf-8", errors="replace")
                    callback(name, text_chunk)
                    
                    if dep_callback and "ModuleNotFoundError" in text_chunk:
                        match = re.search(r"No module named '(\w+)'", text_chunk)
                        if match:
                            missing_pkg = match.group(1)
                            dep_callback(name, missing_pkg) 

                    log_file.write(data)
                    log_file.flush()
                
                log_file.write(f"--- PROCESS EXITED: {proc.poll()} ---\n".encode("utf-8"))

        except: pass

        if proc.stdout: proc.stdout.close()
        callback(name, f"[Process exited with code {proc.poll()}]\n")
        
        if auto_restart and proc.poll() != 0:
             pass 

        if exit_callback: exit_callback(name)