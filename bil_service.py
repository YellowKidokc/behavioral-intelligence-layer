"""
bil_service.py
BIL System Tray Service — the always-on capture + learning daemon.

Features:
  - System tray icon with settings menu
  - Passive screenshots at configurable interval (default: 5 min)
  - Configurable resolution (full, half, quarter)
  - Hotkey Ctrl+Shift+S for manual capture + rating popup
  - Folder watcher: drop files into D:\BIL\inbox\ to "teach" the system
  - Sends everything to NAS BRAIN at \\192.168.1.177
  - Falls back to local D:\BIL\data\ if NAS unreachable

Run:   python pil_service.py
Start: Add shortcut to shell:startup
"""

import json
import os
import sys
import time
import base64
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from pathlib import Path

import keyboard
import mss
import mss.tools
import requests
from PIL import Image, ImageTk

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — edit these or they load from pil_config.json
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "interval_minutes": 5,
    "resolution": "full",            # full | half | quarter
    "nas_url": "http://192.168.1.177:8420",
    "ollama_url": "http://localhost:11434/api/generate",
    "local_capture_dir": r"D:\BIL\data\captures",
    "local_understood_dir": r"D:\BIL\data\understood",
    "local_ratings_file": r"D:\BIL\data\ratings\ratings.jsonl",
    "inbox_dir": r"D:\BIL\inbox",
    "nas_brain_captures": r"\\192.168.1.177\BRAIN\captures",
    "nas_brain_inbox": r"\\192.168.1.177\BRAIN\knowledge\inbox",
    "hotkey": "ctrl+shift+s",
    "auto_start_watcher": True,
    "auto_start_inbox": True,
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bil_config.json")

DATASETS = [
    "general", "github", "ai_quality", "visual",
    "research", "trading", "theophysics", "web",
]

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
        cfg = {**DEFAULT_CONFIG, **saved}
    else:
        cfg = dict(DEFAULT_CONFIG)
    # Ensure dirs exist
    for d in [cfg["local_capture_dir"], cfg["local_understood_dir"],
              os.path.dirname(cfg["local_ratings_file"]), cfg["inbox_dir"]]:
        os.makedirs(d, exist_ok=True)
    return cfg

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

CFG = load_config()

# ══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT
# ══════════════════════════════════════════════════════════════════════════════
def take_screenshot(cfg=None):
    cfg = cfg or CFG
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(cfg["local_capture_dir"], f"cap_{ts}.png")
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = sct.grab(monitor)
        mss.tools.to_png(img.rgb, img.size, output=path)

    # Resize if needed
    res = cfg.get("resolution", "full")
    if res != "full":
        im = Image.open(path)
        factor = {"half": 0.5, "quarter": 0.25}.get(res, 1.0)
        new_size = (int(im.width * factor), int(im.height * factor))
        im = im.resize(new_size, Image.LANCZOS)
        im.save(path)

    # Copy to NAS if reachable
    try_copy_to_nas(path, cfg["nas_brain_captures"])
    return path

def try_copy_to_nas(local_path, nas_dir):
    """Copy file to NAS share. Silent fail if unreachable."""
    try:
        nas_path = Path(nas_dir)
        if nas_path.exists() or nas_path.parent.exists():
            os.makedirs(nas_dir, exist_ok=True)
            import shutil
            shutil.copy2(local_path, os.path.join(nas_dir, os.path.basename(local_path)))
    except Exception:
        pass  # NAS offline — local copy is fine

# ══════════════════════════════════════════════════════════════════════════════
# MOONDREAM DESCRIPTION
# ══════════════════════════════════════════════════════════════════════════════
def describe_image(image_path, cfg=None):
    cfg = cfg or CFG
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        r = requests.post(cfg["ollama_url"], json={
            "model": "moondream",
            "prompt": "One sentence: what app is open and what is the user doing?",
            "images": [img_b64],
            "stream": False,
        }, timeout=30)
        if r.ok:
            desc = r.json().get("response", "").strip()
            ts = os.path.basename(image_path).replace(".png", "")
            desc_path = os.path.join(cfg["local_understood_dir"], f"{ts}.txt")
            with open(desc_path, "w") as f:
                f.write(desc)
            return desc
    except Exception as e:
        print(f"  Moondream: {e}")
    return "Screenshot captured"

# ══════════════════════════════════════════════════════════════════════════════
# RATING / BIL
# ══════════════════════════════════════════════════════════════════════════════
def send_rating(rating, dataset, note, description, image_path, cfg=None):
    cfg = cfg or CFG
    event = {
        "ts": datetime.now().isoformat(),
        "type": "screenshot",
        "signal": rating,
        "dataset": dataset,
        "note": note,
        "description": description,
        "file_path": image_path,
    }
    with open(cfg["local_ratings_file"], "a") as f:
        f.write(json.dumps(event) + "\n")

    # Try NAS API
    try:
        requests.post(f"{cfg['nas_url']}/capture", json=event, timeout=3)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# INBOX WATCHER — drop files here to teach the system
# ══════════════════════════════════════════════════════════════════════════════
def inbox_watcher_loop(cfg=None):
    cfg = cfg or CFG
    inbox = cfg["inbox_dir"]
    processed_dir = os.path.join(inbox, "_processed")
    os.makedirs(processed_dir, exist_ok=True)

    print(f"  Inbox watcher: {inbox}")
    seen = set()
    while True:
        try:
            for fname in os.listdir(inbox):
                fpath = os.path.join(inbox, fname)
                if not os.path.isfile(fpath) or fname.startswith("_") or fpath in seen:
                    continue
                seen.add(fpath)
                print(f"  Inbox: processing {fname}")

                # Copy to NAS knowledge inbox
                try_copy_to_nas(fpath, cfg["nas_brain_inbox"])

                # If image, describe it
                ext = fname.lower().split(".")[-1]
                if ext in ("png", "jpg", "jpeg", "gif", "webp"):
                    desc = describe_image(fpath, cfg)
                    event = {
                        "ts": datetime.now().isoformat(),
                        "type": "inbox_image",
                        "file": fname,
                        "description": desc,
                    }
                else:
                    event = {
                        "ts": datetime.now().isoformat(),
                        "type": "inbox_file",
                        "file": fname,
                        "ext": ext,
                    }

                # Log
                log_path = os.path.join(cfg["local_capture_dir"], "..", "logs", "inbox.jsonl")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a") as f:
                    f.write(json.dumps(event) + "\n")

                # Move to processed
                import shutil
                shutil.move(fpath, os.path.join(processed_dir, fname))

        except Exception as e:
            print(f"  Inbox error: {e}")
        time.sleep(10)

# ══════════════════════════════════════════════════════════════════════════════
# PASSIVE WATCHER
# ══════════════════════════════════════════════════════════════════════════════
def passive_watcher_loop(cfg=None):
    cfg = cfg or CFG
    interval = cfg["interval_minutes"] * 60
    print(f"  Passive watcher: every {cfg['interval_minutes']} min")
    while True:
        try:
            path = take_screenshot(cfg)
            desc = describe_image(path, cfg)
            event = {
                "ts": datetime.now().isoformat(),
                "type": "passive_capture",
                "file": os.path.basename(path),
                "description": desc,
            }
            log_path = os.path.join(os.path.dirname(cfg["local_ratings_file"]), "..", "digests", "watcher.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"  Watcher error: {e}")
        time.sleep(interval)

# ══════════════════════════════════════════════════════════════════════════════
# CAPTURE POPUP (manual hotkey)
# ══════════════════════════════════════════════════════════════════════════════
class CapturePopup:
    def __init__(self, image_path, description):
        self.image_path = image_path
        self.description = description
        self.rating = None

        self.root = tk.Tk()
        self.root.title("BIL Capture")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111111")
        self.root.resizable(False, False)

        w, h = 420, 220
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-60}")
        self._build()
        self.root.bind("<Up>", lambda e: self._rate(1))
        self.root.bind("<Down>", lambda e: self._rate(-1))
        self.root.bind("<Return>", lambda e: self._send())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def _build(self):
        BG, ACC, FG, DIM = "#111111", "#00ff88", "#cccccc", "#444444"
        F = ("Consolas", 9)

        tk.Frame(self.root, bg=ACC, height=2).pack(fill="x")
        body = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        body.pack(fill="both", expand=True)

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(0, 8))
        try:
            img = Image.open(self.image_path).resize((100, 66))
            self.thumb = ImageTk.PhotoImage(img)
            tk.Label(top, image=self.thumb, bg=BG).pack(side="left", padx=(0, 10))
        except Exception:
            tk.Label(top, text="[IMG]", bg=BG, fg=DIM, font=F).pack(side="left")

        df = tk.Frame(top, bg=BG)
        df.pack(side="left", fill="both", expand=True)
        tk.Label(df, text="PREFERENCE CAPTURE", bg=BG, fg=ACC, font=("Consolas", 7)).pack(fill="x")
        tk.Label(df, text=self.description[:80], bg=BG, fg=DIM, font=("Consolas", 8),
                 wraplength=270, anchor="w", justify="left").pack(fill="x")

        dr = tk.Frame(body, bg=BG)
        dr.pack(fill="x", pady=2)
        tk.Label(dr, text="DATASET", bg=BG, fg=DIM, font=("Consolas", 7), width=8).pack(side="left")
        self.ds = tk.StringVar(value="general")
        ttk.Combobox(dr, textvariable=self.ds, values=DATASETS, font=F, width=20, state="readonly").pack(side="left")

        nr = tk.Frame(body, bg=BG)
        nr.pack(fill="x", pady=2)
        tk.Label(nr, text="NOTE", bg=BG, fg=DIM, font=("Consolas", 7), width=8).pack(side="left")
        self.note = tk.StringVar()
        tk.Entry(nr, textvariable=self.note, bg="#1a1a1a", fg=FG, insertbackground=FG, relief="flat", font=F, width=30).pack(side="left")

        br = tk.Frame(body, bg=BG)
        br.pack(fill="x", pady=(8, 0))
        self.bu = tk.Button(br, text="👍 PREFER", command=lambda: self._rate(1),
            bg="#1a1a1a", fg="#444", relief="flat", font=F, padx=10, pady=6)
        self.bu.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.bd = tk.Button(br, text="👎 REJECT", command=lambda: self._rate(-1),
            bg="#1a1a1a", fg="#444", relief="flat", font=F, padx=10, pady=6)
        self.bd.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.bs = tk.Button(br, text="SEND →", command=self._send,
            bg="#1a1a1a", fg=ACC, relief="flat", font=F, state="disabled", padx=10, pady=6)
        self.bs.pack(side="left")

    def _rate(self, v):
        self.rating = v
        if v == 1:
            self.bu.config(fg="#00ff88", bg="#00ff8815")
            self.bd.config(fg="#444", bg="#1a1a1a")
        else:
            self.bd.config(fg="#ff4444", bg="#ff444415")
            self.bu.config(fg="#444", bg="#1a1a1a")
        self.bs.config(state="normal")

    def _send(self):
        if self.rating is None:
            return
        send_rating(self.rating, self.ds.get(), self.note.get(), self.description, self.image_path)
        self.root.destroy()

    def show(self):
        self.root.mainloop()

# ══════════════════════════════════════════════════════════════════════════════
# HOTKEY HANDLER
# ══════════════════════════════════════════════════════════════════════════════
def on_hotkey():
    def _run():
        path = take_screenshot()
        desc = describe_image(path)
        popup = CapturePopup(path, desc)
        popup.show()
    threading.Thread(target=_run, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM TRAY
# ══════════════════════════════════════════════════════════════════════════════
def run_tray():
    import pystray
    from pystray import MenuItem as Item

    watcher_running = [CFG.get("auto_start_watcher", True)]
    inbox_running = [CFG.get("auto_start_inbox", True)]
    watcher_thread = [None]
    inbox_thread = [None]

    def toggle_watcher(icon, item):
        watcher_running[0] = not watcher_running[0]
        if watcher_running[0] and (watcher_thread[0] is None or not watcher_thread[0].is_alive()):
            watcher_thread[0] = threading.Thread(target=passive_watcher_loop, daemon=True)
            watcher_thread[0].start()

    def toggle_inbox(icon, item):
        inbox_running[0] = not inbox_running[0]
        if inbox_running[0] and (inbox_thread[0] is None or not inbox_thread[0].is_alive()):
            inbox_thread[0] = threading.Thread(target=inbox_watcher_loop, daemon=True)
            inbox_thread[0].start()

    def open_config(icon, item):
        os.startfile(CONFIG_PATH)

    def open_captures(icon, item):
        os.startfile(CFG["local_capture_dir"])

    def open_inbox(icon, item):
        os.startfile(CFG["inbox_dir"])

    def quit_app(icon, item):
        icon.stop()
        os._exit(0)

    # Create a simple icon (green square)
    icon_img = Image.new("RGB", (64, 64), "#00ff88")

    menu = pystray.Menu(
        Item("BIL Service", lambda *a: None, enabled=False),
        Item("───────────", lambda *a: None, enabled=False),
        Item(lambda _: f"Watcher: {'ON' if watcher_running[0] else 'OFF'}", toggle_watcher),
        Item(lambda _: f"Inbox:   {'ON' if inbox_running[0] else 'OFF'}", toggle_inbox),
        Item("───────────", lambda *a: None, enabled=False),
        Item(f"Interval: {CFG['interval_minutes']} min", lambda *a: None, enabled=False),
        Item(f"Resolution: {CFG['resolution']}", lambda *a: None, enabled=False),
        Item("───────────", lambda *a: None, enabled=False),
        Item("Open Config", open_config),
        Item("Open Captures", open_captures),
        Item("Open Inbox", open_inbox),
        Item("───────────", lambda *a: None, enabled=False),
        Item("Quit", quit_app),
    )

    icon = pystray.Icon("PIL", icon_img, "BIL Service", menu)

    # Start threads
    if watcher_running[0]:
        watcher_thread[0] = threading.Thread(target=passive_watcher_loop, daemon=True)
        watcher_thread[0].start()

    if inbox_running[0]:
        inbox_thread[0] = threading.Thread(target=inbox_watcher_loop, daemon=True)
        inbox_thread[0].start()

    # Hotkey
    keyboard.add_hotkey(CFG["hotkey"], on_hotkey)

    print("BIL Service running in system tray.")
    print(f"  Hotkey: {CFG['hotkey']}")
    print(f"  Watcher: {'ON' if watcher_running[0] else 'OFF'} ({CFG['interval_minutes']} min)")
    print(f"  Inbox: {CFG['inbox_dir']}")
    print(f"  NAS: {CFG['nas_url']}")

    icon.run()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    save_config(CFG)  # write defaults if first run
    run_tray()
