# settings.py
import os

# -----------------------------
# Pantalla / Juego base
# -----------------------------
WIDTH, HEIGHT = 1600, 900  # área jugable principal (mapa)
HUD_PANEL_WIDTH = 360
WINDOW_WIDTH = WIDTH + HUD_PANEL_WIDTH
WINDOW_HEIGHT = HEIGHT
FULLSCREEN = True
FPS = 60
TITLE = "UP Adventure — Starter Kit (Top-Down)"
TILE = 32

# -----------------------------
# Colores
# -----------------------------
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
GRAY   = (60, 60, 60)
RED    = (200, 40, 40)
GREEN  = (40, 200, 100)
BLUE   = (60, 120, 220)
YELLOW = (235, 200, 40)
PURPLE = (128, 90, 200)
ORANGE = (230, 140, 40)

# Paleta para botones / UI
BURGUNDY = (100, 0, 30)
WINE     = (120, 0, 30)
WINE_HOV = (160, 0, 50)

# -----------------------------
# Controles
# -----------------------------
KEY_UP = "w"
KEY_DOWN = "s"
KEY_LEFT = "a"
KEY_RIGHT = "d"
KEY_INTERACT = "e"
KEY_INVENTORY = "i"
KEY_ACTION_RUSH = "q"
KEY_FIGHT = "f"
KEY_MESSAGE = "m"
KEY_HELP = "h"

# -----------------------------
# Gameplay base
# -----------------------------
PLAYER_SPEED = 180
ENEMY_SPEED  = 120

# -----------------------------
# Rutas (seguras)
# -----------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
MAPS_DIR   = os.path.join(DATA_DIR, "maps")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMG_DIR    = os.path.join(ASSETS_DIR, "images")
FONTS_DIR  = os.path.join(ASSETS_DIR, "fonts")

# Directorios de audio
SFX_DIR    = os.path.join(ASSETS_DIR, "sfx")
MUSIC_DIR  = os.path.join(ASSETS_DIR, "music")

# Directorio del mapa del ZIP que subiste
UP_MAP_DIR = os.path.join(BASE_DIR, "UP_MAP")

# Crear carpetas que el juego usa si no existen
for d in (DATA_DIR, MAPS_DIR, ASSETS_DIR, IMG_DIR, FONTS_DIR, SFX_DIR, MUSIC_DIR):
    os.makedirs(d, exist_ok=True)

# -----------------------------
# Archivo TMX principal (del ZIP)
# -----------------------------
# Usa el TMX que venía en tu comprimido: UP_MAP/UP_map.tmx
TMX_MAP_FILE = os.path.join(BASE_DIR, "UP_MAP", "UP_map.tmx")
# (equivalente a: TMX_MAP_FILE = os.path.join(UP_MAP_DIR, "UP_map.tmx"))

# Si prefieres usar uno en data/maps, cámbialo por:
# TMX_MAP_FILE = os.path.join(MAPS_DIR, "UP_CITY_map.tmx")

# -----------------------------
# Archivos de datos
# -----------------------------
DEFAULT_MAP_CSV = os.path.join(MAPS_DIR, "overworld.csv")  # opcional (no usado si cargas TMX)
DIALOGUES_JSON  = os.path.join(DATA_DIR, "dialogues.json")

# -----------------------------
# Portada y fuente UI
# -----------------------------
TITLE_IMAGE  = os.path.join(IMG_DIR, "portada.png")
UI_FONT_FILE = os.path.join(FONTS_DIR, "04B_30__.ttf")  # usa fallback arial si no existe

# -----------------------------
# Audio
# -----------------------------
HOVER_SFX  = os.path.join(SFX_DIR, "hover.ogg")
MUSIC_FILE = os.path.join(MUSIC_DIR, "bgm.wav")

DEFAULT_MUSIC_VOL = 0.60
DEFAULT_SFX_VOL   = 0.80

# -----------------------------
# Tiempo / calendario (opcionales)
# -----------------------------
DAY_SECONDS = 300.0
CLOCK_SPEED = 1.0

# -----------------------------
# Métricas / Economía (opcionales)
# -----------------------------
GPA_START   = 95.0
GPA_PENALTY = 5.0

MONEY_RULES = {
    "CLASE"      : +5,
    "ASESORIAS"  : +4,
    "SERVICIO"   : +3,
    "TAREA"      : +4,
    "COMER"      : +1,
    "DEPORTE"    : +2,
    "ARTE"       : +2,
    "SOCIALIZAR" : +1,
    "BAÑO"       : +0,
    "VENDIMIA"   : +3,
    "ADMISIONES" : +3,
    "CONTADURIA" : +3,
    "ASEO"       : +2,
    "IDLE"       : -1,
}
ECON_START_BALANCE = 0.0

# -----------------------------
# PlayerTasks por defecto (demo)
# -----------------------------
PLAYER_TASKS_DEFAULT = [
    ("Ir a clase", "clase",      15.0, 180.0),
    ("Comer",      "cafeteria",  10.0, 240.0),
    ("Hacer tarea","tarea",      20.0, 280.0),
    ("Asesorías",  "asesorias",  10.0, 260.0),
]
