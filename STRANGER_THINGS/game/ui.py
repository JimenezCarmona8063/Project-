# game/ui.py — botones, sliders y HUD
import pygame
from settings import WHITE, UI_FONT_FILE


def _load_ui_font(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.Font(UI_FONT_FILE, size)
    except Exception:
        return pygame.font.SysFont("arial", size, bold=bold)

class Button:
    def __init__(self, rect, text, font, on_click, bg=(40,40,40), bg_hover=(60,60,60), fg=(255,255,255), hover_sound=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click = on_click
        self.bg = bg
        self.bg_hover = bg_hover
        self.fg = fg
        self.hover_sound = hover_sound
        self._hover = False
        self._armed = False
        self._played_hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was = self._hover
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover and not was and self.hover_sound:
                if not self._played_hover:
                    self.hover_sound.play()
                    self._played_hover = True
            if not self._hover:
                self._played_hover = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._armed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._armed and self.rect.collidepoint(event.pos):
                try:
                    self.on_click()
                except Exception:
                    pass
            self._armed = False

    def draw(self, surface):
        color = self.bg_hover if self._hover else self.bg
        pygame.draw.rect(surface, color, self.rect, border_radius=16)
        # borde suave
        pygame.draw.rect(surface, (0,0,0), self.rect, width=2, border_radius=16)
        # etiqueta
        s = self.font.render(self.text, True, self.fg)
        surface.blit(s, s.get_rect(center=self.rect.center))

class Slider:
    def __init__(self, rect, value=0.5):
        self.rect = pygame.Rect(rect)
        self.value = float(max(0.0, min(1.0, value)))
        self.drag = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.drag = True
            self._set_from_pos(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            self._set_from_pos(event.pos)

    def _set_from_pos(self, pos):
        x = pos[0]
        t = (x - self.rect.x) / max(1, self.rect.w)
        self.value = max(0.0, min(1.0, t))

    def draw(self, surface):
        pygame.draw.rect(surface, (60,60,60), self.rect, border_radius=8)
        knob_x = int(self.rect.x + self.value * self.rect.w)
        pygame.draw.circle(surface, (220,220,220), (knob_x, self.rect.centery), max(6, self.rect.h//3))

def draw_hud(surface, player):
    """HUD compacto con fondo semitransparente para mejorar la lectura."""

    hud_width = 280
    hud_height = 70
    margin = 16
    rect = pygame.Rect(
        margin,
        surface.get_height() - hud_height - margin,
        hud_width,
        hud_height,
    )

    # Fondo con sombra suave
    shadow = rect.move(3, 3)
    shadow_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, 140), shadow_surface.get_rect(), border_radius=18)
    surface.blit(shadow_surface, shadow.topleft)

    hud_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(hud_surface, (20, 20, 25, 180), hud_surface.get_rect(), border_radius=18)
    pygame.draw.rect(hud_surface, (255, 255, 255, 70), hud_surface.get_rect(), width=2, border_radius=18)
    surface.blit(hud_surface, rect.topleft)

    title_font = _load_ui_font(22, bold=True)
    body_font = _load_ui_font(18)

    hp = getattr(player, "hp", 100)
    inventory = getattr(player, "inventory", [])
    inv_count = len(inventory)
    inv_preview = ", ".join(map(str, inventory[:2]))
    if inv_count > 2:
        inv_preview += "…"

    title_text = title_font.render("Estado", True, WHITE)
    surface.blit(title_text, (rect.x + 18, rect.y + 12))

    line_y = rect.y + 40
    hp_text = body_font.render(f"HP: {hp}", True, (200, 230, 255))
    surface.blit(hp_text, (rect.x + 18, line_y))

    inv_label = body_font.render(f"Inventario ({inv_count}):", True, (200, 230, 255))
    surface.blit(inv_label, (rect.x + 110, line_y))
    if inv_count:
        inv_text = body_font.render(inv_preview, True, (255, 255, 200))
        surface.blit(inv_text, (rect.x + 110, line_y + 22))
    else:
        empty_text = body_font.render("Vacío", True, (150, 160, 190))
        surface.blit(empty_text, (rect.x + 110, line_y + 22))
