# core/tilemap.py
# Proxy: usa TMX si está disponible; si no, cae a un CSV sencillo.

try:
    from .tilemap_tmx import TmxMap as TileMap
    TMX_IMPORT_ERROR = None
except Exception as _tmx_err:
    TMX_IMPORT_ERROR = _tmx_err
    import os, csv, pygame
    from settings import TILE, DEFAULT_MAP_CSV

    def _load_csv_grid(csv_path):
        grid = []
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                grid.append([int(x) for x in row])
        return grid

    class TileMap:
        """Fallback mínimo en caso de que falle el TMX."""
        def __init__(self, csv_path=None):
            self.csv_path = csv_path or DEFAULT_MAP_CSV
            if not os.path.isfile(self.csv_path):
                # Mensaje claro SIN typos
                msg = f"No existe el mapa CSV: {self.csv_path}"
                if TMX_IMPORT_ERROR is not None:
                    msg += f"\n(Fallo al cargar TMX: {TMX_IMPORT_ERROR})"
                raise FileNotFoundError(msg)

            self.grid = _load_csv_grid(self.csv_path)
            self.h = len(self.grid)
            self.w = len(self.grid[0]) if self.h else 0

            self.solid_rects = [
                pygame.Rect(x*TILE, y*TILE, TILE, TILE)
                for y, row in enumerate(self.grid)
                for x, tid in enumerate(row)
                if tid == 1
            ]

        def draw(self, surf, camera):
            for y, row in enumerate(self.grid):
                for x, tid in enumerate(row):
                    color = (50, 50, 50) if tid == 0 else (80, 100, 180)
                    r_world = pygame.Rect(x*TILE, y*TILE, TILE, TILE)
                    r = camera.apply(r_world)
                    pygame.draw.rect(surf, color, r)

        def rect_collide(self, rect):
            return any(rect.colliderect(r) for r in self.solid_rects)

        def world_size(self):
            return self.w*TILE, self.h*TILE
