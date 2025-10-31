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


def draw_interaction_bubble(surface, pos, text, font=None, accent=(120, 180, 255)):
    if not text:
        return
    if font is None:
        font = pygame.font.SysFont("arial", 16, bold=True)
    text_surf = font.render(text, True, (16, 22, 32))
    padding_x, padding_y = 14, 10
    body_w = text_surf.get_width() + padding_x * 2
    body_h = text_surf.get_height() + padding_y * 2
    tail_h = 12
    bubble = pygame.Surface((body_w, body_h + tail_h), pygame.SRCALPHA)
    pygame.draw.rect(
        bubble,
        (245, 248, 255, 235),
        pygame.Rect(0, 0, body_w, body_h),
        border_radius=16,
    )
    pygame.draw.rect(
        bubble,
        (*accent, 255),
        pygame.Rect(0, 0, body_w, body_h),
        width=2,
        border_radius=16,
    )
    tail_points = [
        (body_w // 2 - 12, body_h - 1),
        (body_w // 2 + 12, body_h - 1),
        (body_w // 2, body_h + tail_h),
    ]
    pygame.draw.polygon(bubble, (245, 248, 255, 235), tail_points)
    pygame.draw.lines(bubble, (*accent, 255), False, tail_points, 2)
    shadow = pygame.Surface(bubble.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(
        shadow,
        (0, 0, 0, 90),
        pygame.Rect(4, 6, body_w, body_h),
        border_radius=16,
    )
    pygame.draw.polygon(
        shadow,
        (0, 0, 0, 90),
        [(p[0] + 4, p[1] + 6) for p in tail_points],
    )
    surface.blit(shadow, (pos[0] - bubble.get_width() // 2 + 2, pos[1] - bubble.get_height() - 2))
    surface.blit(bubble, (pos[0] - bubble.get_width() // 2, pos[1] - bubble.get_height()))
    bubble.blit(text_surf, (padding_x, padding_y - 2))

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


def _wrap_text_segments(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = str(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if font.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _blit_wrapped(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color,
    x: int,
    y: int,
    max_width: int,
    line_gap: int = 2,
) -> int:
    segments = _wrap_text_segments(text, font, max_width)
    if not segments:
        return y
    offset = y
    for idx, segment in enumerate(segments):
        surf = font.render(segment, True, color)
        surface.blit(surf, (x, offset))
        offset += surf.get_height()
        if idx < len(segments) - 1:
            offset += line_gap
    return offset


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
        y = _blit_wrapped(content, small, line, WHITE, 18, y, panel_w - 36) + 4

    alerts = list(getattr(player, "alerts", []))
    if alerts:
        y += 6
        for alert in alerts[:3]:
            y = _blit_wrapped(content, tiny, f"⚠ {alert}", RED, 18, y, panel_w - 36) + 2

    relationships_fn = getattr(player, "top_relationships", None)
    rels = relationships_fn() if callable(relationships_fn) else []
    if rels:
        y += 6
        rel_title = small.render("Relaciones", True, WHITE)
        content.blit(rel_title, (18, y))
        y += rel_title.get_height() + 2
        for name, value in rels:
            y = _blit_wrapped(content, tiny, f"{name}: {int(value)}", WHITE, 28, y, panel_w - 46) + 2

    log = list(getattr(player, "interaction_log", []))
    if log:
        y += 8
        log_title = small.render("Interacciones", True, WHITE)
        content.blit(log_title, (18, y))
        y += log_title.get_height() + 2
        for entry in log[-12:]:
            y = _blit_wrapped(content, tiny, entry, WHITE, 28, y, panel_w - 46) + 2

    feed = list(getattr(player, "social_feed", []))
    if feed:
        y += 8
        feed_title = small.render("Red social", True, WHITE)
        content.blit(feed_title, (18, y))
        y += feed_title.get_height() + 2
        for entry in feed[:6]:
            y = _blit_wrapped(content, tiny, entry, WHITE, 24, y, panel_w - 44) + 2

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
            y = _blit_wrapped(content, tiny, label, WHITE, 24, y, panel_w - 44) + 1
            status_text = str(task.get("status", ""))
            if status_text:
                y = _blit_wrapped(content, tiny, status_text, WHITE, 30, y, panel_w - 48) + 4
            else:
                y += 4

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
            label_top = y
            for line in _wrap_text_segments(text, small, rect.width - 32):
                prompt_label = small.render(line, True, WHITE)
                feed_surface.blit(prompt_label, (16, y))
                y += prompt_label.get_height() + 2
            timer = prompt.get("timer")
            duration = prompt.get("duration")
            if timer is not None:
                timer_text = tiny.render(f"{max(0, int(timer + 0.9))}s", True, (170, 190, 220))
                feed_surface.blit(timer_text, (rect.width - timer_text.get_width() - 16, label_top))
            detail = prompt.get("detail")
            if detail:
                for line in _wrap_text_segments(detail, tiny, rect.width - 48):
                    detail_surf = tiny.render(line, True, (190, 210, 235))
                    feed_surface.blit(detail_surf, (28, y))
                    y += detail_surf.get_height() + 2
            if timer is not None and duration:
                progress = 0.0 if duration <= 0 else max(0.0, min(1.0, float(duration - timer) / float(duration)))
                bar_rect = pygame.Rect(28, y, rect.width - 56, 6)
                pygame.draw.rect(feed_surface, (28, 32, 44), bar_rect, border_radius=3)
                fill = bar_rect.inflate(-2, -2)
                fill.width = int(fill.width * progress)
                pygame.draw.rect(feed_surface, (110, 170, 255), fill, border_radius=3)
                y += bar_rect.height + 4
            for option in prompt.get("options", []):
                key_display = option.get("display") or option.get("key")
                if isinstance(key_display, int):
                    key_display = pygame.key.name(key_display).upper()
                label = option.get("label", "Selecciona")
                option_label = f"[{key_display}] {label}"
                for line in _wrap_text_segments(option_label, tiny, rect.width - 56):
                    option_text = tiny.render(line, True, (200, 220, 255))
                    feed_surface.blit(option_text, (28, y))
                    y += option_text.get_height() + 1
            y += 6
    else:
        empty_text = "No hay acciones pendientes. Busca compañeros para interactuar."
        for line in _wrap_text_segments(empty_text, small, rect.width - 32):
            empty = small.render(line, True, (190, 200, 210))
            feed_surface.blit(empty, (16, y))
            y += empty.get_height() + 4
        y += 4

    y = max(y + 4, rect.height // 2 - 10)
    history_title = small.render("Historial reciente", True, WHITE)
    feed_surface.blit(history_title, (16, y))
    y += history_title.get_height() + 4
    for entry in (history or [])[:6]:
        text = entry.get("text", "")
        color = entry.get("color") or (220, 220, 230)
        for line in _wrap_text_segments(text, tiny, rect.width - 48):
            entry_surf = tiny.render(line, True, color)
            feed_surface.blit(entry_surf, (24, y))
            y += entry_surf.get_height() + 2
        if y > rect.height - 36:
            break

    if controls_hint:
        hint_lines = _wrap_text_segments(controls_hint, tiny, rect.width - 32)
        offset_y = rect.height - 10
        for line in reversed(hint_lines):
            hint = tiny.render(line, True, (170, 180, 200))
            offset_y -= hint.get_height()
            feed_surface.blit(hint, (16, offset_y))

    pygame.draw.rect(feed_surface, (10, 12, 18), feed_surface.get_rect(), width=2, border_radius=12)
    surface.blit(feed_surface, rect.topleft)


def _wrap_lines(text, font, max_width):
    return _wrap_text_segments(text, font, max_width)


def draw_action_popup(surface, prompts, anchor_rect=None):
    if not prompts:
        return
    prompt = prompts[0]
    width = min(520, surface.get_width() - 80)
    height = 168
    popup = pygame.Surface((width, height), pygame.SRCALPHA)

    bg_rect = popup.get_rect()
    shadow = pygame.Surface((width + 12, height + 12), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 140), shadow.get_rect(), border_radius=28)
    pygame.draw.rect(popup, (26, 34, 52, 235), bg_rect, border_radius=24)
    pygame.draw.rect(popup, (90, 160, 255, 255), bg_rect, width=2, border_radius=24)

    title_font = pygame.font.SysFont("arial", 20, bold=True)
    body_font = pygame.font.SysFont("arial", 18)
    small_font = pygame.font.SysFont("arial", 16)

    title = prompt.get("text") or "Nueva acción"
    lines = _wrap_lines(title, title_font, width - 48)
    y = 18
    for line in lines:
        surf = title_font.render(line, True, WHITE)
        popup.blit(surf, (24, y))
        y += surf.get_height() + 2

    detail = prompt.get("detail")
    if detail:
        for line in _wrap_lines(detail, body_font, width - 48):
            surf = body_font.render(line, True, (210, 220, 240))
            popup.blit(surf, (24, y))
            y += surf.get_height() + 2
        y += 2

    timer = prompt.get("timer")
    duration = prompt.get("duration")
    if timer is not None and duration:
        remaining = max(0.0, float(timer))
        progress = max(0.0, min(1.0, (duration - remaining) / max(0.1, duration)))
        track = pygame.Rect(24, y + 6, width - 48, 10)
        pygame.draw.rect(popup, (34, 42, 60), track, border_radius=6)
        fill = track.inflate(-2, -2)
        fill.width = int(fill.width * progress)
        pygame.draw.rect(popup, (110, 180, 255), fill, border_radius=6)
        timer_text = small_font.render(f"{int(remaining + 0.9)} s restantes", True, (200, 220, 255))
        popup.blit(timer_text, (24, track.bottom + 6))
        y = track.bottom + 10 + timer_text.get_height()
    else:
        y += 4

    option_y = max(y, height - 70)
    for option in prompt.get("options", []):
        key_display = option.get("display") or option.get("key")
        if isinstance(key_display, int):
            key_display = pygame.key.name(key_display).upper()
        label = option.get("label", "Selecciona")
        key_surf = small_font.render(str(key_display), True, WHITE)
        label_surf = small_font.render(label, True, (210, 220, 240))
        badge_width = max(140, key_surf.get_width() + label_surf.get_width() + 36)
        badge = pygame.Surface((badge_width, 32), pygame.SRCALPHA)
        pygame.draw.rect(badge, (42, 60, 96, 220), badge.get_rect(), border_radius=16)
        pygame.draw.rect(badge, (120, 180, 255, 255), badge.get_rect(), width=2, border_radius=16)
        badge.blit(key_surf, (12, (badge.get_height() - key_surf.get_height()) // 2))
        badge.blit(label_surf, (badge.get_width() - label_surf.get_width() - 14, (badge.get_height() - label_surf.get_height()) // 2))
        popup.blit(badge, (24, option_y))
        option_y += badge.get_height() + 8

    if anchor_rect:
        pos_x = anchor_rect.centerx - popup.get_width() // 2
        pos_y = anchor_rect.top - popup.get_height() - 18
    else:
        pos_x = (surface.get_width() - popup.get_width()) // 2
        pos_y = surface.get_height() - popup.get_height() - 28
    pos_y = max(20, pos_y)

    surface.blit(shadow, (pos_x - 6, pos_y + 6))
    surface.blit(popup, (pos_x, pos_y))


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
        panel_w = max(420, int(surface.get_width() * 0.38))
        panel_h = 320
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

        body_rect = panel.get_rect()
        pygame.draw.rect(panel, (18, 24, 38, 235), body_rect, border_radius=26)

        header_rect = pygame.Rect(0, 0, panel_w, 84)
        pygame.draw.rect(
            panel,
            (46, 68, 118, 255),
            header_rect,
            border_top_left_radius=26,
            border_top_right_radius=26,
        )
        pygame.draw.line(panel, (86, 120, 180), (0, header_rect.bottom), (panel_w, header_rect.bottom), 2)
        title = self.font.render(self.title, True, WHITE)
        panel.blit(title, (32, 18))
        question = self.small.render(self.question, True, (220, 230, 240))
        panel.blit(question, (32, 48))

        list_top = header_rect.bottom + 16
        option_width = panel_w - 64
        for idx, option in enumerate(self.options):
            selected = idx == self.index
            option_rect = pygame.Rect(32, list_top + idx * 50, option_width, 46)
            base_color = (32, 40, 58)
            highlight = (70, 96, 148)
            pygame.draw.rect(
                panel,
                highlight if selected else base_color,
                option_rect,
                border_radius=14,
            )
            pygame.draw.rect(panel, (68, 92, 140), option_rect, width=2, border_radius=14)
            label = self.small.render(self.options[idx], True, WHITE if selected else (215, 225, 240))
            marker = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.circle(marker, (240, 220, 140) if selected else (110, 140, 190), (14, 14), 14)
            marker_text = self.small.render(str(idx + 1), True, (20, 26, 32))
            marker.blit(marker_text, marker_text.get_rect(center=(14, 14)))
            panel.blit(marker, (option_rect.x + 12, option_rect.y + 9))
            panel.blit(label, (option_rect.x + 48, option_rect.y + 10))

        footer_text = "ENTER para confirmar  •  ESC para cancelar  •  Usa ↑/↓ o números"
        hint = self.small.render(footer_text, True, (210, 220, 235))
        panel.blit(hint, (32, panel_h - hint.get_height() - 24))
        pygame.draw.rect(panel, (92, 124, 182), body_rect, width=2, border_radius=26)

        x = max(40, int(surface.get_width() * 0.06))
        y = int(surface.get_height() * 0.16)
        surface.blit(panel, (x, y))


class ChatWindow:
    def __init__(self, title, participant, question, options, font=None, small=None):
        self.title = title
        self.participant = participant
        self.question = question
        self.font = font or pygame.font.SysFont("arial", 20, bold=True)
        self.small = small or pygame.font.SysFont("arial", 16)
        self.body = pygame.font.SysFont("arial", 15)
        self.history: list[dict[str, object]] = []
        self.summary_lines: list[str] = []
        self.closed = False
        self.cancelled = False
        self.mode = "options"
        self.index = 0
        self.options = []
        self.set_options(options)

    def set_options(self, options):
        mapped = []
        for idx, opt in enumerate(options or []):
            if isinstance(opt, str):
                mapped.append({"label": opt, "value": opt})
            else:
                mapped.append({
                    "label": opt.get("label") or opt.get("value") or f"Opción {idx + 1}",
                    "value": opt.get("value") or opt.get("label") or opt,
                })
        self.options = mapped
        self.mode = "options" if self.options else "summary"
        self.index = 0

    def add_message(self, author: str, text: str, outbound: bool = False):
        if not text:
            return
        entry = {"author": author, "text": text, "outbound": outbound}
        self.history.append(entry)
        if len(self.history) > 12:
            self.history = self.history[-12:]

    def show_outcome(self, summary_lines: list[str]):
        self.summary_lines = summary_lines or []
        self.mode = "summary"

    def is_closed(self) -> bool:
        return self.closed

    def handle_event(self, event):
        if self.closed:
            return None
        if self.mode == "options":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.index = (self.index - 1) % len(self.options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.index = (self.index + 1) % len(self.options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    return self.options[self.index]["value"]
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    choice = event.key - pygame.K_1
                    if 0 <= choice < len(self.options):
                        self.index = choice
                        return self.options[self.index]["value"]
                elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self.cancelled = True
                    self.closed = True
                    return "__cancel__"
        elif self.mode == "summary":
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_SPACE,
                pygame.K_ESCAPE,
            ):
                self.closed = True
                return "__closed__"
        return None

    def draw(self, surface):
        panel_w = max(360, int(surface.get_width() * 0.3))
        panel_h = max(420, int(surface.get_height() * 0.68))
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        rect = panel.get_rect()
        pygame.draw.rect(panel, (14, 20, 32, 235), rect, border_radius=26)
        header_rect = pygame.Rect(0, 0, panel_w, 86)
        pygame.draw.rect(
            panel,
            (40, 68, 118, 250),
            header_rect,
            border_top_left_radius=26,
            border_top_right_radius=26,
        )
        title = self.font.render(self.title, True, WHITE)
        panel.blit(title, (26, 16))
        participant_label = self.small.render(f"Chat con {self.participant}", True, (220, 230, 245))
        panel.blit(participant_label, (26, 48))

        question_rect = pygame.Rect(24, header_rect.bottom + 10, panel_w - 48, 60)
        pygame.draw.rect(panel, (26, 34, 52), question_rect, border_radius=14)
        pygame.draw.rect(panel, (62, 88, 140), question_rect, width=2, border_radius=14)
        question = self.small.render(self.question, True, (210, 220, 235))
        panel.blit(question, (question_rect.x + 12, question_rect.y + 16))

        history_top = question_rect.bottom + 12
        history_height = panel_h - history_top - 140
        history_rect = pygame.Rect(24, history_top, panel_w - 48, history_height)
        pygame.draw.rect(panel, (18, 26, 42), history_rect, border_radius=14)
        pygame.draw.rect(panel, (50, 70, 110), history_rect, width=2, border_radius=14)

        y = history_rect.bottom - 16
        for entry in reversed(self.history):
            text = str(entry.get("text", ""))
            author = entry.get("author", "")
            outbound = entry.get("outbound", False)
            lines = [self.body.render(author, True, (210, 220, 235))]
            wrap = self._wrap_text(text, history_rect.width - 36)
            lines.extend(self.body.render(line, True, (230, 234, 242)) for line in wrap)
            block_height = sum(line.get_height() for line in lines) + 16
            bubble = pygame.Surface((history_rect.width - 12, block_height), pygame.SRCALPHA)
            bubble_rect = bubble.get_rect()
            bubble_rect.y = y - block_height
            bg_color = (70, 108, 170, 240) if outbound else (44, 62, 92, 220)
            pygame.draw.rect(bubble, bg_color, (0, 0, bubble_rect.width, bubble_rect.height), border_radius=14)
            offset_y = 10
            for surf_line in lines:
                bubble.blit(surf_line, (14, offset_y))
                offset_y += surf_line.get_height()
            offset_x = history_rect.x + 6
            if outbound:
                offset_x = history_rect.right - bubble_rect.width - 6
            panel.blit(bubble, (offset_x, bubble_rect.y))
            y -= block_height + 10
            if y <= history_rect.y + 24:
                break

        footer_top = history_rect.bottom + 18
        if self.mode == "options":
            for idx, option in enumerate(self.options):
                option_rect = pygame.Rect(32, footer_top + idx * 54, panel_w - 64, 48)
                is_selected = idx == self.index
                pygame.draw.rect(
                    panel,
                    (70, 100, 158) if is_selected else (28, 40, 62),
                    option_rect,
                    border_radius=14,
                )
                pygame.draw.rect(panel, (68, 92, 140), option_rect, width=2, border_radius=14)
                bullet = pygame.Surface((28, 28), pygame.SRCALPHA)
                pygame.draw.circle(
                    bullet,
                    (240, 220, 140) if is_selected else (110, 140, 190),
                    (14, 14),
                    14,
                )
                num = self.small.render(str(idx + 1), True, (20, 26, 32))
                bullet.blit(num, num.get_rect(center=(14, 14)))
                label = self.small.render(str(option["label"]), True, WHITE if is_selected else (210, 220, 235))
                panel.blit(bullet, (option_rect.x + 12, option_rect.y + 10))
                panel.blit(label, (option_rect.x + 50, option_rect.y + 12))
            hint_text = "↑/↓ o números para elegir  •  ENTER para enviar  •  ESC para cerrar"
        else:
            summary_y = footer_top
            for line in self.summary_lines:
                surf_line = self.small.render(line, True, (215, 225, 240))
                panel.blit(surf_line, (32, summary_y))
                summary_y += surf_line.get_height() + 6
            hint_text = "ENTER para continuar"

        hint = self.small.render(hint_text, True, (210, 220, 235))
        panel.blit(hint, (32, panel_h - hint.get_height() - 22))
        pygame.draw.rect(panel, (82, 112, 170), rect, width=2, border_radius=26)

        x = surface.get_width() - panel_w - 32
        y = int(surface.get_height() * 0.14)
        surface.blit(panel, (x, y))

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if self.body.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
