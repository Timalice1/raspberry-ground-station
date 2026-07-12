from abc import ABC
import logging
import pygame_gui as gui
import pygame

from core.ground_station import GSSnapshot


class Screen(ABC):
    def __init__(self):
        """Reusable abstract screen interface"""

        self.manager: gui.UIManager = None
        self.screen_size: tuple[int, int]
        self.container: gui.elements.UIPanel | None = None

    def on_enter(self, manager: gui.UIManager, screen_size: tuple[int, int]) -> None:
        self.manager = manager
        self.screen_size = screen_size
        """Builds a screen widgets"""

    def on_exit(self) -> None:
        """Tear down widget. Called when leaving the screen"""

    def process_event(self, event: pygame.event.Event) -> None:
        """React to a pygame_gui event (UI_BUTTON_PRESSED etc)."""
        if self.container is not None:
            self.container.kill()
            self.container = None

    def update(self, dt: float) -> None:
        """Non-UI per-frame logic (polling a thread result queue, etc)."""

    def draw(self, surface: pygame.Surface, snapshot: GSSnapshot | None = None) -> None:
        """Anything drawn manually, underneath the UI manager's own draw."""
