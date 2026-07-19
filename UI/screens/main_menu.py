from ..screen import Screen, gui, pygame
from box import Box
import json
import threading

from ..components.layout_container import LayoutContainer

with open("config/config.json", "r", encoding="utf-8") as file:
    cfg = Box(json.load(file))


class MainMenuScreen(Screen):
    def __init__(self, on_connect=None, on_connected=None):
        super().__init__()
        self.on_connect = on_connect
        self.on_connected = on_connected
        self._connection_thread: threading.Thread | None = None

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

        self.container = gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 300, 250),
            manager=self.manager,
            anchors={"center": "center"},
        )

        _vertical_box = LayoutContainer(
            relative_rect=pygame.Rect(0, 0, 250, 0),
            manager=self.manager,
            padding=0,
            spacing=5,
            container=self.container,
            orientation="vertical",
            anchors={"center": "center"},
        )

        self.user_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, 0, 250, 35),
            initial_text=cfg.get("usr", "user"),
            placeholder_text="Username",
            manager=self.manager,
            container=_vertical_box,
        )

        self.host_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, 0, 250, 35),
            initial_text=cfg.get("host", "host"),  # grab a host from config
            placeholder_text="Host",
            manager=self.manager,
            container=_vertical_box,
        )

        self.connect_btn = gui.elements.UIButton(
            relative_rect=pygame.Rect(0, 0, 120, 35),
            text="Connect",
            manager=self.manager,
            command=self._try_connect,
            container=_vertical_box,
        )

        _vertical_box.add_entry(self.user_field, 5, "center")
        _vertical_box.add_entry(self.host_field, 5, "center")
        _vertical_box.add_entry(self.connect_btn, 5, "center")

    def on_exit(self):
        super().on_exit()
        if self._connection_thread and self._connection_thread.is_alive():
            self._connection_thread = None

    def _update_settings(self):
        cfg.user = self.user_field.get_text().strip()
        cfg.host = self.host_field.get_text().strip()
        # cfg.res = self._resolution_selector.selected_option[0].strip()

        with open("config/config.json", "w", encoding="utf-8") as file:
            json.dump(cfg.to_dict(), file, indent=4)

    def _validate_credentials(self) -> bool:
        user = self.user_field.get_text().strip()
        host = self.host_field.get_text().strip()
        if not (user or host):
            return False

        self._update_settings()
        return True

    def _try_connect(self):
        # Get connection credentials
        # Start a separated thread

        if self.on_connect is None:
            return

        if not self._validate_credentials():
            return

        self.connect_btn.hide()

        if self._connection_thread and not self._connection_thread.is_alive():
            self._connection_thread = None

        self._connection_thread = threading.Thread(
            target=self._run_connection, daemon=True
        )
        self._connection_thread.start()

    def _run_connection(self):
        ok, msg = self.on_connect(cfg)
        if ok:
            self.on_connected()
        else:
            self.connect_btn.show()
