# game/entities.py
import pygame, random, math
from settings import TILE, PLAYER_SPEED, ENEMY_SPEED, RED, GREEN, YELLOW

def move_with_collision(rect, vel, tilemap, dt):
    # Eje X
    rect.x += vel.x * dt
    if tilemap.rect_collide(rect):
        step = 1 if vel.x > 0 else -1
        while tilemap.rect_collide(rect):
            rect.x -= step
    # Eje Y
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
        # soporte básico de dirección/animación para el engine
        self._dir = "down"     # "up","down","left","right"
        self._anim_t = 0.0
        self._anim_on = False

    def set_dir(self, d):
        self._dir = d

    def tick_anim(self, dt, moving):
        # marcador simple para animación (si luego cambias sprites)
        self._anim_on = bool(moving)
        self._anim_t = (self._anim_t + dt) if moving else 0.0

    def update(self, dt, tilemap):
        pass

    def draw(self, surf, camera):
        pygame.draw.rect(surf, self.color, camera.apply(self.rect))

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, TILE-6, TILE-4, YELLOW)
        self.speed = float(PLAYER_SPEED)
        self.hp = 5
        self.inventory = []
        self.interact_cooldown = 0.0

    def handle_input(self, keys):
        self.vx = (keys.get("right", False) - keys.get("left", False)) * self.speed
        self.vy = (keys.get("down", False)  - keys.get("up", False))   * self.speed
        # actualizar orientación si hay input
        if abs(self.vx) > abs(self.vy):
            if self.vx > 0: self.set_dir("right")
            elif self.vx < 0: self.set_dir("left")
        elif abs(self.vy) > 0:
            if self.vy > 0: self.set_dir("down")
            elif self.vy < 0: self.set_dir("up")

    def update(self, dt, tilemap):
        if self.interact_cooldown > 0:
            self.interact_cooldown -= dt
        vel = pygame.Vector2(self.vx, self.vy)
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)

class NPC(Entity):
    def __init__(self, x, y, name, script_id):
        super().__init__(x, y, TILE-6, TILE-6, (200,200,200))
        self.name = name
        self.script_id = script_id
        self._t = 0.0
        self._dirv = pygame.Vector2(random.choice([(1,0),(-1,0),(0,1),(0,-1),(0,0)]))

    def update(self, dt, tilemap):
        self._t += dt
        if self._t > 1.5:
            self._t = 0.0
            self._dirv.update(random.choice([(1,0),(-1,0),(0,1),(0,-1),(0,0)]))
        vel = self._dirv * 60.0
        # orientar
        if abs(vel.x) > abs(vel.y):
            self.set_dir("right" if vel.x > 0 else "left")
        elif abs(vel.y) > 0:
            self.set_dir("down" if vel.y > 0 else "up")
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)

class Enemy(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, TILE-6, TILE-6, RED)
        self.speed = float(ENEMY_SPEED)

    def update(self, dt, tilemap, player=None):
        if player:
            dirv = pygame.Vector2(player.rect.center) - pygame.Vector2(self.rect.center)
            if dirv.length_squared() > 1.0:
                dirv = dirv.normalize() * self.speed
            vel = dirv
            # orientar hacia el jugador
            if abs(vel.x) > abs(vel.y):
                self.set_dir("right" if vel.x > 0 else "left")
            elif abs(vel.y) > 0:
                self.set_dir("down" if vel.y > 0 else "up")
        else:
            vel = pygame.Vector2(0,0)
        self.rect = move_with_collision(self.rect, vel, tilemap, dt)
        self.tick_anim(dt, vel.length_squared() > 0.1)

class Item(Entity):
    def __init__(self, x, y, item_id):
        super().__init__(x, y, TILE//2, TILE//2, GREEN)
        self.item_id = item_id

    def picked(self, player):
        player.inventory.append(self.item_id)
        self.dead = True
