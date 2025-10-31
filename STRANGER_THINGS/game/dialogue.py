# game/dialogue.py — cajita de diálogos con páginas
import pygame
from settings import WIDTH, HEIGHT, UI_FONT_FILE


def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.Font(UI_FONT_FILE, size)
    except Exception:
        return pygame.font.SysFont("arial", size, bold=bold)

class DialogueBox:
    def __init__(self, lines, speaker=None):
        self.lines = list(lines) if lines else ["..."]
        self.speaker = speaker
        self.idx = 0
        self.done = False
        self.font = _load_font(24)
        self.font_name = _load_font(26, bold=True)
        self.prompt_font = _load_font(18)

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONUP):
            self.idx += 1
            if self.idx >= len(self.lines):
                self.done = True

    def draw(self, surface):
        w, h = surface.get_size()
        ph = max(120, h//5)
        rect = pygame.Rect(10, h - ph - 10, w - 20, ph)

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 12, 18, 220), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (255, 255, 255, 90), panel.get_rect(), width=3, border_radius=18)
        surface.blit(panel, rect.topleft)

        y = rect.y + 12
        if self.speaker:
            s = self.font_name.render(self.speaker, True, (255,230,120))
            surface.blit(s, (rect.x + 12, y))
            y += s.get_height() + 6

        text = self.lines[self.idx] if self.idx < len(self.lines) else ""
        self._blit_wrapped(surface, text, rect.x + 12, y, rect.w - 24)

        if not self.done:
            prompt = self.prompt_font.render("Pulsa para continuar", True, (200, 220, 255))
            surface.blit(prompt, (rect.right - prompt.get_width() - 16, rect.bottom - prompt.get_height() - 14))

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
