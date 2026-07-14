import os
import subprocess
import webbrowser
import pyautogui
import time
import psutil
import requests


class JarvisHands:
    def __init__(self):
        self.tool_map = {
            "open_website": self.open_website,
            "launch_app": self.launch_app,
            "take_screenshot": self.take_screenshot,
            "search_files": self.search_files,
            "get_system_health": self.get_system_health,
            "get_weather": self.get_weather,
            "add_reminder": self.add_reminder,
            "get_reminders": self.get_reminders,
            "run_shell_command": self.run_shell_command,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "search_web": self.search_web,
            "control_media": self.control_media,
            "set_volume": self.set_volume,
            "set_brightness": self.set_brightness,
            "clipboard": self.clipboard,
            "find_file_advanced": self.find_file_advanced,
        }

    def execute(self, tool_name, **kwargs):
        if tool_name in self.tool_map:
            try:
                return self.tool_map[tool_name](**kwargs)
            except TypeError as e:
                return f"Parameter error for {tool_name}: {e}"
            except Exception as e:
                return f"Tool '{tool_name}' failed: {e}"
        return f"Unknown tool: {tool_name}"

    def open_website(self, url):
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url}"

    def launch_app(self, app_name):
        try:
            subprocess.run(["open", "-a", app_name], check=True)
            return f"Launching {app_name}"
        except Exception as e:
            return f"Could not launch {app_name}: {str(e)}"

    def take_screenshot(self, filename="screenshot.png"):
        pyautogui.screenshot(filename)
        return f"Screenshot saved as {filename}"

    def search_files(self, query):
        pyautogui.hotkey('command', 'space')
        time.sleep(0.3)
        pyautogui.write(query)
        pyautogui.press('enter')
        return f"Searching for {query} on your system."

    def get_system_health(self):
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        battery = psutil.sensors_battery()
        batt_str = f"{battery.percent}% {'(Charging)' if battery.power_plugged else '(Discharging)'}" if battery else "N/A"
        return f"CPU: {cpu}% | RAM: {ram}% | Disk: {disk}% | Battery: {batt_str}"

    def get_weather(self, city="Hyderabad"):
        try:
            response = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
            if response.status_code == 200:
                return response.text.strip()
            return "Could not fetch weather data."
        except Exception:
            return "Weather service currently unavailable."

    def add_reminder(self, task):
        os.makedirs("data", exist_ok=True)
        with open("data/reminders.txt", "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M')}] {task}\n")
        return f"Reminder added: '{task}'"

    def get_reminders(self):
        path = "data/reminders.txt"
        if not os.path.exists(path):
            return "No reminders at the moment."
        with open(path, "r") as f:
            lines = f.readlines()
        if not lines:
            return "Reminder list is empty."
        return "Your reminders:\n" + "".join(lines)

    def run_shell_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
            return output[:2000] if output else "Command executed successfully."
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Failed: {str(e)}"

    def read_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()[:5000]
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write_file(self, filepath, content):
        try:
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def list_directory(self, path="."):
        try:
            entries = []
            for entry in os.listdir(path):
                full = os.path.join(path, entry)
                prefix = "  " if os.path.isdir(full) else "  "
                entries.append(f"{prefix}{entry}")
            return "\n".join(entries) if entries else "Directory is empty."
        except Exception as e:
            return f"Error: {str(e)}"

    def search_web(self, query):
        try:
            url = f"https://google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Opened Google search for '{query}'"
        except Exception as e:
            return f"Web search failed: {e}"

    def control_media(self, action):
        try:
            if action in ("play", "pause"):
                subprocess.run(["osascript", "-e",
                    'tell application "System Events" to key code 49'])
                return f"Media {action} toggled."
            elif action == "next":
                subprocess.run(["osascript", "-e",
                    'tell application "System Events" to key code 124 using command down'])
                return "Skipped to next track."
            elif action == "previous":
                subprocess.run(["osascript", "-e",
                    'tell application "System Events" to key code 123 using command down'])
                return "Went to previous track."
            return f"Unknown media action: {action}"
        except Exception as e:
            return f"Media control failed: {e}"

    def set_volume(self, level):
        try:
            level = max(0, min(100, int(level)))
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
            return f"Volume set to {level}%"
        except Exception as e:
            return f"Volume control failed: {e}"

    def set_brightness(self, level):
        try:
            level = max(0, min(100, int(level)))
            subprocess.run(["brightness", str(level / 100)], timeout=5)
            return f"Brightness set to {level}%"
        except FileNotFoundError:
            try:
                steps = level // 10
                subprocess.run(["osascript", "-e",
                    f'tell application "System Events" to repeat {steps} times\n'
                    'key code 144\nend repeat'])
                return f"Adjusting brightness to ~{level}%"
            except Exception as e:
                return f"Brightness control unavailable: {e}"
        except Exception as e:
            return f"Brightness control failed: {e}"

    def clipboard(self, action, text=None):
        import pyperclip
        if action == "copy" and text:
            pyperclip.copy(text)
            return "Copied to clipboard."
        elif action == "paste":
            return pyperclip.paste()
        return "Invalid clipboard action."

    def find_file_advanced(self, name, start_path=None):
        if start_path is None:
            start_path = os.path.expanduser("~")
        try:
            cmd = f'find "{start_path}" -name "*{name}*" -maxdepth 3 -not -path "*/.*" -not -path "*/venv*" -not -path "*/__pycache__*"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout.strip()
            return output if output else "No matching files found."
        except Exception as e:
            return f"Search failed: {e}"

    def get_available_tools(self):
        return list(self.tool_map.keys())

    def get_tool_descriptions(self):
        descs = []
        for name, func in self.tool_map.items():
            doc = (func.__doc__ or "").strip().split("\n")[0]
            descs.append(f"- {name}: {doc}")
        return "\n".join(descs)
