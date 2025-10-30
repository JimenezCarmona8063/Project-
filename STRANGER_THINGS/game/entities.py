# game/entities.py
import random
from typing import Iterable, Optional

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

        moving = False
        if not self.virtual_only and self.action_target:
            center = pygame.Vector2(self.rect.center)
            delta = self.action_target - center
            if delta.length_squared() > 9:
                vel = delta.normalize() * self.speed
                self.rect = move_with_collision(self.rect, vel, tilemap, dt)
                moving = True
        self.tick_anim(dt, moving)
        self.action_timer += dt
        self._tick_feedback(dt)

    def idle_step(self, dt: float, tilemap):
        self.tick_anim(dt, False)
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
            compatibility=["lider"],
            aptitudes=["Recolectar", "Construir", "Defender/Resguardarse"],
        )
        self.inventory = []
        self.interact_cooldown = 0.0

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
            compatibility=["seguridad"],
            aptitudes=["Defender/Resguardarse"],
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
            compatibility=["naturaleza", "equipo"],
            aptitudes=["Recolectar", "Recolectar - Cosecha"],
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
            compatibility=["naturaleza", "seguridad"],
            aptitudes=["Recolectar - Caza", "Defender/Resguardarse"],
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
            compatibility=["infraestructura"],
            aptitudes=["Construir"],
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
            compatibility=["seguridad", "resguardo"],
            aptitudes=["Defender/Resguardarse"],
            visible=visible,
        )
