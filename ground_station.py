import sys
import paramiko
import threading
import json
import rtspstream as rtsp, pygame
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


def setup_connection():
    """Set the SSH connection with a raspberry using paramico"""

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=cfg.host, username=cfg.usr, timeout=10)
        print(f"Connected to {cfg.usr}@{cfg.host} succesfully")
        return ssh
    except Exception as e:
        print(f"Failed to connect to {cfg.usr}@{cfg.host}: {e}")
        sys.exit(1)


def main():

    pygame.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(tuple(cfg.screen_size))
    if cfg.fullscreen:
        pygame.display.toggle_fullscreen()

    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
    ssh = setup_connection()

    streams = []
    current_stream = 0

    try:
        with ssh:
            stdin, stdout, stderr = ssh.exec_command("python vesc-control.py")
            remote_output(stdout, stderr)

        streams = [
            rtsp.CameraStream(ip, 8550 + i)
            for i, ip in enumerate(cfg["cam_cfg"]["ip`s"])
        ]

        while True:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt

                if joystick is not None and event.type == pygame.JOYBUTTONUP:
                    if event.button == 0:
                        # streams[current_stream].stop()
                        current_stream = (current_stream + 1) % len(streams)
                        streams[current_stream].start()

            # ==========================
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

                # try:
                #     stdin.write(f"{json.dumps(data)}\n")
                #     stdin.flush()
                # except OSError as err:
                #     print(f"Lost controll channel, {err}")
                #     break
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
