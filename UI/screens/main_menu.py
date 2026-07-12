from ..screen import Screen, gui, pygame
from box import Box
import json
import time

with open("config/config.json", "r", encoding="utf-8") as file:
    cfg = Box(json.load(file))


class MainMenuScreen(Screen):
    def __init__(self, on_connect, on_connected):
        super().__init__()
        self.on_connect = on_connect
        self.on_connected = on_connected

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

        self.container = gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 400, 400),
            manager=self.manager,
            anchors={"center": "center"},
        )

        y = -40
        self.user_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, y, 200, 35),
            initial_text=cfg.get("usr", "user"),
            manager=self.manager,
            container=self.container,
            anchors={"center": "center"},
        )
        y += 40

        self.host_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, y, 200, 35),
            initial_text=cfg.get("host", "host"),  # grab a host from config
            manager=self.manager,
            container=self.container,
            anchors={"center": "center"},
        )
        y += 45

        self.connect_btn = gui.elements.UIButton(
            relative_rect=pygame.Rect(0, y, 120, 35),
            text="Connect",
            manager=self.manager,
            command=self._try_connect,
            container=self.container,
            anchors={"center": "center"},
        )

    def _try_connect(self):
        # Get connection credentials
        # Start a separated thread
        user = self.user_field.get_text().strip()
        host = self.host_field.get_text().strip()

        cfg.usr = user
        cfg.host = host

        with open("config/config.json", "w", encoding="utf-8") as file:
            json.dump(cfg.to_dict(), file, indent=4)

        time.sleep(1)

        if self.on_connect(cfg):
            self.on_connected()
