from ..screen import Screen, pygame, gui
import numpy as np
from ..widgets.minimap_widget import MininmapWidget


class FlightScreen(Screen):
    def __init__(self):
        super().__init__()

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

        self._signal_label = gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 0, 200, -1),
            text="NO DATA",
            manager=self.manager,
            anchors={"center": "center"},
        )
        self._signal_label.hide()

        self._header = gui.elements.UIPanel(
            relative_rect=(0, 0, screen_size[0], 50),
            manager=self.manager,
            object_id="#flight_screen_header",
        )

        self._battery_indicator = gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 0, -1, -1),
            text="BAT: 0V",
            manager=self.manager,
            container=self._header,
            anchors={
                "centery": "centery",
                "left": "left",
            },
        )

    def draw(self, surface, snapshot=None):
        self._signal_label.set_text(f"NO DATA FOR {snapshot.current_stream}")
        self._render_stream(surface, snapshot.frame)
        if snapshot.telem is not None:
            voltage: float = snapshot.telem.get("voltage", 0)
            self._battery_indicator.set_text(f"BAT: {voltage:.2f}V")

    def _render_stream(self, surf: pygame.Surface, frame: np.ndarray | None = None):
        if frame is None:
            self._signal_label.show()
            return

        self._signal_label.hide()

        screen_w, screen_h = surf.get_size()
        frame_h, frame_w = frame.shape[:2]

        scale = min(screen_w / frame_w, screen_h / frame_h)
        new_w, new_h = int(frame_w * scale), int(frame_h * scale)

        x = (screen_w - new_w) // 2
        y = (screen_h - new_h) // 2

        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        frame_surface = pygame.transform.smoothscale(frame_surface, (new_w, new_h))

        surf.blit(frame_surface, (x, y))
