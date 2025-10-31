# core/tilemap_tmx.py
import os
from typing import Dict, List, Optional

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

        # Colisiones
        self.collision_rects: list[pygame.Rect] = []
        self._load_collisions()

        # Spawn del jugador
        self.player_spawn = self._find_player_spawn(default=(self.tile_w, self.tile_h))

        # Salones (object layers) y puertas para ingreso
        self.rooms: List[Dict] = []
        self.doors: List[Dict] = []
        self._load_rooms_and_doors()

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

    def _load_rooms_and_doors(self) -> None:
        for layer in self.tmx.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                props = getattr(obj, "properties", {}) or {}
                name = obj.name or props.get("name") or f"{layer.name}_{getattr(obj, 'id', len(self.rooms)+1)}"
                rect = pygame.Rect(
                    int(obj.x),
                    int(obj.y),
                    int(getattr(obj, "width", self.tile_w) or self.tile_w),
                    int(getattr(obj, "height", self.tile_h) or self.tile_h),
                )
                obj_type = (getattr(obj, "type", "") or "").lower()
                is_room = (
                    obj_type == "room"
                    or "room" in (name or "").lower()
                    or str(props.get("room", "")).lower() in ("1", "true", "yes")
                )
                if is_room:
                    tags = self._extract_tags(name, layer.name, props)
                    self.rooms.append({
                        "name": name,
                        "layer": layer.name,
                        "rect": rect,
                        "props": props,
                        "tags": tags,
                    })
                    continue

                is_door = (
                    obj_type == "door"
                    or "door" in (name or "").lower()
                    or str(props.get("door", "")).lower() in ("1", "true", "yes")
                )
                if is_door:
                    self.doors.append({
                        "name": name,
                        "layer": layer.name,
                        "rect": rect,
                        "dest": props.get("dest") or props.get("room") or props.get("target") or props.get("dest_room"),
                        "props": props,
                    })

    def _extract_tags(self, name: str, layer_name: str, props: dict) -> List[str]:
        tags: set[str] = set()

        def _tokenise(text: str) -> None:
            if not text:
                return
            for chunk in str(text).replace("/", " ").replace("-", " ").replace(",", " ").split():
                word = chunk.strip().lower()
                if len(word) >= 3:
                    tags.add(word)

        _tokenise(name or "")
        _tokenise(layer_name or "")

        for key in ("tags", "tag", "categoria", "category", "focus", "type", "role"):
            value = props.get(key)
            if isinstance(value, str):
                _tokenise(value)
            elif isinstance(value, (list, tuple)):
                for v in value:
                    _tokenise(v)

        return sorted(tags)

    # ------------------- Render -------------------
    def draw(self, surface: pygame.Surface, camera) -> None:
        camx, camy, cw, ch = camera.view_rect()

        for layer in self.tmx.layers:
            if not getattr(layer, "visible", True):
                continue

            # Image Layer (foto base)
            if isinstance(layer, pytmx.TiledImageLayer):
                img = layer.image
                if img:
                    ox = int(getattr(layer, "offsetx", 0))
                    oy = int(getattr(layer, "offsety", 0))
                    surface.blit(img, (ox - camx, oy - camy))

            # Tile Layer
            elif isinstance(layer, pytmx.TiledTileLayer):
                tw, th = self.tile_w, self.tile_h
                start_x = max(0, camx // tw)
                end_x = min(self.width_tiles, (camx + cw) // tw + 2)
                start_y = max(0, camy // th)
                end_y = min(self.height_tiles, (camy + ch) // th + 2)

                # Usamos layer.data en lugar de layer.content2d
                for x, y, gid in layer:
                    if x < start_x or x > end_x or y < start_y or y > end_y:
                        continue
                    if gid == 0:
                        continue
                    tile_img = self.tmx.get_tile_image_by_gid(gid)
                    if tile_img:
                        surface.blit(tile_img, (x * tw - camx, y * th - camy))

    # ------------------- Debug -------------------
    def debug_draw_collisions(self, surface: pygame.Surface, camera, color=(255, 60, 60)):
        camx, camy, _, _ = camera.view_rect()
        for r in self.collision_rects:
            pygame.draw.rect(surface, color, pygame.Rect(r.x - camx, r.y - camy, r.w, r.h), 2)

    # ------------------- Rooms helpers -------------------
    def get_room(self, name: Optional[str]):
        if not name:
            return None
        for room in self.rooms:
            if room.get("name") == name:
                return room
        return None

    def room_tags(self, name: Optional[str]) -> List[str]:
        room = self.get_room(name)
        if not room:
            return []
        tags = room.get("tags")
        if isinstance(tags, (list, tuple)):
            return list(tags)
        return []

    def room_for_rect(self, rect: pygame.Rect):
        center = rect.center
        for room in self.rooms:
            room_rect = room.get("rect")
            if isinstance(room_rect, pygame.Rect) and room_rect.collidepoint(center):
                return room
        return None

    def door_for_rect(self, rect: pygame.Rect):
        for door in self.doors:
            door_rect = door.get("rect")
            if isinstance(door_rect, pygame.Rect) and door_rect.colliderect(rect):
                return door
        return None

    def closest_room_to_rect(self, rect: pygame.Rect):
        best = None
        best_dist = None
        center = pygame.Vector2(rect.center)
        for room in self.rooms:
            room_rect = room.get("rect")
            if not isinstance(room_rect, pygame.Rect):
                continue
            room_center = pygame.Vector2(room_rect.center)
            dist = room_center.distance_to(center)
            if best is None or dist < best_dist:
                best = room
                best_dist = dist
        return best
