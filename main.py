import json
import pygame
from box import Box
import logging

from ground_station import GroundStation, UIController, JoystickController


def main():
    logging.basicConfig(
        filename="ground_station.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        with open("config.json", "r", encoding="utf-8") as file:
            cfg = Box(json.load(file))
    except Exception as e:
        logging.exception(str(e))
        return

    pygame.init()

    gs: GroundStation | None = None
    ui: UIController | None = None
    controller: JoystickController | None = None

    try:
        ui = UIController(cfg)
        controller = JoystickController(cfg.controller_cfg)
        controller.init()

        gs = GroundStation(cfg, ui, controller)
        gs.setup()
        gs.run()

    except Exception as e:
        logging.exception(f"Unexpected exception in main loop:\t{e}")

    finally:
        if gs is not None:
            gs.stop()
        pygame.quit()
        logging.info("Shut down")


if __name__ == "__main__":
    main()
