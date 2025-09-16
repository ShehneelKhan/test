import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from desktop_agent import DesktopAgent  # use updated DesktopAgent (login with email/password)

def center_window(win, width, height):
    """Position the window at the center of the screen."""
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

# ---------------- LOGIN WINDOW ----------------
class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.root.title("🔑 Login")
        WIDTH, HEIGHT = 500, 220
        center_window(self.root, WIDTH, HEIGHT)
        self.root.resizable(False, False)

        self.agent = DesktopAgent()
        self.on_success = on_success  # callback to launch main window

        # --- Create a grid with spacers so the content is truly centered ---
        # Root grid: 3x3 (top spacer / content / bottom spacer) x (left spacer / content / right spacer)
        self.root.grid_rowconfigure(0, weight=1)   # top spacer
        self.root.grid_rowconfigure(1, weight=0)   # content
        self.root.grid_rowconfigure(2, weight=1)   # bottom spacer
        self.root.grid_columnconfigure(0, weight=1)  # left spacer
        self.root.grid_columnconfigure(1, weight=0)  # content
        self.root.grid_columnconfigure(2, weight=1)  # right spacer

        # Card (center area)
        card = ttk.Frame(self.root, padding=(18, 12))
        # card.grid(row=1, column=1, sticky="nsew")
        card.grid(row=1, column=0, columnspan=2, sticky="w", padx=80)


        # Layout inside card using grid (no mixing geometry managers)
        card.grid_columnconfigure(0, weight=0)
        card.grid_columnconfigure(1, weight=1)
        # card.grid_columnconfigure(2, weight=1)   # spacer -> pushes form left


        # Title (centered by spanning 2 columns)
        title = ttk.Label(card, text="Desktop Agent Login", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w", padx=50)


        # Email row
        ttk.Label(card, text="Email:").grid(row=1, column=0, sticky="e", padx=0, pady=6)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(card, textvariable=self.email_var, width=32)
        self.email_entry.grid(row=1, column=1, sticky="w", pady=2)

        # Password row
        ttk.Label(card, text="Password:").grid(row=2, column=0, sticky="e", padx=0, pady=6)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(card, textvariable=self.password_var, width=32, show="*")
        self.password_entry.grid(row=2, column=1, sticky="w", pady=2)

        # Login button centered by spanning both columns; sticky="" keeps it centered
        login_btn = ttk.Button(card, text="Login", command=self.login)
        login_btn.grid(row=3, column=0, columnspan=2, pady=(14, 0))

        # UX niceties
        self.email_entry.focus_set()
        self.root.bind("<Return>", lambda e: self.login())

    def login(self):
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()

        if not email or not password:
            messagebox.showwarning("Missing Info", "Please enter email and password.")
            return

        try:
            self.agent.login(email, password)
            messagebox.showinfo("Login", "✅ Login successful.")
            self.root.destroy()  # close login window
            self.on_success(self.agent)  # launch agent window
        except Exception as e:
            messagebox.showerror("Login Failed", str(e))



# ---------------- MAIN AGENT WINDOW ----------------
class AgentWindow:
    def __init__(self, agent):
        self.root = tk.Tk()
        self.root.title("📡 Desktop Agent")
        self.root.geometry("600x450")
        self.root.resizable(False, False)

        self.agent = agent
        self.running = False
        self.thread = None

        # ---- Styles ----
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 11), padding=8)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10))

        # ---- Header ----
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="Desktop Agent Dashboard", style="Header.TLabel").pack(side="left")
        self.status_lbl = ttk.Label(header_frame, text="🔴 Not Started", style="Status.TLabel", foreground="red")
        self.status_lbl.pack(side="right")

        # ---- Buttons ----
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")

        self.start_btn = ttk.Button(btn_frame, text="▶️ Start", command=self.start_agent)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_agent, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.exit_btn = ttk.Button(btn_frame, text="❌ Exit", command=self.root.quit)
        self.exit_btn.pack(side="right", padx=5)

        # ---- Log Area ----
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#dcdcdc",
            insertbackground="white",
            state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)

    def log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, f"{msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def start_agent(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_agent, daemon=True)
            self.thread.start()
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_lbl.config(text="🟢 Running", foreground="green")
            self.log("▶️ Agent started...")

    def stop_agent(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_lbl.config(text="🔴 Stopped", foreground="red")
        self.log("⏹ Agent stopped.")

    def run_agent(self):
        while self.running:
            try:
                self.agent.capture_and_send()
                self.log("📤 Screenshot uploaded.")
            except Exception as e:
                self.log(f"⚠️ Error: {e}")
            time.sleep(5)

    def run(self):
        self.root.mainloop()


# ---------------- APP ENTRY ----------------
def launch_main_window(agent):
    app = AgentWindow(agent)
    app.run()

if __name__ == "__main__":
    # Start only login window first
    login_root = tk.Tk()
    LoginWindow(login_root, on_success=launch_main_window)
    login_root.mainloop()
