# game/entities.py
import random
from collections import deque
from typing import Callable, Iterable, Optional, Tuple

import pygame

from settings import (
    TILE,
    PLAYER_SPEED,
    ENEMY_SPEED,
    RED,
    GREEN,
    YELLOW,
    BLUE,
    PURPLE,
    ORANGE,
)


def move_with_collision(rect, vel, tilemap, dt):
    """Desplaza un rectángulo manejando colisiones con el tilemap."""
    rect.x += vel.x * dt
    if tilemap.rect_collide(rect):
        step = 1 if vel.x > 0 else -1
        while tilemap.rect_collide(rect):
            rect.x -= step
    rect.y += vel.y * dt
    if tilemap.rect_collide(rect):
        step = 1 if vel.y > 0 else -1
        while tilemap.rect_collide(rect):
            rect.y -= step
    return rect


class Entity:
    def __init__(self, x, y, w, h, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.vx = 0.0
        self.vy = 0.0
        self.dead = False
        self._dir = "down"
        self._anim_t = 0.0
        self._anim_on = False

    def set_dir(self, d):
        self._dir = d

    def tick_anim(self, dt, moving):
        self._anim_on = bool(moving)
        self._anim_t = (self._anim_t + dt) if moving else 0.0

    def update(self, dt, tilemap):
        pass

    def draw(self, surf, camera):
        pygame.draw.rect(surf, self.color, camera.apply(self.rect))


class Character(Entity):
    """Extiende Entity con datos de clase, compatibilidad y acciones asignadas."""

    NAME_FONT: Optional[pygame.font.Font] = None

    def __init__(
        self,
        x: int,
        y: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
        name: str = "Personaje",
        color=YELLOW,
        importance: int = 1,
        speed: float = PLAYER_SPEED,
        max_hp: int = 100,
        compatibility: Optional[Iterable[str]] = None,
        aptitudes: Optional[Iterable[str]] = None,
        virtual_only: bool = False,
    ):
        w = width if width is not None else (TILE - 6)
        h = height if height is not None else (TILE - 6)
        super().__init__(x, y, w, h, color)
        self.name = name
        self.speed = float(speed)
        self.max_hp = max(1, int(max_hp))
        self.hp = float(self.max_hp)
        self.importance = float(importance)
        self.compatibility = set(compatibility or [])
        self.aptitudes = set(aptitudes or [])
        self.inventory: list[str] = []
        self.current_action = None
        self.action_timer = 0.0
        self.action_duration = 0.0
        self.action_target: Optional[pygame.Vector2] = None
        self.virtual_only = virtual_only
        self.visible = not virtual_only
        self.feedback_timer = 0.0
        self.action_feedback = ""
        self.current_room: Optional[str] = None
        self.availability = 1.0
        self.approach_target: Optional[pygame.Vector2] = None
        self.approach_timer: float = 0.0
        self._approach_target_source: Optional[Callable[[], Tuple[float, float]]] = None

    @classmethod
    def _name_font(cls):
        if cls.NAME_FONT is None and pygame.font.get_init():
            cls.NAME_FONT = pygame.font.SysFont("arial", 14, bold=True)
        return cls.NAME_FONT

    def can_perform(self, action) -> bool:
        required = getattr(action, "required_aptitudes", set())
        compat = getattr(action, "compatibility", set())
        if required and not (self.aptitudes & required):
            return False
        if compat and not (self.compatibility & compat):
            return False
        return True

    def assign_action(self, action, target=None):
        self.current_action = action
        self.action_timer = 0.0
        self.action_duration = max(0.1, float(getattr(action, "duration", 0.1)))
        self.action_target = pygame.Vector2(target) if (target and not self.virtual_only) else None
        self.availability = 0.0

    def clear_action(self):
        self.current_action = None
        self.action_timer = 0.0
        self.action_duration = 0.0
        self.action_target = None
        self.availability = 1.0

    def action_progress(self) -> float:
        if not self.current_action or self.action_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, self.action_timer / self.action_duration))

    def boost_action(self, feedback: str):
        self.action_feedback = feedback
        self.feedback_timer = 2.0
        self.hp = min(self.max_hp, self.hp + 1.5)

    def request_interaction(self, target, duration: float = 3.5) -> None:
        if callable(target):
            self._approach_target_source = target
            try:
                pos = target()
            except Exception:
                pos = None
        else:
            self._approach_target_source = None
            pos = target
        if pos is None:
            return
        self.approach_target = pygame.Vector2(pos)
        self.approach_timer = max(duration, 0.2)

    def clear_interaction_request(self) -> None:
        self.approach_timer = 0.0
        self.approach_target = None
        self._approach_target_source = None

    def _approach_step(self, dt: float, tilemap) -> Tuple[bool, bool]:
        if self.approach_timer <= 0.0 or self.virtual_only:
            self.approach_target = None
            self._approach_target_source = None
            return False, False
        self.approach_timer = max(0.0, self.approach_timer - dt)
        if self._approach_target_source:
            try:
                pos = self._approach_target_source()
            except Exception:
                pos = None
            if pos is not None:
                self.approach_target = pygame.Vector2(pos)
        if not self.approach_target:
            return True, False
        center = pygame.Vector2(self.rect.center)
        delta = self.approach_target - center
        if delta.length_squared() <= 16:
            return True, False
        vel = delta.normalize() * max(60.0, self.speed * 0.55)
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        if abs(vel.x) > abs(vel.y):
            self.set_dir("right" if vel.x > 0 else "left")
        elif abs(vel.y) > 0:
            self.set_dir("down" if vel.y > 0 else "up")
        return True, True

    def _tick_feedback(self, dt: float):
        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)
            if self.feedback_timer <= 0:
                self.action_feedback = ""

    def set_room(self, room_name: Optional[str]):
        self.current_room = room_name

    def update_action(self, dt: float, tilemap):
        if not self.current_action:
            self.tick_anim(dt, False)
            self._tick_feedback(dt)
            return

        engaged, moved = self._approach_step(dt, tilemap)
        moving = moved
        if not engaged and not self.virtual_only and self.action_target:
            center = pygame.Vector2(self.rect.center)
            delta = self.action_target - center
            if delta.length_squared() > 9:
                vel = delta.normalize() * self.speed
                self.rect = move_with_collision(self.rect, vel, tilemap, dt)
                moving = True
        self.tick_anim(dt, moving)
        self.action_timer += dt * (0.5 if engaged and not moved else 1.0)
        self._tick_feedback(dt)

    def idle_step(self, dt: float, tilemap):
        engaged, moved = self._approach_step(dt, tilemap)
        self.tick_anim(dt, moved)
        self._tick_feedback(dt)

    def status_text(self) -> str:
        if self.current_action:
            action = self.current_action
            progress = int(self.action_progress() * 100)
            return f"{action.category} {progress}%"
        return "Disponible"

    def draw(self, surf, camera):
        if not self.visible:
            return
        super().draw(surf, camera)
        view_rect = camera.apply(self.rect)
        bar_bg = pygame.Rect(view_rect.x, view_rect.y - 8, view_rect.w, 5)
        pygame.draw.rect(surf, (60, 10, 10), bar_bg)
        fill = bar_bg.copy()
        fill.width = int(bar_bg.width * max(0.0, min(1.0, self.hp / self.max_hp)))
        pygame.draw.rect(surf, (60, 200, 120), fill)

        font = self._name_font()
        if font:
            name_surf = font.render(self.name, True, (245, 245, 245))
            name_rect = name_surf.get_rect(midbottom=(view_rect.centerx, bar_bg.y - 2))
            surf.blit(name_surf, name_rect)
            status = self.status_text()
            status_surf = font.render(status, True, (200, 220, 235))
            status_rect = status_surf.get_rect(midtop=(view_rect.centerx, view_rect.bottom + 2))
            surf.blit(status_surf, status_rect)
            if self.action_feedback:
                fb_surf = font.render(self.action_feedback, True, (255, 240, 140))
                fb_rect = fb_surf.get_rect(midtop=(view_rect.centerx, status_rect.bottom + 2))
                surf.blit(fb_surf, fb_rect)


class Player(Character):
    def __init__(self, x, y):
        super().__init__(
            x,
            y,
            width=TILE - 6,
            height=TILE - 4,
            name="Jugador",
            color=YELLOW,
            importance=6,
            speed=PLAYER_SPEED,
            max_hp=120,
            compatibility=["lider", "academia", "colaboracion"],
            aptitudes=["Apoyo académico", "Tutoría intensiva", "Logística escolar", "Plan de seguridad"],
        )
        self.inventory = []
        self.interact_cooldown = 0.0
        self.relationships: dict[str, float] = {}
        self.interaction_log: deque[str] = deque(maxlen=6)
        self.mood = "Neutral"
        self.grades = 100.0
        self.social_health = 100.0
        self.hunger = 100.0
        self.alerts: deque[str] = deque(maxlen=6)
        self._last_alert: Optional[str] = None
        self.pending_greeting: Optional[str] = None
        self.idle_time = 0.0

    def handle_input(self, keys):
        self.vx = (keys.get("right", False) - keys.get("left", False)) * self.speed
        self.vy = (keys.get("down", False) - keys.get("up", False)) * self.speed
        if abs(self.vx) > abs(self.vy):
            if self.vx > 0:
                self.set_dir("right")
            elif self.vx < 0:
                self.set_dir("left")
        elif abs(self.vy) > 0:
            if self.vy > 0:
                self.set_dir("down")
            elif self.vy < 0:
                self.set_dir("up")

    def update(self, dt, tilemap):
        if self.interact_cooldown > 0:
            self.interact_cooldown -= dt
        vel = pygame.Vector2(self.vx, self.vy)
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)
        if vel.length_squared() > 1.0:
            self.idle_time = 0.0
        else:
            self.idle_time += dt
        self._update_needs(dt)

    def adjust_relationship(self, name: str, delta: float) -> None:
        base = self.relationships.get(name, 50.0)
        base = max(0.0, min(100.0, base + delta))
        self.relationships[name] = base
        self._update_mood()

    def note_interaction(self, text: str) -> None:
        if not text:
            return
        self.interaction_log.appendleft(text)

    def push_alert(self, text: str) -> None:
        if not text:
            return
        if text == self._last_alert:
            return
        self._last_alert = text
        self.alerts.appendleft(text)

    def top_relationships(self, count: int = 3):
        items = sorted(self.relationships.items(), key=lambda kv: kv[1], reverse=True)
        return items[:count]

    def _update_mood(self) -> None:
        if not self.relationships:
            self.mood = "Neutral"
            return
        avg = sum(self.relationships.values()) / len(self.relationships)
        if avg >= 75:
            self.mood = "Aliado"
        elif avg >= 55:
            self.mood = "Colaborativo"
        elif avg >= 35:
            self.mood = "Neutral"
        else:
            self.mood = "Tenso"

    def adjust_grades(self, delta: float) -> None:
        self.grades = max(0.0, min(100.0, self.grades + delta))
        if delta < 0:
            self.push_alert("Tus calificaciones bajaron")
        elif delta > 0:
            self.note_interaction("Recuperaste calificaciones")
        if self.grades <= 0:
            self.hp = max(0.0, self.hp - 8.0)

    def adjust_social(self, delta: float) -> None:
        self.social_health = max(0.0, min(100.0, self.social_health + delta))
        if delta < 0:
            self.push_alert("Tu vida social se resiente")
        elif delta > 0:
            self.note_interaction("Tu vida social mejora")
        if self.social_health <= 0:
            self.hp = max(0.0, self.hp - 6.0)
        self._update_mood()

    def restore_hunger(self, amount: float) -> None:
        self.hunger = max(0.0, min(100.0, self.hunger + amount))
        if amount > 0:
            self.note_interaction("Te alimentaste")

    def _update_needs(self, dt: float) -> None:
        decay = dt * 1.6
        self.hunger = max(0.0, self.hunger - decay)
        if self.hunger <= 35:
            self.push_alert("Necesitas comer algo")
        if self.hunger <= 0:
            self.hp = max(0.0, self.hp - dt * 10.0)
        if self.idle_time > 12.0:
            self.hp = max(0.0, self.hp - dt * 8.0)
            self.push_alert("Si no haces nada perderás energía")
        if self.hp <= 0:
            self.push_alert("Colapsaste por agotamiento")

    def begin_greeting(self, name: str) -> None:
        self.pending_greeting = name
        self.push_alert(f"{name} te está saludando")

    def resolve_greeting(self, name: str, responded: bool) -> None:
        if self.pending_greeting != name:
            return
        if responded:
            self.adjust_social(+9)
            self.note_interaction(f"Saludaste a {name}")
        else:
            self.adjust_social(-12)
            self.hp = max(0.0, self.hp - 5.0)
            self.note_interaction(f"Ignoraste a {name}")
        self.pending_greeting = None


class NPC(Character):
    def __init__(self, x, y, name, script_id):
        super().__init__(
            x,
            y,
            name=name,
            color=(200, 200, 200),
            speed=110.0,
            max_hp=90,
            compatibility=["social"],
            aptitudes=["Diálogo"],
        )
        self.script_id = script_id
        self._t = 0.0
        self._dirv = pygame.Vector2(random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]))

    def update(self, dt, tilemap):
        self._t += dt
        if self._t > 1.5:
            self._t = 0.0
            self._dirv.update(random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]))
        vel = self._dirv * 60.0
        if abs(vel.x) > abs(vel.y):
            self.set_dir("right" if vel.x > 0 else "left")
        elif abs(vel.y) > 0:
            self.set_dir("down" if vel.y > 0 else "up")
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)


class Enemy(Character):
    def __init__(self, x, y):
        super().__init__(
            x,
            y,
            name="Enemigo",
            color=RED,
            importance=4,
            speed=ENEMY_SPEED,
            max_hp=80,
            compatibility=["bienestar"],
            aptitudes=["Plan de seguridad"],
        )

    def update(self, dt, tilemap, player=None):
        if player:
            dirv = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
            if dirv.length_squared() > 1.0:
                dirv = dirv.normalize() * self.speed
            vel = dirv
            if abs(vel.x) > abs(vel.y):
                self.set_dir("right" if vel.x > 0 else "left")
            elif abs(vel.y) > 0:
                self.set_dir("down" if vel.y > 0 else "up")
        else:
            vel = pygame.Vector2(0, 0)
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)


class Item(Entity):
    def __init__(self, x, y, item_id):
        super().__init__(x, y, TILE // 2, TILE // 2, GREEN)
        self.item_id = item_id

    def picked(self, player):
        player.inventory.append(self.item_id)
        self.dead = True


class AICharacter(Character):
    def __init__(
        self,
        x: int,
        y: int,
        name: str,
        color,
        importance: int,
        speed: float,
        max_hp: int,
        compatibility: Iterable[str],
        aptitudes: Iterable[str],
        visible: bool = True,
    ):
        super().__init__(
            x,
            y,
            name=name,
            color=color,
            importance=importance,
            speed=speed,
            max_hp=max_hp,
            compatibility=compatibility,
            aptitudes=aptitudes,
            virtual_only=not visible,
        )
        self.visible = visible
        self._idle_timer = random.uniform(1.0, 2.5)
        self._idle_vector = pygame.Vector2(random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]))
        self._idle_speed = max(30.0, speed * 0.45)

    def idle_step(self, dt: float, tilemap):
        if self.virtual_only:
            self._tick_feedback(dt)
            return
        self._idle_timer -= dt
        if self._idle_timer <= 0:
            self._idle_timer = random.uniform(1.0, 2.4)
            self._idle_vector.update(random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (0, 0)]))
        vel = self._idle_vector * self._idle_speed
        if vel.length_squared() > 0.1:
            if abs(vel.x) > abs(vel.y):
                self.set_dir("right" if vel.x > 0 else "left")
            else:
                self.set_dir("down" if vel.y > 0 else "up")
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)
        self._tick_feedback(dt)


class Collector(AICharacter):
    def __init__(self, x, y, name, visible: bool = True):
        super().__init__(
            x,
            y,
            name=name,
            color=GREEN,
            importance=2,
            speed=120.0,
            max_hp=95,
            compatibility=["academia", "colaboracion"],
            aptitudes=["Apoyo académico", "Tutoría intensiva"],
            visible=visible,
        )


class Hunter(AICharacter):
    def __init__(self, x, y, name, visible: bool = True):
        super().__init__(
            x,
            y,
            name=name,
            color=ORANGE,
            importance=3,
            speed=125.0,
            max_hp=105,
            compatibility=["academia", "emergencia"],
            aptitudes=["Tutoría intensiva", "Plan de seguridad"],
            visible=visible,
        )


class Builder(AICharacter):
    def __init__(self, x, y, name, visible: bool = True):
        super().__init__(
            x,
            y,
            name=name,
            color=BLUE,
            importance=4,
            speed=110.0,
            max_hp=110,
            compatibility=["logistica"],
            aptitudes=["Logística escolar"],
            visible=visible,
        )


class Guardian(AICharacter):
    def __init__(self, x, y, name, visible: bool = True):
        super().__init__(
            x,
            y,
            name=name,
            color=PURPLE,
            importance=5,
            speed=115.0,
            max_hp=120,
            compatibility=["bienestar", "resguardo"],
            aptitudes=["Plan de seguridad"],
            visible=visible,
        )
