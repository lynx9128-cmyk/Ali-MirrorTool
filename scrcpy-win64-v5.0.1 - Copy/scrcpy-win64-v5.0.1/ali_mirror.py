import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import re
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
ADB = os.path.join(BASE, "adb.exe")
SCRCPY = os.path.join(BASE, "scrcpy.exe")
APP_TITLE = "Ali Wireless Mirror"

def run_cmd(args, timeout=20):
    try:
        return subprocess.run(
            args, cwd=BASE, capture_output=True, text=True,
            timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    except subprocess.TimeoutExpired:
        return None
    except Exception as exc:
        return exc

def set_status(text, color="#9ca3af"):
    status_label.config(text=text, fg=color)

def run_background(fn):
    threading.Thread(target=fn, daemon=True).start()

def check_tools():
    missing = [p for p in (ADB, SCRCPY) if not os.path.isfile(p)]
    if missing:
        messagebox.showerror(
            "Files Missing",
            "adb.exe aur scrcpy.exe ko ali_mirror.py ke same folder mein rakho."
        )
        return False
    return True

def enable_wireless():
    if not check_tools():
        return
    set_status("USB device par wireless mode enable ho raha hai...", "#fbbf24")
    def task():
        result = run_cmd([ADB, "tcpip", "5555"])
        if isinstance(result, Exception) or result is None:
            root.after(0, lambda: set_status("ADB command failed", "#ef4444"))
            root.after(0, lambda: messagebox.showerror("Error", str(result)))
        elif result.returncode == 0:
            root.after(0, lambda: set_status("Wireless mode ready — ab phone ka IP enter karo", "#22c55e"))
            root.after(0, lambda: messagebox.showinfo(
                "Wireless Ready",
                "Wireless debugging mode enabled!\n\n"
                "Ab phone ka Wi-Fi IP address enter karke Connect dabao.\n"
                "Phone aur PC same Wi-Fi network par hone chahiye."
            ))
        else:
            detail = (result.stderr or result.stdout or "Phone USB se connect karo aur USB debugging allow karo.").strip()
            root.after(0, lambda: set_status("USB setup failed", "#ef4444"))
            root.after(0, lambda: messagebox.showerror("Enable Wireless Failed", detail))
    run_background(task)

def selected_settings():
    mode = quality.get()
    if mode == "Smooth":
        return ["--max-size=1024", "--max-fps=30", "--video-bit-rate=4M"]
    if mode == "Balanced":
        return ["--max-size=1600", "--max-fps=60", "--video-bit-rate=8M"]
    return ["--max-size=1920", "--max-fps=60", "--video-bit-rate=16M"]

def launch_mirror(serial):
    if not check_tools():
        return
    # scrcpy enables mouse, touch, keyboard and text input by default.
    args = [
        SCRCPY, "--serial", serial,
        "--window-title=ALI WIRELESS MIRROR",
        "--stay-awake"
    ]
    # In mirror-only mode, keep video streaming but block all input events
    # (mouse clicks, wheel/scroll, keyboard) from reaching the phone.
    if not allow_phone_control.get():
        args.append("--no-control")
    args += selected_settings()
    try:
        subprocess.Popen(args, cwd=BASE)
        if allow_phone_control.get():
            set_status("Mirror started — phone control ON (mouse/keyboard/scroll active)", "#22c55e")
        else:
            set_status("Mirror-only started — phone input/scroll LOCKED", "#22c55e")
    except Exception as exc:
        set_status("Could not start scrcpy", "#ef4444")
        messagebox.showerror("Launch Error", str(exc))

def connect_mobile():
    ip = ip_entry.get().strip()
    if not ip:
        messagebox.showwarning("IP Required", "Mobile ka IP address enter karo.")
        return
    # Accept either an IP address or IP:port.
    if not re.fullmatch(r"[A-Za-z0-9.-]+(?::\d{1,5})?", ip):
        messagebox.showwarning("Invalid Address", "IP address sahi enter karo, example: 192.168.1.100")
        return
    serial = ip if ":" in ip else ip + ":5555"
    if not check_tools():
        return
    set_status("Phone se connect ho raha hai...", "#fbbf24")
    def task():
        result = run_cmd([ADB, "connect", serial])
        if isinstance(result, Exception) or result is None:
            root.after(0, lambda: set_status("Connection command failed", "#ef4444"))
            root.after(0, lambda: messagebox.showerror("Connection Error", str(result)))
            return
        output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        success = result.returncode == 0 and (
            "connected to" in output.lower() or "already connected" in output.lower()
        )
        if success:
            root.after(0, lambda: launch_mirror(serial))
        else:
            root.after(0, lambda: set_status("Connection failed — check IP / Wi-Fi", "#ef4444"))
            root.after(0, lambda: messagebox.showerror(
                "Connection Failed",
                output or "Phone aur PC same Wi-Fi par check karo. USB debugging / Wireless debugging bhi check karo."
            ))
    run_background(task)

def connect_usb():
    if not check_tools():
        return
    set_status("USB phone detect ho raha hai...", "#fbbf24")
    def task():
        result = run_cmd([ADB, "devices"])
        if isinstance(result, Exception) or result is None:
            root.after(0, lambda: messagebox.showerror("ADB Error", str(result)))
            return
        devices = []
        for line in (result.stdout or "").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and not parts[0].startswith("emulator-"):
                devices.append(parts[0])
        if not devices:
            root.after(0, lambda: set_status("USB phone not found", "#ef4444"))
            root.after(0, lambda: messagebox.showwarning(
                "No USB Phone", "Phone USB se connect karo, USB debugging ON karo aur Allow dabao."
            ))
            return
        if len(devices) > 1:
            root.after(0, lambda: messagebox.showwarning(
                "Multiple Devices", "Multiple phones connected hain. Sirf ek phone connect rakho."
            ))
            return
        root.after(0, lambda: launch_mirror(devices[0]))
    run_background(task)

def disconnect_mobile():
    ip = ip_entry.get().strip()
    serial = ip if ":" in ip else (ip + ":5555" if ip else "")
    if not serial:
        messagebox.showinfo("Disconnect", "Wireless disconnect ke liye IP address enter karo.")
        return
    result = run_cmd([ADB, "disconnect", serial])
    if isinstance(result, Exception) or result is None:
        messagebox.showerror("Disconnect Error", str(result))
    else:
        set_status("Wireless device disconnected", "#9ca3af")

def refresh_status():
    if not check_tools():
        return
    result = run_cmd([ADB, "devices"])
    if isinstance(result, Exception) or result is None:
        set_status("ADB status unavailable", "#ef4444")
        return
    connected = [
        line.split()[0] for line in (result.stdout or "").splitlines()[1:]
        if len(line.split()) >= 2 and line.split()[1] == "device"
    ]
    if connected:
        set_status("Connected device(s): " + ", ".join(connected), "#22c55e")
    else:
        set_status("No phone connected", "#fbbf24")

root = tk.Tk()
root.title(APP_TITLE)
root.geometry("480x510")
root.configure(bg="#101827")
root.resizable(False, False)

tk.Label(
    root, text="ALI WIRELESS MIRROR",
    font=("Segoe UI", 18, "bold"),
    fg="white", bg="#101827"
).pack(pady=(17, 12))

tk.Label(root, text="Mobile IP Address", fg="white", bg="#101827",
         font=("Segoe UI", 10)).pack()

ip_entry = tk.Entry(root, font=("Segoe UI", 12), justify="center", width=25,
                    bg="#f8fafc", fg="#111827", relief="flat")
ip_entry.pack(pady=7, ipady=5)
ip_entry.insert(0, "192.168.1.100")

tk.Button(
    root, text="1. Enable Wireless (USB)",
    command=enable_wireless, width=30, pady=6,
    bg="#334155", fg="white", activebackground="#475569",
    relief="flat", cursor="hand2"
).pack(pady=5)

tk.Label(root, text="Quality Mode", fg="white", bg="#101827").pack(pady=(5, 2))
quality = tk.StringVar(value="Smooth")
quality_menu = tk.OptionMenu(root, quality, "Smooth", "Balanced", "HD")
quality_menu.config(width=13, bg="#e2e8f0", fg="#111827", relief="flat")
quality_menu.pack(pady=3)

allow_phone_control = tk.BooleanVar(value=False)
tk.Checkbutton(
    root, text="Allow mouse + keyboard control on phone (also enables scrolling)",
    variable=allow_phone_control, fg="white", bg="#101827",
    activebackground="#101827", activeforeground="white",
    selectcolor="#334155", font=("Segoe UI", 8)
).pack(pady=(5, 0))

tk.Button(
    root, text="2. Connect Mobile Wirelessly",
    command=connect_mobile, width=30, pady=8,
    bg="#2563eb", fg="white", activebackground="#1d4ed8",
    relief="flat", cursor="hand2"
).pack(pady=(9, 5))

tk.Button(
    root, text="Mirror via USB (Mouse + Keyboard)",
    command=connect_usb, width=30, pady=7,
    bg="#0f766e", fg="white", activebackground="#115e59",
    relief="flat", cursor="hand2"
).pack(pady=5)

row = tk.Frame(root, bg="#101827")
row.pack(pady=5)
tk.Button(row, text="Refresh Status", command=refresh_status,
          width=14, pady=5, bg="#334155", fg="white",
          relief="flat", cursor="hand2").pack(side="left", padx=5)
tk.Button(row, text="Disconnect Wi-Fi", command=disconnect_mobile,
          width=14, pady=5, bg="#7f1d1d", fg="white",
          relief="flat", cursor="hand2").pack(side="left", padx=5)

status_label = tk.Label(
    root, text="Ready — connect your Android phone",
    fg="#9ca3af", bg="#101827", font=("Segoe UI", 9),
    wraplength=440
)
status_label.pack(pady=(7, 3))

tk.Label(
    root, text="Mouse: click / drag     Keyboard: type directly",
    fg="#cbd5e1", bg="#101827", font=("Segoe UI", 9)
).pack(pady=3)
tk.Label(
    root, text="Free • Wi-Fi • USB • Low Lag",
    fg="#64748b", bg="#101827", font=("Segoe UI", 9)
).pack(pady=(2, 10))

root.mainloop()
