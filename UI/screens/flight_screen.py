from ..screen import Screen, pygame, gui, GSSnapshot
import numpy as np


class FlightScreen(Screen):
    def __init__(self):
        super().__init__()

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

    def on_exit(self):
        return super().on_exit()

    def draw(self, surface, snapshot=None):
        self._render_stream(surface, snapshot.frame)

    def update(self, dt):
        return super().update(dt)

    def process_event(self, event):
        return super().process_event(event)

    def _render_stream(self, surf: pygame.Surface, frame: np.ndarray | None = None):
        if frame is None:
            return

        screen_w, screen_h = surf.get_size()
        frame_h, frame_w = frame.shape[:2]

        scale = min(screen_w / frame_w, screen_h / frame_h)
        new_w, new_h = int(frame_w * scale), int(frame_h * scale)

        x = (screen_w - new_w) // 2
        y = (screen_h - new_h) // 2

        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        frame_surface = pygame.transform.smoothscale(frame_surface, (new_w, new_h))

        surf.blit(frame_surface, (x, y))
