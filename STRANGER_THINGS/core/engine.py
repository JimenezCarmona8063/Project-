# core/engine.py
import pygame
from settings import WIDTH, HEIGHT

class Camera2D:
    """
    Cámara 2D sencilla con soporte de zoom:
      - center_on(rect): centra la vista en un rect (jugador, etc.)
      - apply(rect): convierte coords del mundo -> pantalla
      - view_rect(): devuelve (camx, camy, cw, ch) (coordenadas en el mundo)
    """

    def __init__(
        self,
        world_w: int,
        world_h: int,
        screen_w: int = WIDTH,
        screen_h: int = HEIGHT,
        zoom: float = 1.0,
    ):
        self.world_w = max(1, int(world_w))
        self.world_h = max(1, int(world_h))
        self.screen_w = int(screen_w)
        self.screen_h = int(screen_h)
        self.x = 0.0
        self.y = 0.0
        self._zoom = 1.0
        self.set_zoom(zoom)

    # --------------------------- helpers ---------------------------
    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def view_w(self) -> float:
        return self.screen_w / self._zoom

    @property
    def view_h(self) -> float:
        return self.screen_h / self._zoom

    def set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.1, float(zoom))
        self.clamp()

    def zoom_in(self, amount: float) -> None:
        self.set_zoom(self._zoom + amount)

    def zoom_out(self, amount: float) -> None:
        self.set_zoom(self._zoom - amount)

    def clamp(self) -> None:
        """Mantiene la cámara dentro de los límites del mundo."""
        max_x = max(0.0, self.world_w - self.view_w)
        max_y = max(0.0, self.world_h - self.view_h)
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))

    def center_on(self, target_rect: pygame.Rect) -> None:
        """Centra la cámara en el rect objetivo."""
        cx = target_rect.centerx - self.view_w / 2
        cy = target_rect.centery - self.view_h / 2
        self.x, self.y = float(cx), float(cy)
        self.clamp()

    def apply(self, world_rect: pygame.Rect) -> pygame.Rect:
        """Transforma un rect del mundo a coordenadas de pantalla."""
        sx = (world_rect.x - self.x) * self._zoom
        sy = (world_rect.y - self.y) * self._zoom
        sw = max(1, world_rect.w * self._zoom)
        sh = max(1, world_rect.h * self._zoom)
        return pygame.Rect(int(round(sx)), int(round(sy)), int(round(sw)), int(round(sh)))

    def project_point(self, x: float, y: float) -> tuple[int, int]:
        """Convierte un punto del mundo a pantalla, aplicando zoom."""
        sx = (x - self.x) * self._zoom
        sy = (y - self.y) * self._zoom
        return int(round(sx)), int(round(sy))

    def view_rect(self) -> tuple[int, int, int, int]:
        """Rect de vista (camx, camy, width, height) — usado por el renderer TMX."""
        return (
            int(self.x),
            int(self.y),
            max(1, int(round(self.view_w))),
            max(1, int(round(self.view_h))),
        )


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
