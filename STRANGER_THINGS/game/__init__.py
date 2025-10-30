# main.py — imports necesarios
import os, sys, json
import pygame

from settings import (
    # ventana y juego
    WIDTH, HEIGHT, FPS, TILE, TITLE,
    # controles
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_INTERACT, KEY_INVENTORY,
    # rutas y assets
    DEFAULT_MAP_CSV, DIALOGUES_JSON, TITLE_IMAGE, UI_FONT_FILE,
    # audio
    MUSIC_FILE, HOVER_SFX,
    # colores UI (si los usas)
    RED, WINE, WINE_HOV
)

from core.engine import Camera2D, Scene, draw_text
from core.tilemap_tmx import TmxMap

# UI (HUD, botones, sliders de ajustes)
from game.ui import draw_hud, Button
# importa Slider sólo si tu SettingsScene lo usa
try:
    from game.ui import Slider
except Exception:
    Slider = None

# entidades del juego
from game.entities import Player, NPC, Enemy, Item

# diálogos (si los invocas en runtime)
from game.dialogue import DialogueBox

class Game:
    def __init__(self):
        pygame.init()
        # audio (no falla si no hay dispositivo)
        try:
            pygame.mixer.init()
        except Exception:
            pass

        # tamaño de ventana según portada si existe
        win_size = (WIDTH, HEIGHT)
        try:
            tmp = pygame.image.load(TITLE_IMAGE)
            win_size = (tmp.get_width(), tmp.get_height())
        except Exception:
            win_size = (WIDTH, HEIGHT)

        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode(win_size)
        self.clock = pygame.time.Clock()
        
        self.play_scene = None
        self.selected_role = None
        
        # volúmenes globales (si usas ajustes)
        self.music_vol = 0.60
        self.sfx_vol   = 0.80

        # música de fondo (opcional)
        self.music_loaded = False
        try:
            if os.path.isfile(MUSIC_FILE):
                pygame.mixer.music.load(MUSIC_FILE)
                pygame.mixer.music.set_volume(self.music_vol)  # usa tu slider
                pygame.mixer.music.play(-1)  # loop
                self.music_loaded = True
        except Exception:
            self.music_loaded = False
        
        try:
            pygame.mixer.init()
        except Exception:
            pass

        # sfx hover global (opcional)
        self.hover_sfx = None
        try:
            if os.path.isfile(HOVER_SFX):
                self.hover_sfx = pygame.mixer.Sound(HOVER_SFX)
                self.hover_sfx.set_volume(self.sfx_vol)
        except Exception:
            self.hover_sfx = None

        # estado global
        self.play_scene = None
        self.scene = None
        self.selected_role = None

"""
ya tenog mi música destry:
    from game.ui import Slider  # solo si tu SettingsScene lo usa
except Exception:
    Slider = None
"""