import pygame
from box import Box
import logging
from dataclasses import dataclass
import json

from services.joystick_controller import JoystickController
from services.ssh_connector import SSHConnector
from services.rtspstream import CameraStream, np


@dataclass(frozen=True)
class GSSnapshot:
    """Snapshot data class, that will provide a data from a backend to a frontend"""

    frame: np.ndarray | None
    telem: dict | None
    # Any another data that needs to be displayed
    # ...


class GroundStation:

    def __init__(self, joystick: JoystickController):
        self.joystick = joystick
        self.cfg: Box | None = None

        self.ssh: SSHConnector | None = None
        self.rc_enabled = False

        self.streams: list[CameraStream] = []
        self.current_stream = 0

    def _init_streams(self):
        if not self.cfg.cam_cfg.IPs:
            logging.warning("No camera IPs provided in config")
            return
        self.streams = [
            CameraStream(self.cfg, ip, 8550 + i)
            for i, ip in enumerate(self.cfg.cam_cfg.IPs)
        ]

    def connect(self, cfg: Box):
        self.cfg = cfg
        self.ssh = SSHConnector()
        connected, msg = self.ssh.connect(
            self.cfg.get("usr", ""), self.cfg.get("host", "")
        )
        if not connected:
            logging.error("Failed to set up SSH connection")
            return False, msg
        return True, ""

    def run(self):
        self._init_streams()
        if self.streams:
            self.streams[self.current_stream].start()
        self.rc_enabled = self.ssh.start_remote_controll()

    def process_event(self, event):
        if self.joystick.connected and event.type == pygame.JOYBUTTONUP:
            if (
                event.button == self.cfg.controller_cfg.swich_cam_btn
            ):  # Cycle between cameras
                self._cycle_stream()

    def _process_rc(self):
        if not (self.joystick.connected or self.rc_enabled and self.ssh is not None):
            return
        data = self.joystick.get_input()
        if data is not None:
            self.ssh.send_command(data)

    def update(self, delta_time: float):
        self._process_rc()

    def _get_stream(self):
        if not self.streams:
            return None
        return self.streams[self.current_stream].read()

    def _cycle_stream(self):
        if not self.streams:
            return
        self.current_stream = (self.current_stream + 1) % len(self.streams)
        self.streams[self.current_stream].start()

    def snapshot(self) -> GSSnapshot:
        """Creates a current state snapshot, that will be provided to the GUI"""
        telem = None
        if self.ssh and self.rc_enabled:
            telem = json.loads(self.ssh.read_telemetry())
        return GSSnapshot(frame=self._get_stream(), telem=telem)

    def stop(self):
        for stream in self.streams:
            stream.stop()
        if self.ssh:
            self.ssh.close()
