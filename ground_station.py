import pygame
from box import Box
import logging

from network.ssh_connector import SSHConnector
from network.rtspstream import CameraStream
from UI.ui_manager import UIController
from joystick_controller import JoystickController


class GroundStation:

    def __init__(
        self, cfg: Box, ui_controller: UIController, joystick: JoystickController
    ):
        self.running = False
        self.clock = pygame.time.Clock()
        self.cfg = cfg

        self.ssh: SSHConnector | None = None
        self.rc_enabled = False

        self.joystick = joystick

        self.streams = []
        self.current_stream = 0

        self.ui_controller = ui_controller

    def _init_connection(self):
        # TODO: add a reconection timeout
        self.ssh = SSHConnector()
        if not self.ssh.connect(self.cfg.get("usr", ""), self.cfg.get("host", "")):
            raise RuntimeError("Failsed to set up an ssh connection")
        self.rc_enabled = self.ssh.start_remote_controll()

    def _init_streams(self):
        if not self.cfg.cam_cfg.IPs:
            logging.warning("No camera IPs prowided in config")
            return
        self.streams = [
            CameraStream(self.cfg, ip, 8550 + i)
            for i, ip in enumerate(self.cfg.cam_cfg.IPs)
        ]

    def setup(self):
        # Probably make that in separated thread, since that blocks the main thread
        self._init_connection()
        self._init_streams()
        self.running = True

    def run(self):
        if self.streams:
            self.streams[self.current_stream].start()

        while self.running:
            dt = self.clock.tick(self.cfg.get("target_fps", 30)) / 1000.0

            self._process_events()
            self._process_rc_command()

            if self.streams:
                frame = self.streams[self.current_stream].read()
                self.ui_controller.render_frame(frame)

            self.ui_controller.update(dt)

    def _process_events(self):
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.joystick is not None and event.type == pygame.JOYBUTTONUP:
                if (
                    event.button == self.cfg.controller_cfg.swich_cam_btn
                ):  # Cycle between cameras
                    self._cycle_stream()

            self.ui_controller.process_event(event)

    def _process_rc_command(self):
        if not (self.rc_enabled and self.ssh is not None):
            return
        data = self.joystick.get_input()
        if data is not None:
            self.ssh.send_command(data)

    def _cycle_stream(self):
        if not self.streams:
            return
        self.current_stream = (self.current_stream + 1) % len(self.streams)
        self.streams[self.current_stream].start()

    def stop(self):
        self.running = False
        for stream in self.streams:
            stream.stop()
        if self.ssh:
            self.ssh.close()
