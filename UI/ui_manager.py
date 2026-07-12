import pygame
import pygame_gui as gui
from box import Box
import logging
from typing import Optional
import numpy as np


class UIController:
    def __init__(self, cfg: Box):
        self.cfg: Box = cfg

        self.screen_size = tuple(cfg.screen_size)
        self.screen: pygame.Surface = self._init_screen()
        self.ui_manager = gui.UIManager(tuple(self.cfg.screen_size))

    def _init_screen(self):
        return pygame.display.set_mode(
            size=tuple(self.cfg.screen_size),
            flags=pygame.FULLSCREEN if self.cfg.fullscreen else 0,
        )

    def render_stream(self, frame: Optional[np.ndarray]):
        self.screen.fill((0, 0, 12))

        if frame is None:
            return False

        screen_w, screen_h = self.screen.get_size()
        frame_h, frame_w = frame.shape[:2]

        scale = min(screen_w / frame_w, screen_h / frame_h)
        new_w, new_h = int(frame_w * scale), int(frame_h * scale)

        x = (screen_w - new_w) // 2
        y = (screen_h - new_h) // 2

        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        frame_surface = pygame.transform.smoothscale(frame_surface, (new_w, new_h))

        self.screen.blit(frame_surface, (x, y))
        return True

    def update(self, delta_time: float):
        self.ui_manager.update(delta_time)
        self.ui_manager.draw_ui(self.screen)
        pygame.display.update()

    def process_event(self, event):
        self.ui_manager.process_events(event)
