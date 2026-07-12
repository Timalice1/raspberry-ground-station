import json
import pygame
from box import Box
import logging
import sys

from core.ground_station import GroundStation
from services.joystick_controller import JoystickController


from UI import UIController, FlightScreen, MainMenuScreen

CONFIG_PATH = "config/config.json"
LOG_PATH = "ground_station.log"


def load_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            return Box(json.load(file))
    except Exception as e:
        logging.exception(str(e))
        sys.exit(1)


def fake_Connect(user: str, host: str):
    print(f"{user}@{host}")


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

        controller = JoystickController(cfg.controller_cfg)
        controller.init()

        gs = GroundStation(controller)
        # gs.setup()

        ui = UIController(cfg)

        def open_flight():
            ui.open_screen(FlightScreen())

        ui.open_screen(MainMenuScreen(on_connect=gs.setup, on_connected=open_flight))

        while running:
            dt = clock.tick(cfg.get("target_fps", 30)) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                gs.process_event(event)
                ui.process_event(event)

            gs.update(dt)
            ui.update(dt)
            ui.draw(gs.snapshot())
            pygame.display.update()

    except Exception as e:
        logging.exception(f"Exception in main loop:\t{str(e)}")

    finally:
        if gs is not None:
            gs.stop()
        pygame.quit()
        logging.info("Shut down")


if __name__ == "__main__":
    main()
