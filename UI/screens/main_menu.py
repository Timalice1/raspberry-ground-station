from ..screen import Screen, gui, pygame


class MainMenuScreen(Screen):
    def __init__(self, on_connect):
        super().__init__()
        self.on_connect = on_connect

    def on_enter(self, manager, screen_size):
        super().on_enter(manager, screen_size)

    def _try_connect(self):
        # Get connection credentials
        # Start a separated thread
        self.on_connect()
