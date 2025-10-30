# game/dialogue.py — cajita de diálogos con páginas
import pygame
from settings import WIDTH, HEIGHT

class DialogueBox:
    def __init__(self, lines, speaker=None):
        self.lines = list(lines) if lines else ["..."]
        self.speaker = speaker
        self.idx = 0
        self.done = False
        self.font = pygame.font.SysFont("arial", 22)
        self.font_name = pygame.font.SysFont("arial", 20, bold=True)

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONUP):
            self.idx += 1
            if self.idx >= len(self.lines):
                self.done = True

    def draw(self, surface):
        w, h = surface.get_size()
        ph = max(120, h//5)
        rect = pygame.Rect(10, h - ph - 10, w - 20, ph)
        pygame.draw.rect(surface, (0,0,0), rect, border_radius=12)
        pygame.draw.rect(surface, (255,255,255), rect, width=2, border_radius=12)

        y = rect.y + 12
        if self.speaker:
            s = self.font_name.render(self.speaker, True, (255,230,120))
            surface.blit(s, (rect.x + 12, y))
            y += s.get_height() + 6

        text = self.lines[self.idx] if self.idx < len(self.lines) else ""
        self._blit_wrapped(surface, text, rect.x + 12, y, rect.w - 24)

    def _blit_wrapped(self, surface, text, x, y, maxw):
        words = str(text).split()
        line = ""
        while words:
            test = line + ("" if line=="" else " ") + words[0]
            srf = self.font.render(test, True, (230,230,230))
            if srf.get_width() <= maxw:
                line = test
                words.pop(0)
            else:
                srf2 = self.font.render(line, True, (230,230,230))
                surface.blit(srf2, (x, y))
                y += srf2.get_height() + 2
                line = ""
        if line:
            srf2 = self.font.render(line, True, (230,230,230))
            surface.blit(srf2, (x, y))
