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
    current_stream: str | None
    telem: dict | None
    # Any another data that needs to be displayed
    # ...


class GroundStation:

    def __init__(self, joystick: JoystickController):
        self.joystick = joystick
        self.cfg: Box | None = None

        self.ssh: SSHConnector | None = None
        self.rc_enabled = False
        self._current_direction: int = 1

        self.streams: dict[str, CameraStream] = {}
        self.current_stream: str | None = None

        self.running = False

    def _init_streams(self):

        cameras = self.cfg.cam_cfg.get("cameras", {})
        if not cameras:
            logging.warning("No camera provided in config")
            return

        self.streams = {
            name: CameraStream(self.cfg, ip, 8550 + i)
            for i, (name, ip) in enumerate(cameras.items())
        }
        self.current_stream = next(iter(self.streams))

    def connect(self, cfg: Box):
        self.cfg = cfg
        self.ssh = SSHConnector()
        connected, msg = self.ssh.connect(
            self.cfg.get("usr", ""), self.cfg.get("host", "")
        )
        if not connected:
            logging.error("Failed to set up SSH connection")
            return False, msg
        self._init_streams()
        return True, ""

    def run(self):
        if self.streams and self.current_stream:
            self.streams[self.current_stream].start()
        self.rc_enabled = self.ssh.start_remote_controll()
        self.running = True

    def process_event(self, event):
        if self.joystick.connected and event.type == pygame.JOYBUTTONUP:

            if (
                event.button == self.cfg.controller_cfg.swich_cam_btn
            ):  # Cycle between cameras
                self._cycle_stream()

    def _process_rc(self):
        if not (self.joystick.connected or self.rc_enabled) or self.ssh is None:
            return
        data = self.joystick.get_input(self._current_direction)
        if data is not None:
            self.ssh.send_command(data)

    def update(self, delta_time: float):
        if not self.running:
            return
        self._process_rc()

    def _get_stream(self):
        if not (self.streams or self.current_stream):
            return None
        return self.streams[self.current_stream].read()

    def _cycle_stream(self):
        if not self.streams or len(self.streams) <= 1 or not self.current_stream:
            return

        names = list(self.streams.keys())
        index = names.index(self.current_stream)
        index = (index + 1) % len(names)

        self.current_stream = names[index]
        self.streams[self.current_stream].start()

        if self.current_stream == "back" and self.cfg.get(
            "invert_rc_on_cam_switch", False
        ):
            self._invert_control()

    def _invert_control(self):
        self._current_direction *= -1

    def snapshot(self) -> GSSnapshot:
        """Creates a current state snapshot, that will be provided to the GUI"""

        telem = None
        if self.ssh and self.rc_enabled:
            data = self.ssh.read_telemetry()
            if data is not None:
                telem = json.loads(data)

        return GSSnapshot(
            frame=self._get_stream(),
            current_stream=(
                self.current_stream.upper() if self.current_stream is not None else None
            ),
            telem=telem,
        )

    def stop(self):
        for name, stream in self.streams.items():
            stream.stop()
        if self.ssh:
            self.ssh.close()
