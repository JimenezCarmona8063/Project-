# game/ui.py — botones, sliders y HUD
import pygame
from settings import WHITE, RED, GREEN

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

def draw_hud(surface, player, planner_status=None):
    font = pygame.font.SysFont("arial", 18, bold=True)
    small = pygame.font.SysFont("arial", 16)

    bar_rect = pygame.Rect(12, 12, 220, 20)
    pygame.draw.rect(surface, (25, 25, 25), bar_rect, border_radius=8)
    inner = bar_rect.inflate(-4, -4)
    ratio = 1.0
    if getattr(player, "max_hp", 0):
        ratio = max(0.0, min(1.0, float(getattr(player, "hp", 0)) / float(player.max_hp)))
    pygame.draw.rect(surface, RED, inner, border_radius=6)
    fill = inner.copy()
    fill.width = int(inner.width * ratio)
    pygame.draw.rect(surface, GREEN, fill, border_radius=6)
    label = font.render(f"HP {int(getattr(player, 'hp', 0))}/{int(getattr(player, 'max_hp', 0))}", True, WHITE)
    surface.blit(label, (bar_rect.x, bar_rect.y - 24))

    info_lines = []
    room = getattr(player, "current_room", None)
    if room:
        info_lines.append(f"Salón: {room}")
    info_lines.append(f"Inventario: {len(getattr(player, 'inventory', []))}")

    y = bar_rect.bottom + 6
    for line in info_lines:
        s = small.render(line, True, WHITE)
        surface.blit(s, (bar_rect.x, y))
        y += s.get_height() + 2

    if planner_status:
        active_total = planner_status.get("active_total", 0)
        max_parallel = planner_status.get("max_parallel", active_total)
        queue = planner_status.get("queue", 0)
        buffer_size = planner_status.get("buffer", 0)
        resources = planner_status.get("resources", {})
        res_text = " ".join(
            f"{key[:1].upper()}{int(value)}" for key, value in resources.items()
        )
        planner_lines = [
            f"Acciones: {active_total}/{max_parallel}",
            f"Heap: {queue}  Buffer: {buffer_size}",
            f"Recursos: {res_text}",
        ]
        last_event = planner_status.get("last_event")
        if last_event:
            planner_lines.append(last_event)
        for line in planner_lines:
            s = small.render(line, True, WHITE)
            surface.blit(s, (bar_rect.x, y))
            y += s.get_height() + 2
