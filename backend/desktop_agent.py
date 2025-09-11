import os
import time
import requests
from datetime import datetime
from PIL import ImageGrab
import psutil
import win32gui, win32process  # only works on Windows

API_BASE = "https://test-8d3m.onrender.com"
EMAIL = "shehneel.khan@datapillar.co.uk"
PASSWORD = "abcd1234"

class DesktopAgent:
    def __init__(self):
        self.token = None

    def login(self):
        resp = requests.post(f"{API_BASE}/api/login", json={
            "username": EMAIL,
            "password": PASSWORD
        })
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            print("✅ Logged in")
        else:
            print(resp.text)
            raise Exception("Login failed")

    def get_active_window(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name(), window_title
        except Exception:
            return "Unknown", "Unknown"

    def capture_and_send(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

        img = ImageGrab.grab()
        img.save(filename)

        app, title = self.get_active_window()

        data = {
            "application": app,
            "window_title": title,
            "timestamp": timestamp
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        with open(filename, "rb") as f:
            files = {"screenshot": f}
            resp = requests.post(f"{API_BASE}/api/upload-screenshot", 
                                files=files, data=data, headers=headers)

        print("📤 Uploaded:", resp.status_code)
        os.remove(filename)


    def run(self):
        self.login()
        while True:
            self.capture_and_send()
            time.sleep(5)  # every 60s

if __name__ == "__main__":
    DesktopAgent().run()
