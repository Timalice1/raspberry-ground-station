import pygame
import pygame_gui as gui
from box import Box
import logging
import numpy as np

from core.ground_station import GSSnapshot
from .screen import Screen


class UIController:
    def __init__(self, cfg: Box):
        self.cfg: Box = cfg

        self.screen_size = tuple(cfg.screen_size)
        self.window: pygame.Surface = self._init_window()
        self.ui_manager = gui.UIManager(tuple(self.cfg.screen_size))

        self._current_screen: Screen | None = None

    def _init_window(self):
        return pygame.display.set_mode(
            size=tuple(self.cfg.screen_size),
            flags=pygame.FULLSCREEN if self.cfg.fullscreen else 0,
        )

    def open_screen(self, screen: Screen):
        if self._current_screen is not None:
            self._current_screen.on_exit()
        self._current_screen = screen
        self._current_screen.on_enter(self.ui_manager, self.screen_size)

    def draw(self, snapshot: GSSnapshot):
        self.window.fill((0, 0, 15))
        if self._current_screen is not None:
            self._current_screen.draw(self.window, snapshot)
        self.ui_manager.draw_ui(self.window)

    def update(self, delta_time: float):
        if self._current_screen is not None:
            self._current_screen.update(delta_time)

        self.ui_manager.update(delta_time)

    def process_event(self, event):
        self.ui_manager.process_events(event)
        if self._current_screen is not None:
            self._current_screen.process_event(event)
