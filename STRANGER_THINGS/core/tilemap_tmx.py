# core/tilemap_tmx.py
import os
import pygame
from settings import TMX_MAP_FILE, TILE

# Carga segura de pytmx
PYTMX_OK = True
try:
    from pytmx.util_pygame import load_pygame
    import pytmx
except Exception:
    PYTMX_OK = False
    print("[AVISO] pytmx no disponible. Instala con: pip install pytmx")


class TmxMap:
    """
    Loader de TMX con:
      - Dibujo de Tile Layers e Image Layers (fotos)
      - Colisiones de capa "Collisions" (Object o Tile Layer)
      - Punto de spawn por objeto "Player" o propiedad player_spawn=true
    """

    def __init__(self, tmx_path: str | None = None):
        if not PYTMX_OK:
            raise RuntimeError("pytmx no está disponible.")

        self.tmx_path = tmx_path or TMX_MAP_FILE
        if not os.path.isfile(self.tmx_path):
            raise FileNotFoundError(f"No se encontró el TMX: {self.tmx_path}")

        # Cargar TMX
        self.tmx = load_pygame(self.tmx_path)

        self.width_tiles = self.tmx.width
        self.height_tiles = self.tmx.height
        self.tile_w = self.tmx.tilewidth
        self.tile_h = self.tmx.tileheight

        # caché simple para superficies escaladas según zoom
        self._scale_cache: dict[tuple[int, float], pygame.Surface] = {}

        # Colisiones
        self.collision_rects: list[pygame.Rect] = []
        self._load_collisions()

        # Spawn del jugador
        self.player_spawn = self._find_player_spawn(default=(self.tile_w, self.tile_h))

    # ------------------- Datos del mundo -------------------
    def world_size(self):
        return (self.width_tiles * self.tile_w, self.height_tiles * self.tile_h)

    # ------------------- Colisiones -------------------
    def _load_collisions(self):
        """Carga colisiones de Object Layer 'Collisions' o de tiles con prop block=1."""
        # 1) Object Layer
        try:
            layer = self.tmx.get_layer_by_name("Collisions")
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    r = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                    self.collision_rects.append(r)
        except Exception:
            pass

        # 2) Tile Layer con propiedad 'block'
        try:
            layer = self.tmx.get_layer_by_name("Collisions")
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:  # iterador seguro
                    if gid == 0:
                        continue
                    props = self.tmx.get_tile_properties_by_gid(gid) or {}
                    if props.get("block") in (1, True, "1", "true", "True"):
                        r = pygame.Rect(x * self.tile_w, y * self.tile_h, self.tile_w, self.tile_h)
                        self.collision_rects.append(r)
        except Exception:
            pass

    def collide_rect(self, rect: pygame.Rect) -> bool:
        for r in self.collision_rects:
            if rect.colliderect(r):
                return True
        return False

    # Alias para compatibilidad
    rect_collide = collide_rect

    # ------------------- Spawn -------------------
    def _find_player_spawn(self, default=(0, 0)):
        for layer in self.tmx.layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    name = (obj.name or "").lower()
                    props = getattr(obj, "properties", {}) or {}
                    if name in ("player", "spawn") or str(props.get("player_spawn", "")).lower() in ("1", "true", "yes"):
                        return (int(obj.x), int(obj.y))
        return default

    # ------------------- Render -------------------
    def _get_scaled(self, surf: pygame.Surface, zoom: float) -> pygame.Surface:
        if zoom == 1.0 or surf is None:
            return surf
        key = (id(surf), zoom)
        cached = self._scale_cache.get(key)
        target_size = (
            max(1, int(round(surf.get_width() * zoom))),
            max(1, int(round(surf.get_height() * zoom))),
        )
        if cached and cached.get_size() == target_size:
            return cached
        scaled = pygame.transform.smoothscale(surf, target_size)
        self._scale_cache[key] = scaled
        return scaled

    def draw(self, surface: pygame.Surface, camera) -> None:
        camx, camy, cw, ch = camera.view_rect()
        zoom = getattr(camera, "zoom", 1.0)
        project = getattr(camera, "project_point", None)

        for layer in self.tmx.layers:
            if not getattr(layer, "visible", True):
                continue

            # Image Layer (foto base)
            if isinstance(layer, pytmx.TiledImageLayer):
                img = layer.image
                if img:
                    ox = int(getattr(layer, "offsetx", 0))
                    oy = int(getattr(layer, "offsety", 0))
                    if project:
                        screen_pos = project(ox, oy)
                    else:
                        screen_pos = (ox - camx, oy - camy)
                    surface.blit(self._get_scaled(img, zoom), screen_pos)

            # Tile Layer
            elif isinstance(layer, pytmx.TiledTileLayer):
                tw, th = self.tile_w, self.tile_h
                start_x = max(0, camx // tw)
                end_x = min(self.width_tiles, (camx + cw) // tw + 2)
                start_y = max(0, camy // th)
                end_y = min(self.height_tiles, (camy + ch) // th + 2)

                # Usamos layer.data en lugar de layer.content2d
                offset_x = int(getattr(layer, "offsetx", 0))
                offset_y = int(getattr(layer, "offsety", 0))

                for x, y, gid in layer:
                    if x < start_x or x > end_x or y < start_y or y > end_y:
                        continue
                    if gid == 0:
                        continue
                    tile_img = self.tmx.get_tile_image_by_gid(gid)
                    if tile_img:
                        world_x = x * tw + offset_x
                        world_y = y * th + offset_y
                        if project:
                            screen_x, screen_y = project(world_x, world_y)
                        else:
                            screen_x = world_x - camx
                            screen_y = world_y - camy
                        surface.blit(self._get_scaled(tile_img, zoom), (screen_x, screen_y))

    # ------------------- Debug -------------------
    def debug_draw_collisions(self, surface: pygame.Surface, camera, color=(255, 60, 60)):
        camx, camy, _, _ = camera.view_rect()
        for r in self.collision_rects:
            pygame.draw.rect(surface, color, pygame.Rect(r.x - camx, r.y - camy, r.w, r.h), 2)
