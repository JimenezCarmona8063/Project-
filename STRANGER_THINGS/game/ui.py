# game/ui.py — botones, sliders y HUD
import pygame
from settings import (
    WHITE,
    RED,
    GREEN,
    BLUE,
    ORANGE,
    PURPLE,
    HUD_PANEL_WIDTH,
    KEY_UP,
    KEY_DOWN,
    KEY_LEFT,
    KEY_RIGHT,
    KEY_INTERACT,
    KEY_INVENTORY,
    KEY_ACTION_RUSH,
    KEY_FIGHT,
    KEY_MESSAGE,
)

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

def _draw_bar(panel, label_font, value_font, y, label, value, max_value, bar_color):
    label_surf = label_font.render(label, True, WHITE)
    panel.blit(label_surf, (18, y))
    y += label_surf.get_height() + 4
    bar_rect = pygame.Rect(18, y, HUD_PANEL_WIDTH - 36, 22)
    pygame.draw.rect(panel, (20, 24, 34), bar_rect, border_radius=10)
    inner = bar_rect.inflate(-4, -4)
    ratio = 0.0
    if max_value:
        ratio = max(0.0, min(1.0, float(value) / float(max_value)))
    fill = inner.copy()
    fill.width = int(inner.width * ratio)
    pygame.draw.rect(panel, bar_color, fill, border_radius=8)
    pygame.draw.rect(panel, (12, 16, 24), inner, width=2, border_radius=8)
    text = value_font.render(f"{int(value)}/{int(max_value)}", True, WHITE)
    panel.blit(text, (inner.x + 6, inner.y + 2))
    return y + bar_rect.height + 10


def draw_hud(surface, player, planner_status=None, task_log=None, scroll_offset=0.0):
    font = pygame.font.SysFont("arial", 20, bold=True)
    small = pygame.font.SysFont("arial", 16)
    tiny = pygame.font.SysFont("arial", 14)

    panel_w = HUD_PANEL_WIDTH
    panel_h = surface.get_height()
    panel = pygame.Surface((panel_w, panel_h))
    panel.fill((14, 20, 32))

    content_h = panel_h
    content = pygame.Surface((panel_w, 2000), pygame.SRCALPHA)

    y = 18
    title = font.render("Panel de Misión", True, WHITE)
    content.blit(title, (18, y))
    y += title.get_height() + 10

    y = _draw_bar(content, small, tiny, y, "Salud", getattr(player, "hp", 0), getattr(player, "max_hp", 0), GREEN)
    y = _draw_bar(content, small, tiny, y, "Calificaciones", getattr(player, "grades", 0), 100, BLUE)
    y = _draw_bar(content, small, tiny, y, "Vida social", getattr(player, "social_health", 0), 100, PURPLE)
    y = _draw_bar(content, small, tiny, y, "Hambre", getattr(player, "hunger", 0), 100, ORANGE)

    social_state = getattr(player, "mood", "Neutral")
    room = getattr(player, "current_room", None)
    info_lines = [f"Ánimo social: {social_state}"]
    if room:
        info_lines.append(f"Salón actual: {room}")
    info_lines.append(f"Inventario: {len(getattr(player, 'inventory', []))}")
    for line in info_lines:
        text = small.render(line, True, WHITE)
        content.blit(text, (18, y))
        y += text.get_height() + 4

    alerts = list(getattr(player, "alerts", []))
    if alerts:
        y += 6
        for alert in alerts[:3]:
            alert_text = tiny.render(f"⚠ {alert}", True, RED)
            content.blit(alert_text, (18, y))
            y += alert_text.get_height() + 2

    relationships_fn = getattr(player, "top_relationships", None)
    rels = relationships_fn() if callable(relationships_fn) else []
    if rels:
        y += 6
        rel_title = small.render("Relaciones", True, WHITE)
        content.blit(rel_title, (18, y))
        y += rel_title.get_height() + 2
        for name, value in rels:
            rel_text = tiny.render(f"{name}: {int(value)}", True, WHITE)
            content.blit(rel_text, (28, y))
            y += rel_text.get_height() + 2

    log = list(getattr(player, "interaction_log", []))
    if log:
        y += 8
        log_title = small.render("Interacciones", True, WHITE)
        content.blit(log_title, (18, y))
        y += log_title.get_height() + 2
        for entry in log[-12:]:
            entry_surf = tiny.render(entry, True, WHITE)
            content.blit(entry_surf, (28, y))
            y += entry_surf.get_height() + 2

    feed = list(getattr(player, "social_feed", []))
    if feed:
        y += 8
        feed_title = small.render("Red social", True, WHITE)
        content.blit(feed_title, (18, y))
        y += feed_title.get_height() + 2
        for entry in feed[:6]:
            entry_surf = tiny.render(entry, True, WHITE)
            content.blit(entry_surf, (24, y))
            y += entry_surf.get_height() + 2

    tasks = task_log or []
    if tasks:
        y += 10
        tasks_title = small.render("Tus decisiones", True, WHITE)
        content.blit(tasks_title, (18, y))
        y += tasks_title.get_height() + 4
        for task in tasks[-6:]:
            label = task["name"]
            room_label = task.get("room")
            if room_label:
                label = f"{label} @ {room_label}"
            desc = tiny.render(label, True, WHITE)
            content.blit(desc, (24, y))
            y += desc.get_height() + 1
            status = tiny.render(task.get("status", ""), True, WHITE)
            content.blit(status, (30, y))
            y += status.get_height() + 4

    content_h = max(y + 24, panel_h)
    if content.get_height() < content_h:
        expanded = pygame.Surface((panel_w, content_h), pygame.SRCALPHA)
        expanded.blit(content, (0, 0))
        content = expanded
    else:
        content = content.subsurface((0, 0, panel_w, content_h)).copy()

    max_scroll = max(0, content_h - panel_h)
    offset = int(max(0, min(max_scroll, scroll_offset)))
    panel.blit(content, (0, -offset))

    if max_scroll > 0:
        track = pygame.Rect(panel_w - 14, 16, 8, panel_h - 32)
        pygame.draw.rect(panel, (28, 36, 52), track, border_radius=4)
        thumb_h = max(24, int(track.height * (panel_h / content_h)))
        thumb_range = track.height - thumb_h
        thumb_y = track.y + int((offset / max_scroll) * thumb_range) if max_scroll else track.y
        thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
        pygame.draw.rect(panel, (120, 170, 220), thumb, border_radius=4)

    surface.blit(panel, (0, 0))
    return max_scroll


def draw_action_feed(surface, rect, prompts, history, controls_hint=None):
    if rect.width <= 0 or rect.height <= 0:
        return
    feed_surface = pygame.Surface((rect.width, rect.height))
    feed_surface.fill((16, 20, 30))

    title_font = pygame.font.SysFont("arial", 18, bold=True)
    small = pygame.font.SysFont("arial", 16)
    tiny = pygame.font.SysFont("arial", 14)

    y = 12
    header = title_font.render("Eventos en curso", True, WHITE)
    feed_surface.blit(header, (16, y))
    y += header.get_height() + 6

    active_prompts = [p for p in (prompts or [])]
    if active_prompts:
        for prompt in active_prompts[:3]:
            text = prompt.get("text") or "Acción disponible"
            prompt_label = small.render(text, True, WHITE)
            feed_surface.blit(prompt_label, (16, y))
            timer = prompt.get("timer")
            if timer is not None:
                timer_text = tiny.render(f"{max(0, int(timer + 0.9))}s", True, (170, 190, 220))
                feed_surface.blit(timer_text, (rect.width - timer_text.get_width() - 16, y))
            y += prompt_label.get_height() + 2
            for option in prompt.get("options", []):
                key_display = option.get("display") or option.get("key")
                if isinstance(key_display, int):
                    key_display = pygame.key.name(key_display).upper()
                label = option.get("label", "Selecciona")
                option_text = tiny.render(f"[{key_display}] {label}", True, (200, 220, 255))
                feed_surface.blit(option_text, (28, y))
                y += option_text.get_height() + 1
            y += 4
    else:
        empty = small.render("No hay acciones pendientes. Busca compañeros para interactuar.", True, (190, 200, 210))
        feed_surface.blit(empty, (16, y))
        y += empty.get_height() + 8

    y = max(y + 4, rect.height // 2 - 10)
    history_title = small.render("Historial reciente", True, WHITE)
    feed_surface.blit(history_title, (16, y))
    y += history_title.get_height() + 4
    for entry in (history or [])[:6]:
        text = entry.get("text", "")
        color = entry.get("color") or (220, 220, 230)
        entry_surf = tiny.render(text, True, color)
        feed_surface.blit(entry_surf, (24, y))
        y += entry_surf.get_height() + 2
        if y > rect.height - 36:
            break

    if controls_hint:
        hint = tiny.render(controls_hint, True, (170, 180, 200))
        feed_surface.blit(hint, (16, rect.height - hint.get_height() - 10))

    pygame.draw.rect(feed_surface, (10, 12, 18), feed_surface.get_rect(), width=2, border_radius=12)
    surface.blit(feed_surface, rect.topleft)


class DecisionPrompt:
    def __init__(self, title, question, options, font=None, small=None):
        self.title = title
        self.question = question
        self.options = list(options)
        self.index = 0
        self.finished = False
        self.selection = None
        self.font = font or pygame.font.SysFont("arial", 24, bold=True)
        self.small = small or pygame.font.SysFont("arial", 18)

    def handle_event(self, event):
        if self.finished:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self.selection = self.options[self.index]
                self.finished = True
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.selection = None
                self.finished = True

    def draw(self, surface):
        panel_w = int(surface.get_width() * 0.42)
        panel_h = 260
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((16, 20, 32, 240))
        pygame.draw.rect(panel, (70, 90, 140), panel.get_rect(), width=2, border_radius=16)

        y = 24
        title = self.font.render(self.title, True, WHITE)
        panel.blit(title, (24, y))
        y += title.get_height() + 6
        question = self.small.render(self.question, True, WHITE)
        panel.blit(question, (24, y))
        y += question.get_height() + 14

        for idx, option in enumerate(self.options):
            selected = idx == self.index
            color = (240, 220, 120) if selected else WHITE
            marker = "▶ " if selected else "  "
            text = self.small.render(marker + option, True, color)
            panel.blit(text, (32, y))
            y += text.get_height() + 8

        hint = self.small.render("ENTER para confirmar • ESC para cancelar", True, WHITE)
        panel.blit(hint, (24, panel_h - hint.get_height() - 18))

        x = max(40, int(surface.get_width() * 0.08))
        y = int(surface.get_height() * 0.18)
        surface.blit(panel, (x, y))
