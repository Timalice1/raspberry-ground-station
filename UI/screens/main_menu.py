from ..screen import Screen, gui, pygame
from box import Box
import json
import time
import threading

with open("config/config.json", "r", encoding="utf-8") as file:
    cfg = Box(json.load(file))


class MainMenuScreen(Screen):
    def __init__(self, on_connect, on_connected):
        super().__init__()
        self.on_connect = on_connect
        self.on_connected = on_connected
        self._connection_thread: threading.Thread | None = None

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

        self.container = gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 400, 500),
            manager=self.manager,
            anchors={"center": "center"},
        )

        y = -80
        self._connect_result_message = gui.elements.UILabel(
            relative_rect=pygame.Rect(0, y, 200, -1),
            manager=self.manager,
            text="Connection failed",
            container=self.container,
            anchors={"center": "center"},
        )
        self._connect_result_message.hide()

        y += 40

        self.user_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, y, 200, 35),
            initial_text=cfg.get("usr", "user"),
            placeholder_text="Username",
            manager=self.manager,
            container=self.container,
            anchors={"center": "center"},
        )
        y += 40

        self.host_field = gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(0, y, 200, 35),
            initial_text=cfg.get("host", "host"),  # grab a host from config
            placeholder_text="Host",
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

        self._connection_label = gui.elements.UILabel(
            relative_rect=pygame.Rect(0, y, 120, 35),
            text="Connecting...",
            manager=self.manager,
            container=self.container,
            anchors={"center": "center"},
        )

        self._footer = gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, -120, 380, 110),
            manager=self.manager,
            container=self.container,
            anchors={
                "centerx": "centerx",
                "bottom": "bottom",
            },
            object_id="#main_menu_footer",
        )

        self._resolution_selector = gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(0, 0, 120, 35),
            options_list=[str(x) for x in cfg.available_resolutions],
            starting_option=str(cfg.res),
            container=self._footer,
            manager=self.manager,
        )

        self._connection_label.hide()

    def on_exit(self):
        super().on_exit()
        if self._connection_thread and self._connection_thread.is_alive():
            self._connection_thread = None

    def _update_settings(self):
        cfg.user = self.user_field.get_text().strip()
        cfg.host = self.host_field.get_text().strip()
        cfg.res = self._resolution_selector.selected_option[0].strip()

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

        if not self._validate_credentials():
            return

        self._connect_result_message.hide()
        self.connect_btn.hide()
        self._connection_label.show()

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
            self._connection_label.hide()
            self._connect_result_message.show()
            self._connect_result_message.set_text(f"Connection failed: {msg}")
