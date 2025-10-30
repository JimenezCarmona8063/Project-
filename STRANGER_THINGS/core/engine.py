# core/engine.py
import pygame
from settings import WIDTH, HEIGHT

class Camera2D:
    """
    Cámara 2D sencilla con:
      - center_on(rect): centra la vista en un rect (jugador, etc.)
      - apply(rect): convierte coords del mundo -> pantalla
      - view_rect(): devuelve (camx, camy, cw, ch) que usa el renderer del TMX
    """
    def __init__(self, world_w: int, world_h: int, screen_w: int = WIDTH, screen_h: int = HEIGHT):
        self.world_w = max(1, int(world_w))
        self.world_h = max(1, int(world_h))
        self.screen_w = int(screen_w)
        self.screen_h = int(screen_h)
        self.x = 0
        self.y = 0

    def clamp(self):
        """Mantiene la cámara dentro de los límites del mundo."""
        self.x = max(0, min(self.x, self.world_w - self.screen_w))
        self.y = max(0, min(self.y, self.world_h - self.screen_h))

    def center_on(self, target_rect: pygame.Rect):
        """Centra la cámara en el rect objetivo."""
        cx = target_rect.centerx - self.screen_w // 2
        cy = target_rect.centery - self.screen_h // 2
        self.x, self.y = int(cx), int(cy)
        self.clamp()

    def apply(self, world_rect: pygame.Rect) -> pygame.Rect:
        """Transforma un rect del mundo a coordenadas de pantalla."""
        return pygame.Rect(
            world_rect.x - self.x,
            world_rect.y - self.y,
            world_rect.w,
            world_rect.h
        )

    def view_rect(self):
        """Rect de vista (camx, camy, width, height) — usado por el dibujador TMX."""
        return int(self.x), int(self.y), int(self.screen_w), int(self.screen_h)


# ---------- Base de escenas y utilidades ----------

class Scene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, event): pass
    def update(self, dt: float): pass
    def draw(self, surface: pygame.Surface): pass


def draw_text(surface: pygame.Surface, text: str, font: pygame.font.Font,
              color=(255, 255, 255), center=None, topleft=None):
    """Helper simple para dibujar texto."""
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center is not None:
        rect.center = center
    elif topleft is not None:
        rect.topleft = topleft
    surface.blit(img, rect)
    return rect
