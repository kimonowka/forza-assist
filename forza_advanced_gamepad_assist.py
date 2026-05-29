"""
Forza UDP Advanced Gamepad Assist prototype.

Pipeline:
    physical gamepad stick -> assist calculation -> vJoy steering output

This file focuses only on steering. It does not use vibration/rumble.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import socket
import struct
import tkinter as tk
import threading
import time
from typing import Optional

from inputs import get_gamepad
import pyvjoy


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Config:
    def __init__(self, gyro_strength: float = 0.9, lerp_factor: float = 0.2) -> None:
        self._lock = threading.Lock()
        self._gyro_strength = gyro_strength
        self._lerp_factor = lerp_factor

    def get_values(self) -> tuple[float, float]:
        with self._lock:
            return self._gyro_strength, self._lerp_factor

    def set_gyro_strength(self, value: float) -> None:
        with self._lock:
            self._gyro_strength = clamp(float(value), 0.0, 2.0)

    def set_lerp_factor(self, value: float) -> None:
        with self._lock:
            self._lerp_factor = clamp(float(value), 0.01, 0.5)


runtime_config = Config()


class AssistApp:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.root = tk.Tk()
        self.root.title("Forza Assist v0.1")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        gyro_strength, lerp_factor = self.config.get_values()

        tk.Label(self.root, text="FFB Strength").pack(
            padx=12, pady=(12, 0), anchor="w"
        )
        gyro_slider = tk.Scale(
            self.root,
            from_=0.0,
            to=2.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=260,
            command=lambda value: self.config.set_gyro_strength(float(value)),
        )
        gyro_slider.set(gyro_strength)
        gyro_slider.pack(padx=12, pady=(0, 10))

        tk.Label(self.root, text="Smoothness").pack(
            padx=12, pady=(4, 0), anchor="w"
        )
        lerp_slider = tk.Scale(
            self.root,
            from_=0.01,
            to=0.5,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            length=260,
            command=lambda value: self.config.set_lerp_factor(float(value)),
        )
        lerp_slider.set(lerp_factor)
        lerp_slider.pack(padx=12, pady=(0, 12))

    def on_closing(self) -> None:
        os._exit(0)

    def run(self) -> None:
        self.root.mainloop()


def start_config_gui(config: Config) -> threading.Thread:
    def run_gui() -> None:
        AssistApp(config).run()

    thread = threading.Thread(target=run_gui, name="AssistConfigGUI", daemon=True)
    thread.start()
    return thread


@dataclass(frozen=True)
class Telemetry:
    speed_mps: float
    front_tire_slip_angle: float
    angular_velocity_y: float


@dataclass
class AssistConfig:
    # Steering is integrated as velocity -> angle. Higher damping tracks the
    # stick faster; lower values feel heavier.
    base_damping: float = 26.0
    min_damping_under_slip: float = 10.0

    # Forza TireSlipAngle is normalized: 0 = grip, |angle| > 1.0 = loss of grip.
    slip_deadband: float = 0.04
    slip_counter_threshold: float = 0.15
    slip_full_effect: float = 1.05
    slip_target_weight_loss: float = 0.62

    # A7-style counter-steer/self-aligning terms.
    counter_steer_mix: float = 0.72
    counter_steer_gain: float = 0.82
    self_align_gain: float = 0.10

    # Stops numerical spikes after pauses without filtering normal frames.
    max_dt: float = 0.05


class AdvancedGamepadAssist:
    def __init__(
        self,
        config: Optional[AssistConfig] = None,
        runtime: Config = runtime_config,
    ) -> None:
        self.config = config or AssistConfig()
        self.runtime = runtime
        self.current_steer_angle = 0.0
        self.steer_velocity = 0.0

    def update(self, raw_stick_x: float, telemetry: Telemetry, dt: float) -> float:
        gyro_strength, lerp_factor = self.runtime.get_values()
        gyro_force = -telemetry.angular_velocity_y * gyro_strength
        
        target = gyro_force + raw_stick_x
        
        self.current_steer_angle = (self.current_steer_angle * (1.0 - lerp_factor)) + (target * lerp_factor)
        
        self.current_steer_angle = clamp(self.current_steer_angle, -1.0, 1.0)
        
        if self.current_steer_angle != self.current_steer_angle:
            self.current_steer_angle = 0
            
        return self.current_steer_angle

class VJoySteering:
    def __init__(self) -> None:
        self.device = pyvjoy.VJoyDevice(1)

    def set_steering(self, stick_x: float) -> None:
        normalized = clamp(stick_x, -1.0, 1.0)
        value = int(round((normalized + 1.0) * 0.5 * 32767.0))
        self.device.set_axis(pyvjoy.HID_USAGE_X, clamp(value, 0, 32767))

    def set_throttle(self, throttle: float) -> None:
        value = normalized_trigger_to_vjoy(throttle)
        self.device.set_axis(pyvjoy.HID_USAGE_SL0, value)

    def set_brake(self, brake: float) -> None:
        value = normalized_trigger_to_vjoy(brake)
        self.device.set_axis(pyvjoy.HID_USAGE_SL1, value)

    def set_buttons(self, buttons: tuple[bool, ...]) -> None:
        for button_id, pressed in enumerate(buttons, start=1):
            self.device.set_button(button_id, int(pressed))

    def set_controls(
        self,
        stick_x: float,
        throttle: float,
        brake: float,
        buttons: tuple[bool, ...],
    ) -> None:
        self.set_steering(stick_x)
        self.set_throttle(throttle)
        self.set_brake(brake)
        self.set_buttons(buttons)


def normalized_trigger_to_vjoy(value: float) -> int:
    return int(round(clamp(value, 0.0, 1.0) * 32767.0))


def normalize_signed_axis(value: int) -> float:
    if value < 0:
        return clamp(float(value) / 32768.0, -1.0, 1.0)
    return clamp(float(value) / 32767.0, -1.0, 1.0)


@dataclass(frozen=True)
class PhysicalControls:
    stick_x: float = 0.0
    stick_y: float = 0.0
    throttle: float = 0.0
    brake: float = 0.0
    buttons: tuple[bool, ...] = (False,) * 14


BUTTON_CODE_TO_INDEX = {
    "BTN_WEST": 0,    # X -> vJoy 1
    "BTN_SOUTH": 1,   # A -> vJoy 2
    "BTN_EAST": 2,    # B -> vJoy 3
    "BTN_NORTH": 3,   # Y -> vJoy 4
    "BTN_TL": 4,      # LB -> vJoy 5
    "BTN_TR": 5,      # RB -> vJoy 6
    "BTN_SELECT": 10, # Back -> vJoy 11
    "BTN_START": 11,  # Start -> vJoy 12
    "BTN_THUMBL": 12, # LS -> vJoy 13
    "BTN_THUMBR": 13, # RS -> vJoy 14
}


class InputsGamepadListener:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._controls = PhysicalControls()
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._running.set()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="InputsGamepadListener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()

    def get_latest(self) -> PhysicalControls:
        with self._lock:
            return self._controls

    def _listen_loop(self) -> None:
        while self._running.is_set():
            try:
                events = get_gamepad()
            except Exception:
                time.sleep(0.25)
                continue

            with self._lock:
                stick_x = self._controls.stick_x
                stick_y = self._controls.stick_y
                throttle = self._controls.throttle
                brake = self._controls.brake
                buttons = list(self._controls.buttons)

                for event in events:
                    if event.code == "ABS_X":
                        stick_x = normalize_signed_axis(event.state)
                    elif event.code == "ABS_Y":
                        stick_y = normalize_signed_axis(event.state)
                    elif event.code == "ABS_RZ":
                        throttle = clamp(float(event.state) / 255.0, 0.0, 1.0)
                    elif event.code == "ABS_Z":
                        brake = clamp(float(event.state) / 255.0, 0.0, 1.0)
                    elif event.code in BUTTON_CODE_TO_INDEX:
                        buttons[BUTTON_CODE_TO_INDEX[event.code]] = bool(event.state)
                    elif event.code == "ABS_HAT0X":
                        buttons[6] = event.state == -1
                        buttons[7] = event.state == 1
                    elif event.code == "ABS_HAT0Y":
                        buttons[8] = event.state == -1
                        buttons[9] = event.state == 1

                self._controls = PhysicalControls(
                    stick_x=stick_x,
                    stick_y=stick_y,
                    throttle=throttle,
                    brake=brake,
                    buttons=tuple(buttons),
                )


_gamepad_listener = InputsGamepadListener()


def initialize_physical_gamepad() -> None:
    _gamepad_listener.start()

class ForzaUdpTelemetryListener:
    PACKET_SIZE = 324
    ANGULAR_VELOCITY_Y_OFFSET = 48
    FRONT_LEFT_SLIP_OFFSET = 164
    FRONT_RIGHT_SLIP_OFFSET = 168
    SPEED_OFFSET = 256
    FLOAT32 = struct.Struct("<f")

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 20777,
        stale_after_sec: float = 0.5,
    ) -> None:
        self.host = host
        self.port = port
        self.stale_after_sec = stale_after_sec

        self._lock = threading.Lock()
        self._latest = Telemetry(
            speed_mps=0.0,
            front_tire_slip_angle=0.0,
            angular_velocity_y=0.0,
        )
        self._last_packet_time = 0.0
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._running.set()
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="ForzaUdpTelemetryListener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        sock = self._socket
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def get_latest(self) -> Telemetry:
        with self._lock:
            if time.monotonic() - self._last_packet_time > self.stale_after_sec:
                return Telemetry(
                    speed_mps=0.0,
                    front_tire_slip_angle=0.0,
                    angular_velocity_y=0.0,
                )
            return self._latest

    def _listen_loop(self) -> None:
        while self._running.is_set():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    self._socket = sock
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((self.host, self.port))
                    sock.settimeout(0.2)

                    while self._running.is_set():
                        try:
                            packet, _addr = sock.recvfrom(2048)
                        except socket.timeout:
                            continue
                        except OSError:
                            break

                        telemetry = self._parse_packet(packet)
                        if telemetry is None:
                            continue

                        with self._lock:
                            self._latest = telemetry
                            self._last_packet_time = time.monotonic()
            except OSError:
                if self._running.is_set():
                    time.sleep(0.5)
            finally:
                self._socket = None

    @classmethod
    def _parse_packet(cls, packet: bytes) -> Optional[Telemetry]:
        if len(packet) < cls.PACKET_SIZE:
            return None

        front_left_slip = cls.FLOAT32.unpack_from(
            packet, cls.FRONT_LEFT_SLIP_OFFSET
        )[0]
        front_right_slip = cls.FLOAT32.unpack_from(
            packet, cls.FRONT_RIGHT_SLIP_OFFSET
        )[0]
        angular_velocity_y = cls.FLOAT32.unpack_from(
            packet, cls.ANGULAR_VELOCITY_Y_OFFSET
        )[0]
        speed_mps = cls.FLOAT32.unpack_from(packet, cls.SPEED_OFFSET)[0]

        if not (
            math.isfinite(front_left_slip)
            and math.isfinite(front_right_slip)
            and math.isfinite(angular_velocity_y)
            and math.isfinite(speed_mps)
        ):
            return None

        front_slip_angle = (front_left_slip + front_right_slip) * 0.5
        return Telemetry(
            speed_mps=max(0.0, speed_mps),
            front_tire_slip_angle=front_slip_angle,
            angular_velocity_y=angular_velocity_y,
        )


_forza_udp_listener = ForzaUdpTelemetryListener()


def read_physical_stick_x() -> float:
    """
    Read the latest XInput steering value captured by the inputs thread.
    """
    return _gamepad_listener.get_latest().stick_x


def read_physical_controls() -> tuple[float, float, float, tuple[bool, ...]]:
    """
    Return latest steering, throttle, brake, buttons from the inputs thread.
    """
    controls = _gamepad_listener.get_latest()
    return controls.stick_x, controls.throttle, controls.brake, controls.buttons


def read_forza_telemetry() -> Telemetry:
    """
    Return the latest decoded Forza UDP telemetry.

    If no fresh UDP packet arrived recently, this intentionally returns zeroed
    telemetry so the assist model degrades to plain filtered steering.
    """
    _forza_udp_listener.start()
    return _forza_udp_listener.get_latest()


def run_filter_loop(update_hz: float = 120.0) -> None:
    start_config_gui(runtime_config)
    _forza_udp_listener.start()
    initialize_physical_gamepad()
    assist = AdvancedGamepadAssist(runtime=runtime_config)
    output = VJoySteering()

    frame_time = 1.0 / update_hz
    previous = time.perf_counter()

    try:
        while True:
            now = time.perf_counter()
            dt = now - previous
            previous = now

            raw_stick_x, throttle, brake, buttons = read_physical_controls()
            telemetry = read_forza_telemetry()

            filtered_stick_x = assist.update(raw_stick_x, telemetry, dt)
            output.set_controls(filtered_stick_x, throttle, brake, buttons)

            elapsed = time.perf_counter() - now
            time.sleep(max(0.0, frame_time - elapsed))
    except KeyboardInterrupt:
        output.set_controls(0.0, 0.0, 0.0, (False,) * 14)
    finally:
        _gamepad_listener.stop()
        _forza_udp_listener.stop()


if __name__ == "__main__":
    run_filter_loop()
