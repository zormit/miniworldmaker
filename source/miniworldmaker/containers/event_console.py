import os
import pygame
from miniworldmaker.containers.container import Container


class EventConsole(Container):

    event_id = 0

    def __init__(self):
        super().__init__()
        self._lines = 0
        self._height = self._lines * 20
        self._text_queue = []
        self.listen_to_all_events = True
        self.margin_first = 10
        self.margin_last = 5
        self.row_height = 25
        self.row_margin = 10
        self.margin_left = 10
        self.margin_right = 10
        self._dirty = 1

    def repaint(self):
        if self.dirty:
            self.surface.fill((255, 255, 255))
            package_directory = os.path.dirname(os.path.abspath(__file__))
            myfont = pygame.font.SysFont("monospace", 15)
            for i, text in enumerate(self._text_queue):
                row = pygame.Surface((self.width - (self.margin_left + self.margin_right), self.row_height))
                row.fill((200, 200, 200))
                label = myfont.render(text, 1, (0, 0, 0))
                row.blit(label, (10, 5))
                self.surface.blit(row, (self.margin_left, self.margin_first + i * 20 + i * self.row_margin))

    @property
    def lines(self):
        _lines = int(self.height - self.margin_first - self.margin_last) / (self.row_height)
        print(_lines)
        return _lines

    def get_event(self, event, data):
        text = "Nr: {0}, Event: {1}, Data: {2}".format(self.event_id, str(event), str(data))
        self.event_id += 1
        self._text_queue.append(text)
        if len(self._text_queue) > self.lines:
            self._text_queue.pop(0)
        self.dirty = 1