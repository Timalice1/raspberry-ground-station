import sys
import paramiko
import threading
import json
import rtspstream as rtsp, pygame
from typing import Optional
from box import Box
import pygame_gui as gui

with open("config.json", "r", encoding="utf-8") as file:
    cfg = Box(json.load(file))


def remap(value: float, in_min, in_max, out_min, out_max) -> int:
    return out_min + ((value - in_min) / (in_max - in_min)) * (out_max - out_min)


def remote_output(stdout, stderr):
    def _pump(stream, label):
        for line in iter(stream.readline, ""):
            if line:
                print(f"[remote:{label}] {line.rstrip()}")

    threading.Thread(target=_pump, args=(stdout, "out"), daemon=True).start()
    threading.Thread(target=_pump, args=(stderr, "err"), daemon=True).start()


def init_streams() -> Optional[list[rtsp.CameraStream]]:
    try:
        streams = [
            rtsp.CameraStream(ip, 8550 + i) for i, ip in enumerate(cfg.cam_cfg.ip)
        ]
        return streams
    except Exception as e:
        print(f"failed to create streams: {e}")
        return []


def init_screen():
    screen = pygame.display.set_mode(tuple(cfg.screen_size))
    if cfg.fullscreen:
        pygame.display.toggle_fullscreen()
    ui_manager = gui.UIManager(tuple(cfg.screen_size))
    return screen, ui_manager


class SSHConnector:
    def __init__(self):
        self.stdin = None
        self.ssh: Optional[paramiko.SSHClient] = None

    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=cfg.host, username=cfg.usr, timeout=10)
            print(f"Connected to {cfg.usr}@{cfg.host} succesfully")
            return True
        except Exception as e:
            print(f"Failed to connect to {cfg.usr}@{cfg.host}: {e}")
            return False

    def start_remote_controll(self):
        if not self.ssh:
            return False
        try:
            self.stdin, stdout, stderr = self.ssh.exec_command("python vesc-control.py")
            remote_output(stdout, stderr)
            return True
        except Exception as e:
            print(f"Failed to start remote controll, {e}")
            return False

    def send_command(self, cmd: dict):
        if self.stdin is None:
            return
        try:
            self.stdin.write(f"{json.dumps(cmd)}\n")
            self.stdin.flush()
        except OSError as err:
            print(f"Lost controll channel, {err}")

    def close(self):
        if self.ssh:
            self.ssh.close()


# =====UI=============
pygame.init()
screen, ui_manager = init_screen()

wight, height = screen.get_size()
cx = wight // 2
cy = height // 2

vid_label = gui.elements.UILabel(
    relative_rect=pygame.Rect(cx - 60, cy - 10, 120, 20),
    text="waiting for video",
    manager=ui_manager,
)


def main():
    clock = pygame.time.Clock()
    dt = clock.tick(30) / 1000.0

    ssh = SSHConnector()
    if not ssh.connect():
        sys.exit(1)

    if not ssh.start_remote_controll():
        ssh.close()

    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None

    try:
        current_stream = 0
        streams = init_streams()
        if streams is not None:
            streams[current_stream].start()

        while True:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt

                if joystick is not None and event.type == pygame.JOYBUTTONUP:
                    if event.button == 0 and streams:  # Cycle between cameras
                        # streams[current_stream].stop()
                        current_stream = (current_stream + 1) % len(streams)
                        streams[current_stream].start()

                ui_manager.process_events(event)

            # ==========================
            if streams and screen:
                if streams[current_stream].render_stream(screen):
                    vid_label.hide()
                else:
                    vid_label.show()
            # =========================

            # =======================================================================================
            if joystick is not None:

                deadzone = cfg["controller_cfg"]["deadzone"]
                axis_thr = cfg["controller_cfg"]["axis_thr"]
                axis_yaw = cfg["controller_cfg"]["axis_yaw"]
                inv_thr = cfg["controller_cfg"]["invert_thr"]
                inv_yaw = cfg["controller_cfg"]["invert_yaw"]

                thr = (
                    joystick.get_axis(axis_thr) * inv_thr
                    if abs(joystick.get_axis(axis_thr)) > deadzone
                    else 0
                )

                yaw = (
                    joystick.get_axis(axis_yaw) * inv_yaw
                    if abs(joystick.get_axis(axis_yaw)) > deadzone
                    else 0
                )

                data = {
                    "thr": int(remap(thr, -1, 1, 1000, 2000)),
                    "yaw": int(remap(yaw, -1, 1, 1000, 2000)),
                }

                ssh.send_command(data)
            # =======================================================================================

            ui_manager.draw_ui(screen)
            ui_manager.update(dt)
            pygame.display.update()

    finally:
        for stream in streams:
            stream.stop()

        if ssh:
            ssh.close()
        pygame.quit()


if __name__ == "__main__":
    main()
