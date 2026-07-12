import json
import pygame
from box import Box
import logging
import sys

from core.ground_station import GroundStation
from services.joystick_controller import JoystickController
from UI.ui_manager import UIController

CONFIG_PATH = "config/config.json"
LOG_PATH = "ground_station.log"


def load_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            return Box(json.load(file))
    except Exception as e:
        logging.exception(str(e))
        sys.exit(1)


def main():
    logging.basicConfig(
        filename=LOG_PATH,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg = load_cfg()

    pygame.init()
    clock = pygame.time.Clock()
    gs: GroundStation | None = None
    ui: UIController | None = None
    controller: JoystickController | None = None

    running = True
    try:

        ui = UIController(cfg)

        controller = JoystickController(cfg.controller_cfg)
        controller.init()

        gs = GroundStation(cfg, controller)
        gs.setup()

        while running:
            dt = clock.tick(cfg.get("target_fps", 30)) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                gs.process_event(event)
                ui.process_event(event)

            stream = gs.get_stream()
            if stream is not None:
                ui.render_stream(stream)

            gs.update(dt)
            ui.update(dt)

    except Exception as e:
        logging.exception(f"Exception in main loop:\t{str(e)}")

    finally:
        if gs is not None:
            gs.stop()
        pygame.quit()
        logging.info("Shut down")


if __name__ == "__main__":
    main()
