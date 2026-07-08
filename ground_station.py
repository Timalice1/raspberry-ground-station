import json
import pygame
import pygame_gui as gui
from box import Box
from typing import Optional
import logging

from network.ssh_connector import SSHConnector
from network.rtspstream import CameraStream

with open("config.json", "r", encoding="utf-8") as file:
    cfg = Box(json.load(file))


def remap(value: float, in_min, in_max, out_min, out_max) -> int:
    return out_min + ((value - in_min) / (in_max - in_min)) * (out_max - out_min)


def init_streams() -> Optional[list[CameraStream]]:
    try:
        streams = [CameraStream(ip, 8550 + i) for i, ip in enumerate(cfg.cam_cfg.IPs)]
        return streams
    except Exception as e:
        logging.exception(e)
        return []


def init_screen():
    screen = pygame.display.set_mode(tuple(cfg.screen_size))
    if cfg.fullscreen:
        pygame.display.toggle_fullscreen()
    ui_manager = gui.UIManager(tuple(cfg.screen_size))
    return screen, ui_manager


def init_connection():
    ssh = SSHConnector()
    connected, msg = ssh.connect(cfg.usr, cfg.host)
    if not connected:
        logging.error(msg)
        return None, False
    logging.info(msg)

    rc_enabled, msg = ssh.start_remote_controll()
    if not rc_enabled:
        logging.error(msg)
        # ssh.close() # TODO: probably i still ant to hold a connection
        return ssh, False
    logging.info(msg)

    return ssh, rc_enabled


pygame.init()
screen, ui_manager = init_screen()


def main():
    logging.basicConfig(filename="groung_station.log", filemode="w", level=logging.INFO)
    clock = pygame.time.Clock()
    dt = clock.tick(cfg.get("target_fps", 30)) / 1000.0

    ssh, rc_enabled = init_connection()
    streams = init_streams()

    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
    if joystick is None:
        logging.warning("No joysticks found connected")
    else:
        logging.info(f"Joystick connected: {joystick.get_name()}")

    try:
        current_stream = 0
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

                ui_manager.process_events(event)

            # ==========================
            if streams and screen:
                streams[current_stream].render_stream(screen)

            # =======================================================================================
            if joystick is not None and rc_enabled:
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

                msg = ssh.send_command(data)
            # =======================================================================================

            ui_manager.draw_ui(screen)
            ui_manager.update(dt)
            pygame.display.update()

    except KeyboardInterrupt:
        logging.info("shut down")
    except Exception as e:
        logging.exception(f"Unexpected exception in main loop:\t{e}")

    finally:
        for stream in streams:
            stream.stop()

        if ssh:
            ssh.close()
        pygame.quit()


if __name__ == "__main__":
    main()
