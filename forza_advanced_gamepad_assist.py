"""
Forza UDP Advanced Gamepad Assist (Ultimate Edition v0.2)

Features:
- Zero-lag XInput polling
- Advanced Slip & Counter-steer math
- Live UI Telemetry
- Dynamic Rumble (Force Feedback) on slip with UI Toggle
- CPU optimized 120Hz loop
- Interactive UI Hints
- Multi-language support (EN, RU, UK)
- Low-pass Telemetry Filter (Adjustable via UI)
- Device Selection (Gamepad ID & vJoy ID)
- Profile System (Create, Save, Import, Export JSON profiles anywhere)
"""

from __future__ import annotations

import math
import os
import socket
import struct
import json
import tkinter as tk
from tkinter import simpledialog, filedialog
import threading
import time
from dataclasses import dataclass
from typing import Optional
import ctypes
from ctypes import wintypes

import pyvjoy

APP_CONFIG_FILE = "forza_app_config.json"
PROFILES_DIR = "profiles"

# --- TRANSLATIONS DICTIONARY ---
TRANSLATIONS = {
    "en": {
        "title": "Forza Assist v0.2",
        "lang_select": "Language:",
        "ctrl_select": "Gamepad ID:",
        "vjoy_select": "vJoy Device:",
        "profile_select": "Profile:",
        "btn_save": "Save",
        "btn_new": "New",
        "btn_import": "Import",
        "btn_export": "Export",
        "prompt_new": "Enter new profile name:",
        "settings": "Physics Settings",
        "telemetry": "Live Telemetry",
        "gyro": "Gyro Influence",
        "gyro_hint": "Gyro influence. Emulates Caster effect: wheels align with movement vector. Improves stability on straights and in corners.",
        "damping": "Steering Damping (Weight)",
        "damping_hint": "Steering inertia. Higher values smooth out wheel movements. Wheel feels lighter during slip.",
        "counter": "Counter-Steer Gain",
        "counter_hint": "Counter-steer multiplier. How aggressively the assist turns the wheel into the skid to prevent spinning out.",
        "deadband": "Slip Deadband (Grip Limit)",
        "deadband_hint": "Grip limit. Below this tire slip angle, counter-steer and rumble are disabled, allowing for micro-slips.",
        "smoothing": "Telemetry Smoothing (Lag)",
        "smoothing_hint": "Filters out telemetry noise (micro-spikes). 0.0 = raw data. Higher values = smoother wheel, but introduces slight input lag.",
        "rumble": "Enable Rumble (FFB)",
        "rumble_hint": "Physical feedback. The gamepad motors will vibrate when the front wheels lose grip.",
        "raw_input": "Raw Input",
        "filt_out": "Filtered Output",
        "tire_slip": "Tire Slip",
        "hint_def": "Hover over a parameter to see its description."
    },
    "ru": {
        "title": "Forza Assist v0.6",
        "lang_select": "Язык:",
        "ctrl_select": "Геймпад №:",
        "vjoy_select": "vJoy №:",
        "profile_select": "Профиль:",
        "btn_save": "Сохр.",
        "btn_new": "Новый",
        "btn_import": "Импорт",
        "btn_export": "Экспорт",
        "prompt_new": "Введите имя нового профиля:",
        "settings": "Настройки физики",
        "telemetry": "Телеметрия",
        "gyro": "Влияние гироскопа (Gyro)",
        "gyro_hint": "Влияние гироскопа. Эмулирует эффект Кастера: колеса сами выравниваются по вектору движения машины. Улучшает стабильность.",
        "damping": "Тяжесть руля (Damping)",
        "damping_hint": "Инерция руля. Чем выше значение, тем плавнее движения колес. При заносе руль автоматически становится легче.",
        "counter": "Сила контр-руления",
        "counter_hint": "Множитель контр-руления. Насколько агрессивно ассист будет выворачивать руль в сторону заноса, чтобы спасти машину.",
        "deadband": "Предел сцепления (Мертвая зона)",
        "deadband_hint": "До этого угла скольжения шин контр-руление и вибрация не включаются, позволяя делать легкие микро-скольжения.",
        "smoothing": "Сглаживание телеметрии",
        "smoothing_hint": "Убирает шум (микро-спайки) из данных игры. 0.0 = сырые данные. Чем выше, тем плавнее руль, но появляется микро-задержка.",
        "rumble": "Включить вибрацию (FFB)",
        "rumble_hint": "Физическая отдача. Геймпад будет вибрировать в тот момент, когда передние колеса теряют зацеп.",
        "raw_input": "Сырой стик",
        "filt_out": "Ассист",
        "tire_slip": "Скольжение",
        "hint_def": "Наведи курсор на параметр, чтобы увидеть подсказку."
    },
    "uk": {
        "title": "Forza Assist v0.6",
        "lang_select": "Мова:",
        "ctrl_select": "Геймпад №:",
        "vjoy_select": "vJoy №:",
        "profile_select": "Профіль:",
        "btn_save": "Збер.",
        "btn_new": "Новий",
        "btn_import": "Імпорт",
        "btn_export": "Експорт",
        "prompt_new": "Введіть ім'я нового профілю:",
        "settings": "Налаштування фізики",
        "telemetry": "Телеметрія",
        "gyro": "Вплив гіроскопа (Gyro)",
        "gyro_hint": "Вплив гіроскопа. Емулює ефект Кастера: колеса самі вирівнюються за вектором руху авто. Покращує стабільність.",
        "damping": "Важкість керма (Damping)",
        "damping_hint": "Інерція керма. Вищі значення роблять рухи коліс плавнішими. Під час заносу кермо автоматично стає легшим.",
        "counter": "Сила контр-кермування",
        "counter_hint": "Множник контр-кермування. Наскільки агресивно асист вивертатиме кермо в бік заносу, щоб врятувати авто.",
        "deadband": "Межа зчеплення (Мертва зона)",
        "deadband_hint": "До цього кута ковзання шин контр-кермування та вібрація не вмикаються, дозволяючи робити легкі мікро-ковзання.",
        "smoothing": "Згладжування телеметрії",
        "smoothing_hint": "Прибирає шум (мікро-спайки) з даних гри. 0.0 = сирі дані. Чим вище, тим плавніше кермо, але з'являється мікро-затримка.",
        "rumble": "Увімкнути вібрацію (FFB)",
        "rumble_hint": "Фізична віддача. Геймпад вібруватиме в той момент, коли передні колеса втрачають зчеплення.",
        "raw_input": "Сирий стік",
        "filt_out": "Асист",
        "tire_slip": "Ковзання",
        "hint_def": "Наведи курсор на параметр, щоб побачити підказку."
    }
}

LANG_MAP = {"English": "en", "Русский": "ru", "Українська": "uk"}
REVERSE_LANG_MAP = {v: k for k, v in LANG_MAP.items()}


# --- XINPUT WRAPPER (ZERO LAG + RUMBLE) ---
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", wintypes.SHORT),
        ("sThumbLY", wintypes.SHORT),
        ("sThumbRX", wintypes.SHORT),
        ("sThumbRY", wintypes.SHORT),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ("wLeftMotorSpeed", wintypes.WORD),
        ("wRightMotorSpeed", wintypes.WORD),
    ]

try:
    xinput = ctypes.windll.xinput1_4
except OSError:
    try:
        xinput = ctypes.windll.xinput1_3
    except OSError:
        xinput = ctypes.windll.xinput9_1_0

XInputGetState = xinput.XInputGetState
XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
XInputGetState.restype = wintypes.DWORD

XInputSetState = xinput.XInputSetState
XInputSetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_VIBRATION)]
XInputSetState.restype = wintypes.DWORD

XINPUT_BUTTONS = {
    "DPAD_UP": 0x0001, "DPAD_DOWN": 0x0002, "DPAD_LEFT": 0x0004, "DPAD_RIGHT": 0x0008,
    "START": 0x0010, "BACK": 0x0020, "LEFT_THUMB": 0x0040, "RIGHT_THUMB": 0x0080,
    "LEFT_SHOULDER": 0x0100, "RIGHT_SHOULDER": 0x0200,
    "A": 0x1000, "B": 0x2000, "X": 0x4000, "Y": 0x8000
}

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def set_gamepad_rumble(controller_id: int, left_motor: float, right_motor: float):
    vib = XINPUT_VIBRATION()
    vib.wLeftMotorSpeed = int(clamp(left_motor, 0.0, 1.0) * 65535)
    vib.wRightMotorSpeed = int(clamp(right_motor, 0.0, 1.0) * 65535)
    XInputSetState(controller_id, ctypes.byref(vib))


# --- CONFIGURATION & PROFILE MANAGEMENT ---
class Config:
    def __init__(self):
        self._lock = threading.Lock()
        
        # App Settings (Global)
        self.language = "en"
        self.controller_index = 0
        self.vjoy_device = 1
        self.current_profile = "Default"
        
        # Physics Settings (Profile-specific)
        self.gyro_strength = 0.9
        self.base_damping = 26.0
        self.counter_steer_gain = 0.82
        self.slip_deadband = 0.04
        self.telemetry_smoothing = 0.80  
        self.enable_rumble = True
        
        self.ensure_directories()
        self.load_app_config()
        self.load_profile(self.current_profile)

    def ensure_directories(self):
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR)

    def get_profile_list(self) -> list[str]:
        self.ensure_directories()
        profiles = [f[:-5] for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
        if not profiles:
            self.save_profile("Default")
            return ["Default"]
        return sorted(profiles)

    def get_values(self):
        with self._lock:
            return (
                self.gyro_strength, 
                self.base_damping, 
                self.counter_steer_gain, 
                self.slip_deadband, 
                self.telemetry_smoothing,
                self.enable_rumble
            )

    def update(self, key, value):
        with self._lock:
            if key == "enable_rumble":
                self.enable_rumble = bool(value)
            elif key in ["language", "controller_index", "vjoy_device", "current_profile"]:
                setattr(self, key, value)
                if key != "current_profile":
                    threading.Thread(target=self.save_app_config).start()
            else:
                setattr(self, key, float(value))

    def load_app_config(self):
        try:
            if os.path.exists(APP_CONFIG_FILE):
                with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.language = data.get("language", "en")
                    self.controller_index = data.get("controller_index", 0)
                    self.vjoy_device = data.get("vjoy_device", 1)
                    self.current_profile = data.get("current_profile", "Default")
        except Exception:
            pass

    def save_app_config(self):
        data = {
            "language": self.language,
            "controller_index": self.controller_index,
            "vjoy_device": self.vjoy_device,
            "current_profile": self.current_profile
        }
        try:
            with open(APP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def load_profile(self, name: str):
        filepath = os.path.join(PROFILES_DIR, f"{name}.json")
        loaded_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
            except Exception:
                pass

        with self._lock:
            self.current_profile = name
            if "gyro_strength" in loaded_data: self.gyro_strength = float(loaded_data["gyro_strength"])
            if "base_damping" in loaded_data: self.base_damping = float(loaded_data["base_damping"])
            if "counter_steer_gain" in loaded_data: self.counter_steer_gain = float(loaded_data["counter_steer_gain"])
            if "slip_deadband" in loaded_data: self.slip_deadband = float(loaded_data["slip_deadband"])
            if "telemetry_smoothing" in loaded_data: self.telemetry_smoothing = float(loaded_data["telemetry_smoothing"])
            if "enable_rumble" in loaded_data: self.enable_rumble = bool(loaded_data["enable_rumble"])
        
        self.save_app_config()

    def save_profile(self, name: str):
        filepath = os.path.join(PROFILES_DIR, f"{name}.json")
        with self._lock:
            data = {
                "gyro_strength": self.gyro_strength,
                "base_damping": self.base_damping,
                "counter_steer_gain": self.counter_steer_gain,
                "slip_deadband": self.slip_deadband,
                "telemetry_smoothing": self.telemetry_smoothing,
                "enable_rumble": self.enable_rumble
            }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass


class DebugState:
    def __init__(self):
        self.lock = threading.Lock()
        self.raw_stick = 0.0
        self.filtered_stick = 0.0
        self.slip = 0.0

    def update(self, raw, filtered, slip):
        with self.lock:
            self.raw_stick = raw
            self.filtered_stick = filtered
            self.slip = slip

    def get(self):
        with self.lock:
            return self.raw_stick, self.filtered_stick, self.slip

shared_debug = DebugState()


# --- UI (MAIN THREAD) ---
class AssistApp:
    def __init__(self, config: Config):
        self.config = config
        self.root = tk.Tk()
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 1. Top Bar (Language, Devices, Profiles)
        frame_top = tk.Frame(self.root)
        frame_top.pack(padx=10, pady=(10, 0), fill="x")
        
        # Row 1: Language
        frame_lang = tk.Frame(frame_top)
        frame_lang.pack(fill="x", pady=2)
        self.lbl_lang = tk.Label(frame_lang, text="")
        self.lbl_lang.pack(side="left")
        
        current_lang_str = REVERSE_LANG_MAP.get(self.config.language, "English")
        self.lang_var = tk.StringVar(value=current_lang_str)
        tk.OptionMenu(frame_lang, self.lang_var, *LANG_MAP.keys(), command=self.on_lang_change).pack(side="right")

        # Row 2: Controllers
        frame_dev = tk.Frame(frame_top)
        frame_dev.pack(fill="x", pady=2)
        
        self.lbl_ctrl = tk.Label(frame_dev, text="")
        self.lbl_ctrl.pack(side="left")
        self.ctrl_var = tk.IntVar(value=self.config.controller_index)
        tk.OptionMenu(frame_dev, self.ctrl_var, 0, 1, 2, 3, command=lambda v: self.config.update("controller_index", v)).pack(side="left", padx=(5, 10))
        
        self.lbl_vjoy = tk.Label(frame_dev, text="")
        self.lbl_vjoy.pack(side="left")
        self.vjoy_var = tk.IntVar(value=self.config.vjoy_device)
        tk.OptionMenu(frame_dev, self.vjoy_var, 1, 2, 3, 4, command=lambda v: self.config.update("vjoy_device", v)).pack(side="right")

        # Row 3: Profiles
        frame_prof = tk.Frame(frame_top)
        frame_prof.pack(fill="x", pady=(8, 2))
        
        self.lbl_prof = tk.Label(frame_prof, text="")
        self.lbl_prof.pack(side="left")
        
        self.prof_var = tk.StringVar(value=self.config.current_profile)
        self.prof_menu = tk.OptionMenu(frame_prof, self.prof_var, *self.config.get_profile_list(), command=self.on_profile_change)
        self.prof_menu.pack(side="left", padx=2)

        self.btn_new = tk.Button(frame_prof, text="", command=self.on_new_profile)
        self.btn_new.pack(side="left", padx=2)
        
        self.btn_save = tk.Button(frame_prof, text="", command=self.on_save_profile)
        self.btn_save.pack(side="left", padx=2)

        # Export/Import buttons on the right
        self.btn_export = tk.Button(frame_prof, text="", command=self.on_export_profile)
        self.btn_export.pack(side="right", padx=2)

        self.btn_import = tk.Button(frame_prof, text="", command=self.on_import_profile)
        self.btn_import.pack(side="right", padx=2)

        # 2. Physics Settings Container
        self.frame_controls = tk.LabelFrame(self.root, padx=10, pady=10)
        self.frame_controls.pack(padx=10, pady=5, fill="x")

        self.hint_label = tk.Label(
            self.frame_controls, text="", 
            fg="gray", wraplength=280, justify="left", height=3, font=("Arial", 8, "italic")
        )

        self.lbl_gyro, self.slider_gyro = self.add_slider(
            self.frame_controls, 0.0, 2.0, self.config.gyro_strength, "gyro_strength", "gyro_hint"
        )
        self.lbl_damping, self.slider_damping = self.add_slider(
            self.frame_controls, 5.0, 50.0, self.config.base_damping, "base_damping", "damping_hint", resolution=1.0
        )
        self.lbl_counter, self.slider_counter = self.add_slider(
            self.frame_controls, 0.0, 2.0, self.config.counter_steer_gain, "counter_steer_gain", "counter_hint"
        )
        self.lbl_deadband, self.slider_deadband = self.add_slider(
            self.frame_controls, 0.01, 0.2, self.config.slip_deadband, "slip_deadband", "deadband_hint", resolution=0.01
        )
        self.lbl_smoothing, self.slider_smoothing = self.add_slider(
            self.frame_controls, 0.0, 0.95, self.config.telemetry_smoothing, "telemetry_smoothing", "smoothing_hint", resolution=0.05
        )

        # Rumble Checkbox
        self.rumble_var = tk.BooleanVar(value=self.config.enable_rumble)
        self.rumble_cb = tk.Checkbutton(
            self.frame_controls, text="", 
            variable=self.rumble_var,
            command=lambda: self.config.update("enable_rumble", self.rumble_var.get())
        )
        self.rumble_cb.pack(anchor="w", pady=(5, 0))
        self.bind_hint([self.rumble_cb], "rumble_hint")

        self.hint_label.pack(fill="x", pady=(10, 0))

        # 3. Telemetry Container
        self.frame_debug = tk.LabelFrame(self.root, padx=10, pady=10)
        self.frame_debug.pack(padx=10, pady=5, fill="x")
        
        self.canvas = tk.Canvas(self.frame_debug, width=300, height=80, bg="black")
        self.canvas.pack()
        
        self.apply_translations()
        self.update_debug_ui()

    def get_text(self, key):
        return TRANSLATIONS[self.config.language].get(key, key)

    def on_lang_change(self, choice):
        self.config.update("language", LANG_MAP[choice])
        self.apply_translations()

    def on_profile_change(self, choice):
        self.config.load_profile(choice)
        self.refresh_sliders()

    def on_save_profile(self):
        self.config.save_profile(self.config.current_profile)

    def on_new_profile(self):
        name = simpledialog.askstring("New Profile", self.get_text("prompt_new"), parent=self.root)
        if name:
            safe_name = "".join(x for x in name if x.isalnum() or x in " _-").strip()
            if safe_name:
                self.config.current_profile = safe_name
                self.config.save_profile(safe_name)
                self.update_profile_dropdown()
                self.prof_var.set(safe_name)

    def on_export_profile(self):
        """ Allows the user to save the current settings anywhere on their PC """
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title=self.get_text("btn_export"),
            initialfile=f"{self.config.current_profile}.json"
        )
        if filepath:
            data = {
                "gyro_strength": self.config.gyro_strength,
                "base_damping": self.config.base_damping,
                "counter_steer_gain": self.config.counter_steer_gain,
                "slip_deadband": self.config.slip_deadband,
                "telemetry_smoothing": self.config.telemetry_smoothing,
                "enable_rumble": self.config.enable_rumble
            }
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except Exception:
                pass

    def on_import_profile(self):
        """ Allows the user to load a profile from anywhere and adds it to the internal list """
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title=self.get_text("btn_import")
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                
                # Extract file name without extension to use as the new profile name
                raw_name = os.path.splitext(os.path.basename(filepath))[0]
                safe_name = "".join(x for x in raw_name if x.isalnum() or x in " _-").strip()
                if not safe_name:
                    safe_name = "ImportedProfile"

                # Update the config state
                self.config.current_profile = safe_name
                if "gyro_strength" in loaded_data: self.config.gyro_strength = float(loaded_data["gyro_strength"])
                if "base_damping" in loaded_data: self.config.base_damping = float(loaded_data["base_damping"])
                if "counter_steer_gain" in loaded_data: self.config.counter_steer_gain = float(loaded_data["counter_steer_gain"])
                if "slip_deadband" in loaded_data: self.config.slip_deadband = float(loaded_data["slip_deadband"])
                if "telemetry_smoothing" in loaded_data: self.config.telemetry_smoothing = float(loaded_data["telemetry_smoothing"])
                if "enable_rumble" in loaded_data: self.config.enable_rumble = bool(loaded_data["enable_rumble"])
                
                # Save into the internal 'profiles' folder so it appears in the dropdown
                self.config.save_profile(safe_name)
                
                self.update_profile_dropdown()
                self.prof_var.set(safe_name)
                self.refresh_sliders()

            except Exception:
                pass

    def update_profile_dropdown(self):
        menu = self.prof_menu["menu"]
        menu.delete(0, "end")
        for p in self.config.get_profile_list():
            menu.add_command(label=p, command=tk._setit(self.prof_var, p, self.on_profile_change))

    def refresh_sliders(self):
        self.slider_gyro.set(self.config.gyro_strength)
        self.slider_damping.set(self.config.base_damping)
        self.slider_counter.set(self.config.counter_steer_gain)
        self.slider_deadband.set(self.config.slip_deadband)
        self.slider_smoothing.set(self.config.telemetry_smoothing)
        self.rumble_var.set(self.config.enable_rumble)

    def apply_translations(self):
        self.root.title(self.get_text("title"))
        self.lbl_lang.config(text=self.get_text("lang_select"))
        self.lbl_ctrl.config(text=self.get_text("ctrl_select"))
        self.lbl_vjoy.config(text=self.get_text("vjoy_select"))
        self.lbl_prof.config(text=self.get_text("profile_select"))
        
        self.btn_save.config(text=self.get_text("btn_save"))
        self.btn_new.config(text=self.get_text("btn_new"))
        self.btn_import.config(text=self.get_text("btn_import"))
        self.btn_export.config(text=self.get_text("btn_export"))
        
        self.frame_controls.config(text=self.get_text("settings"))
        self.frame_debug.config(text=self.get_text("telemetry"))
        
        self.lbl_gyro.config(text=self.get_text("gyro"))
        self.lbl_damping.config(text=self.get_text("damping"))
        self.lbl_counter.config(text=self.get_text("counter"))
        self.lbl_deadband.config(text=self.get_text("deadband"))
        self.lbl_smoothing.config(text=self.get_text("smoothing"))
        
        self.rumble_cb.config(text=self.get_text("rumble"))
        self.hint_label.config(text=self.get_text("hint_def"))

    def bind_hint(self, widgets, hint_key):
        def on_enter(e):
            self.hint_label.config(text=self.get_text(hint_key), fg="black", font=("Arial", 8, "normal"))
        def on_leave(e):
            self.hint_label.config(text=self.get_text("hint_def"), fg="gray", font=("Arial", 8, "italic"))
        
        for widget in widgets:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def add_slider(self, parent, min_val, max_val, default, config_key, hint_key, resolution=0.05):
        lbl = tk.Label(parent, text="")
        lbl.pack(anchor="w")
        slider = tk.Scale(
            parent, from_=min_val, to=max_val, resolution=resolution,
            orient=tk.HORIZONTAL, length=280,
            command=lambda v, k=config_key: self.config.update(k, v)
        )
        slider.set(default)
        slider.pack(pady=(0, 5))
        
        self.bind_hint([lbl, slider], hint_key)
        return lbl, slider

    def update_debug_ui(self):
        self.canvas.delete("all")
        raw, filtered, slip = shared_debug.get()
        
        center_x = 150
        
        # Raw Input
        raw_x = center_x + int(raw * 140)
        self.canvas.create_rectangle(center_x, 10, raw_x, 25, fill="red", outline="")
        self.canvas.create_text(150, 17, text=self.get_text("raw_input"), fill="white", font=("Arial", 8))
        
        # Filtered Output
        filt_x = center_x + int(filtered * 140)
        self.canvas.create_rectangle(center_x, 35, filt_x, 50, fill="green", outline="")
        self.canvas.create_text(150, 42, text=self.get_text("filt_out"), fill="white", font=("Arial", 8))

        # Tire Slip
        vis_slip = clamp(slip * 2.0, -1.0, 1.0)
        slip_x = center_x + int(vis_slip * 140)
        self.canvas.create_rectangle(center_x, 60, slip_x, 75, fill="cyan", outline="")
        self.canvas.create_text(150, 67, text=self.get_text("tire_slip"), fill="black", font=("Arial", 8))

        # Center Line
        self.canvas.create_line(center_x, 0, center_x, 80, fill="white", dash=(2, 2))

        self.root.after(33, self.update_debug_ui)

    def on_closing(self):
        self.config.save_profile(self.config.current_profile)
        set_gamepad_rumble(self.config.controller_index, 0.0, 0.0)
        self.root.destroy()
        os._exit(0)

    def run(self):
        self.root.mainloop()


# --- TELEMETRY & PHYSICS (BACKGROUND THREAD) ---
@dataclass(frozen=True)
class Telemetry:
    speed_mps: float
    front_tire_slip_angle: float
    angular_velocity_y: float

class LowPassFilter:
    """ EMA Low-pass filter to smooth out noisy UDP telemetry """
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.value = 0.0
        self.initialized = False

    def update(self, new_val: float) -> float:
        if not self.initialized:
            self.value = new_val
            self.initialized = True
        else:
            self.value = self.alpha * new_val + (1.0 - self.alpha) * self.value
        return self.value

class AdvancedGamepadAssist:
    def __init__(self, runtime: Config):
        self.runtime = runtime
        self.current_steer_angle = 0.0
        
        self.slip_filter = LowPassFilter(alpha=0.2)
        self.gyro_filter = LowPassFilter(alpha=0.2)

    def update(self, raw_stick_x: float, telemetry: Telemetry, dt: float) -> float:
        gyro_str, base_damp, counter_gain, deadband, smoothing, rumble_enabled = self.runtime.get_values()
        
        filter_alpha = max(0.01, 1.0 - smoothing)
        self.slip_filter.alpha = filter_alpha
        self.gyro_filter.alpha = filter_alpha

        smooth_slip = self.slip_filter.update(telemetry.front_tire_slip_angle)
        smooth_gyro = self.gyro_filter.update(telemetry.angular_velocity_y)
        
        gyro_force = -smooth_gyro * gyro_str
        
        counter_steer = 0.0
        current_damping = base_damp
        rumble_power = 0.0

        if abs(smooth_slip) > deadband:
            slip_excess = abs(smooth_slip) - deadband
            slip_dir = -math.copysign(1.0, smooth_slip) 
            
            counter_steer = slip_excess * counter_gain * slip_dir
            current_damping = max(5.0, base_damp * 0.4) 
            
            rumble_power = clamp(slip_excess / 0.2, 0.0, 1.0)

        ctrl_idx = self.runtime.controller_index
        if rumble_enabled:
            set_gamepad_rumble(ctrl_idx, rumble_power * 0.3, rumble_power)
        else:
            set_gamepad_rumble(ctrl_idx, 0.0, 0.0)

        target = raw_stick_x + gyro_force + counter_steer
        target = clamp(target, -1.0, 1.0)
        
        self.current_steer_angle = target + (self.current_steer_angle - target) * math.exp(-current_damping * dt)
        self.current_steer_angle = clamp(self.current_steer_angle, -1.0, 1.0)
        
        if not math.isfinite(self.current_steer_angle):
            self.current_steer_angle = 0.0
            
        shared_debug.update(raw_stick_x, self.current_steer_angle, smooth_slip)
            
        return self.current_steer_angle

class VJoySteering:
    def __init__(self):
        self.device_id = -1
        self.device = None

    def set_device(self, dev_id: int):
        if self.device_id != dev_id:
            self.device_id = dev_id
            try:
                self.device = pyvjoy.VJoyDevice(dev_id)
            except Exception:
                self.device = None

    def set_controls(self, stick_x: float, throttle: float, brake: float, buttons: tuple[bool, ...]):
        if not self.device:
            return
            
        val_x = int(round((clamp(stick_x, -1.0, 1.0) + 1.0) * 0.5 * 32767.0))
        self.device.set_axis(pyvjoy.HID_USAGE_X, clamp(val_x, 0, 32767))
        self.device.set_axis(pyvjoy.HID_USAGE_SL0, int(round(clamp(throttle, 0.0, 1.0) * 32767.0)))
        self.device.set_axis(pyvjoy.HID_USAGE_SL1, int(round(clamp(brake, 0.0, 1.0) * 32767.0)))
        
        for button_id, pressed in enumerate(buttons, start=1):
            self.device.set_button(button_id, int(pressed))

class ForzaUdpTelemetryListener:
    PACKET_SIZE = 324
    ANGULAR_VELOCITY_Y_OFFSET = 48
    FRONT_LEFT_SLIP_OFFSET = 164
    FRONT_RIGHT_SLIP_OFFSET = 168
    SPEED_OFFSET = 256
    FLOAT32 = struct.Struct("<f")

    def __init__(self, host="0.0.0.0", port=20777, stale_after_sec=0.5):
        self.host, self.port, self.stale_after_sec = host, port, stale_after_sec
        self._lock = threading.Lock()
        self._latest = Telemetry(0.0, 0.0, 0.0)
        self._last_time = 0.0
        self._running = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._running.set()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()

    def get_latest(self) -> Telemetry:
        with self._lock:
            if time.monotonic() - self._last_time > self.stale_after_sec:
                return Telemetry(0.0, 0.0, 0.0)
            return self._latest

    def _listen_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.settimeout(0.2)
            while self._running.is_set():
                try:
                    packet, _ = sock.recvfrom(2048)
                    if len(packet) >= self.PACKET_SIZE:
                        fl_slip = self.FLOAT32.unpack_from(packet, self.FRONT_LEFT_SLIP_OFFSET)[0]
                        fr_slip = self.FLOAT32.unpack_from(packet, self.FRONT_RIGHT_SLIP_OFFSET)[0]
                        ang_vel = self.FLOAT32.unpack_from(packet, self.ANGULAR_VELOCITY_Y_OFFSET)[0]
                        spd = self.FLOAT32.unpack_from(packet, self.SPEED_OFFSET)[0]
                        
                        if math.isfinite(fl_slip) and math.isfinite(fr_slip) and math.isfinite(ang_vel):
                            with self._lock:
                                self._latest = Telemetry(max(0.0, spd), (fl_slip + fr_slip) * 0.5, ang_vel)
                                self._last_time = time.monotonic()
                except (socket.timeout, OSError):
                    pass

def read_xinput_controls(controller_id=0):
    state = XINPUT_STATE()
    if XInputGetState(controller_id, ctypes.byref(state)) == 0:
        gp = state.Gamepad
        raw_stick = gp.sThumbLX / 32768.0 if gp.sThumbLX < 0 else gp.sThumbLX / 32767.0
        
        DEADZONE = 0.15
        if abs(raw_stick) < DEADZONE:
            stick_x = 0.0
        else:
            stick_x = math.copysign((abs(raw_stick) - DEADZONE) / (1.0 - DEADZONE), raw_stick)
        
        throttle = gp.bRightTrigger / 255.0
        brake = gp.bLeftTrigger / 255.0
        
        btns = gp.wButtons
        b_tuple = (
            bool(btns & XINPUT_BUTTONS["X"]), bool(btns & XINPUT_BUTTONS["A"]),
            bool(btns & XINPUT_BUTTONS["B"]), bool(btns & XINPUT_BUTTONS["Y"]),
            bool(btns & XINPUT_BUTTONS["LEFT_SHOULDER"]), bool(btns & XINPUT_BUTTONS["RIGHT_SHOULDER"]),
            bool(btns & XINPUT_BUTTONS["DPAD_LEFT"]), bool(btns & XINPUT_BUTTONS["DPAD_RIGHT"]),
            bool(btns & XINPUT_BUTTONS["DPAD_UP"]), bool(btns & XINPUT_BUTTONS["DPAD_DOWN"]),
            bool(btns & XINPUT_BUTTONS["BACK"]), bool(btns & XINPUT_BUTTONS["START"]),
            bool(btns & XINPUT_BUTTONS["LEFT_THUMB"]), bool(btns & XINPUT_BUTTONS["RIGHT_THUMB"])
        )
        return stick_x, throttle, brake, b_tuple
    return 0.0, 0.0, 0.0, (False,) * 14

def run_physics_loop(update_hz=120.0):
    ctypes.windll.winmm.timeBeginPeriod(1)
    
    udp_listener = ForzaUdpTelemetryListener()
    udp_listener.start()
    
    assist = AdvancedGamepadAssist(runtime_config)
    output_steering = VJoySteering()

    frame_time = 1.0 / update_hz
    previous = time.perf_counter()

    try:
        while True:
            output_steering.set_device(runtime_config.vjoy_device)

            now = time.perf_counter()
            dt = clamp(now - previous, 0.001, 0.1)
            previous = now

            stick_x, throttle, brake, buttons = read_xinput_controls(runtime_config.controller_index)
            telemetry = udp_listener.get_latest()

            filtered_stick = assist.update(stick_x, telemetry, dt)
            output_steering.set_controls(filtered_stick, throttle, brake, buttons)

            target_time = previous + frame_time
            sleep_time = target_time - time.perf_counter()
            
            if sleep_time > 0.002:
                time.sleep(sleep_time - 0.002) 
                
            while time.perf_counter() < target_time:
                time.sleep(0)

    except (KeyboardInterrupt, SystemExit):
        output_steering.set_controls(0.0, 0.0, 0.0, (False,) * 14)
        set_gamepad_rumble(runtime_config.controller_index, 0.0, 0.0)
    finally:
        udp_listener.stop()
        ctypes.windll.winmm.timeEndPeriod(1)

runtime_config = Config()

if __name__ == "__main__":
    physics_thread = threading.Thread(
        target=run_physics_loop,
        daemon=True
    )

    physics_thread.start()

    app = AssistApp(runtime_config)
    app.run()
