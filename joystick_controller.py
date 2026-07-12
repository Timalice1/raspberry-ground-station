import pygame
from box import Box
import logging


class JoystickController:
    def __init__(self, cfg: Box):
        self.cfg = cfg
        self.joystick: pygame.joystick.Joystick | None = None

        self.deadzone = cfg.get("deadzone", 0.08)
        self.axis_thr = cfg.axis_thr
        self.axis_yaw = cfg.axis_yaw
        self.inv_thr = cfg.get("invert_thr", 1)
        self.inv_yaw = cfg.get("invert_yaw", 1)

    def init(self):
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            logging.info(f"Joystick connected: {self.joystick.get_name()}")
        else:
            logging.warning("No joysticks found connected")
            self.joystick = None

    @staticmethod
    def _remap(value: float, in_min, in_max, out_min, out_max) -> int:
        return int(
            out_min + ((value - in_min) / (in_max - in_min)) * (out_max - out_min)
        )

    def _read_axis(self, axis: int, invert: int):
        raw = self.joystick.get_axis(axis)
        return raw * invert if abs(raw) > self.deadzone else 0

    def get_input(self) -> dict[str, int] | None:
        if self.joystick is None:
            return None

        thr = self._read_axis(self.axis_thr, self.inv_thr)
        yaw = self._read_axis(self.axis_yaw, self.inv_yaw)

        return {
            "thr": int(self._remap(thr, -1, 1, 1000, 2000)),
            "yaw": int(self._remap(yaw, -1, 1, 1000, 2000)),
        }
