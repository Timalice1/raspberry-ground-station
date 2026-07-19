from pygame_gui.core import UIElement, UIContainer


class LayoutContainer(UIContainer):

    def __init__(
        self,
        relative_rect,
        manager,
        *,
        container=None,
        object_id=None,
        element_id=None,
        anchors=None,
        orientation: str = "vertical",
        padding: float = 0,
        spacing: float = 0
    ):
        super().__init__(
            relative_rect,
            manager,
            container=container,
            object_id=object_id,
            element_id=element_id,
            anchors=anchors,
        )
        self.padding = padding
        self.spacing = spacing
        self.orientation = orientation
        self.cursor = self.padding

    def add_entry(self, entry: UIElement, margin: float = 10, align: str = "left"):
        """Append a new element entry to the container"""
        self.cursor += margin

        entry_size = 0

        if self.orientation == "vertical":
            x = self._allign_entry(
                entry.relative_rect.width, self.rect.width, self.padding, align=align
            )
            entry.set_relative_position((x, self.cursor))
            entry_size = entry.relative_rect.height

        if self.orientation == "horizontal":
            y = self._allign_entry(
                entry.relative_rect.height, self.rect.height, self.padding, align=align
            )
            entry.set_relative_position((self.cursor, y))
            entry_size = entry.relative_rect.width

        self.cursor += entry_size + self.spacing
        self._scale_container()

    def _scale_container(self):
        content_size = self.cursor - self.spacing + self.padding
        if self.orientation == "vertical":
            self.set_dimensions((self.relative_rect.width, content_size))
        if self.orientation == "horizontal":
            self.set_dimensions((content_size, self.relative_rect.height))

    def _allign_entry(
        self, entry_size: float, container_size: float, padding: float, align: str
    ) -> float:
        if align in ("left", "top"):
            return padding
        if align == "center":
            return (container_size - entry_size) / 2
        if align in ("right", "bottom"):
            return container_size - padding - entry_size
        return 0
