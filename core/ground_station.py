import pygame
from box import Box
import logging

from services.joystick_controller import JoystickController
from services.ssh_connector import SSHConnector
from services.rtspstream import CameraStream


class GroundStation:

    def __init__(self, cfg: Box, joystick: JoystickController):
        self.cfg = cfg
        self.joystick = joystick

        self.ssh: SSHConnector | None = None
        self.rc_enabled = False

        self.streams: list[CameraStream] = []
        self.current_stream = 0

    def _init_connection(self):
        self.ssh = SSHConnector()
        if not self.ssh.connect(self.cfg.get("usr", ""), self.cfg.get("host", "")):
            raise RuntimeError("Failed to set up an ssh connection")
        self.rc_enabled = self.ssh.start_remote_controll()

    def _init_streams(self):
        if not self.cfg.cam_cfg.IPs:
            logging.warning("No camera IPs provided in config")
            return
        self.streams = [
            CameraStream(self.cfg, ip, 8550 + i)
            for i, ip in enumerate(self.cfg.cam_cfg.IPs)
        ]

    def setup(self):
        # Probably make that in separated thread, since that blocks the main thread
        self._init_connection()
        self._init_streams()
        if self.streams:
            self.streams[self.current_stream].start()

    def process_event(self, event):
        if self.joystick is not None and event.type == pygame.JOYBUTTONUP:
            if (
                event.button == self.cfg.controller_cfg.swich_cam_btn
            ):  # Cycle between cameras
                self._cycle_stream()

    def _process_rc(self):
        if not (self.rc_enabled and self.ssh is not None):
            return
        data = self.joystick.get_input()
        if data is not None:
            self.ssh.send_command(data)

    def update(self, delta_time: float):
        self._process_rc()

    def get_stream(self):
        if not self.streams:
            return None
        return self.streams[self.current_stream].read()

    def _cycle_stream(self):
        if not self.streams:
            return
        self.current_stream = (self.current_stream + 1) % len(self.streams)
        self.streams[self.current_stream].start()

    def stop(self):
        for stream in self.streams:
            stream.stop()
        if self.ssh:
            self.ssh.close()
