import sys
import paramiko
import threading
import json
import rtspstream as rtsp, pygame
from typing import Optional
from box import Box

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
            rtsp.CameraStream(ip, 8550 + i)
            for i, ip in enumerate(cfg["cam_cfg"]["ip`s"])
        ]
        return streams
    except Exception as e:
        print(f"failed to create streams: {e}")
        return []


def init_screen() -> pygame.Surface:
    screen = pygame.display.set_mode(tuple(cfg.screen_size))
    if cfg.fullscreen:
        pygame.display.toggle_fullscreen()
    return screen


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


def main():
    pygame.init()
    clock = pygame.time.Clock()
    screen = init_screen()

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
                        current_stream = (current_stream + 1) % len(streams)
                        streams[current_stream].start()

            # ==========================
            if streams and screen:
                streams[current_stream].render_stream(screen)
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

            pygame.display.flip()
            clock.tick(30)

    finally:
        for stream in streams:
            stream.stop()

        if ssh:
            ssh.close()
        pygame.quit()


if __name__ == "__main__":
    main()
