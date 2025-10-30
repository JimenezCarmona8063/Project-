# main.py — versión ordenada para evitar "MenuScene undefined"
import os, sys, json
import pygame

from settings import (
    WIDTH, HEIGHT, FPS, TILE, TITLE,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_INTERACT, KEY_INVENTORY,
    DEFAULT_MAP_CSV, DIALOGUES_JSON, TITLE_IMAGE, UI_FONT_FILE,
    MUSIC_FILE, HOVER_SFX, DEFAULT_MUSIC_VOL, DEFAULT_SFX_VOL,
    WINE, WINE_HOV, RED  
)

from core.engine import Camera2D, Scene, draw_text
from game.ui import draw_hud, Button, Slider

from game.entities import Player, NPC, Enemy, Item
from game.dialogue import DialogueBox
from core.tilemap_tmx import TmxMap

# ---------- helpers ----------
def load_ui_font(size=32):
    try:
        return pygame.font.Font(UI_FONT_FILE, size)
    except Exception:
        return pygame.font.SysFont("arial", size, bold=True)

def keydict():
    keys = pygame.key.get_pressed()
    kd = {
        "up": keys[getattr(pygame, "K_"+KEY_UP)],
        "down": keys[getattr(pygame, "K_"+KEY_DOWN)],
        "left": keys[getattr(pygame, "K_"+KEY_LEFT)],
        "right": keys[getattr(pygame, "K_"+KEY_RIGHT)],
        "interact": keys[getattr(pygame, "K_"+KEY_INTERACT)],
        "inventory": keys[getattr(pygame, "K_"+KEY_INVENTORY)],
    }
    return kd

# -------------------- ESCENAS --------------------

class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)

        # 1) Cargar TMX
        self.map = TmxMap()  # usa settings.TMX_MAP_FILE

        # 2) Cámara al tamaño del mapa
        # world_w, world_h vienen de tu mapa TMX
        self.camera = Camera2D(*self.map.world_size(), *self.game.screen.get_size())


        # 3) Player en el spawn del TMX
        spawn_x, spawn_y = self.map.player_spawn
        self.player = Player(spawn_x, spawn_y)
        # aplica rol si existe
        ROLE_COLORS = {
            "ALUMNO": (235,200,40),
            "MAESTRO": (200,200,255),
            "COLABORADOR": (255,170,110),
        }
        if getattr(self.game, "selected_role", None) in ROLE_COLORS:
            self.player.color = ROLE_COLORS[self.game.selected_role]

        self.npcs = [
            NPC(8*TILE, 6*TILE, "Profe", "npc_prof"),
            NPC(30*TILE, 20*TILE, "Guardia", "npc_guard"),
        ]
        self.enemies = [Enemy(20*TILE, 4*TILE), Enemy(34*TILE, 14*TILE)]
        self.items = [Item(25*TILE, 8*TILE, "Tarjeta de Acceso")]
        # diálogos
        if not os.path.isfile(DIALOGUES_JSON):
            os.makedirs(os.path.dirname(DIALOGUES_JSON), exist_ok=True)
            with open(DIALOGUES_JSON, "w", encoding="utf-8") as f:
                json.dump({
                    "npc_prof": [
                        "¡Hey! Bienvenido a UP Adventure.",
                        "Trae de la cafetería una *Tarjeta de Acceso* y vuelve conmigo.",
                        "Con eso podrás entrar al laboratorio."
                    ],
                    "npc_guard": [
                        "No puedes pasar sin Tarjeta de Acceso.",
                        "Regresa cuando la tengas."
                    ],
                    "npc_congrats": ["¡Eso es! Ya puedes entrar al lab. ¡Suerte!"]
                }, f, ensure_ascii=False, indent=2)
        with open(DIALOGUES_JSON, "r", encoding="utf-8") as f:
            self.scripts = json.load(f)
        self.dialogue = None
        self.interact_hold = False

    def handle_event(self, event):
        if self.dialogue:
            self.dialogue.handle_event(event)
            if self.dialogue.done:
                self.dialogue = None

    def update(self, dt):
        if not self.dialogue:
            self.player.handle_input(keydict())
        self.player.update(dt, self.map)
        for n in self.npcs: n.update(dt, self.map)
        for e in self.enemies: e.update(dt, self.map, self.player)
        for it in self.items:
            if not it.dead and self.player.rect.colliderect(it.rect):
                it.picked(self.player)
        self.items = [i for i in self.items if not i.dead]

        kd = keydict()
        if kd["interact"] and not self.interact_hold and not self.dialogue:
            self.interact_hold = True
            for n in self.npcs:
                if self.player.rect.colliderect(n.rect.inflate(30,30)):
                    lines = self.scripts.get(n.script_id, ["..."])
                    if n.script_id == "npc_guard" and "Tarjeta de Acceso" in self.player.inventory:
                        lines = self.scripts.get("npc_congrats", ["Bien."])
                    self.dialogue = DialogueBox(lines, n.name)
                    break
        if not kd["interact"]:
            self.interact_hold = False

        self.camera.center_on(self.player.rect)

    def draw(self, surface):
        surface.fill((15,15,20))
        self.map.draw(surface, self.camera)
        for it in self.items: it.draw(surface, self.camera)
        for n in self.npcs: n.draw(surface, self.camera)
        for e in self.enemies: e.draw(surface, self.camera)
        self.player.draw(surface, self.camera)
        draw_hud(surface, self.player)
        if self.dialogue: self.dialogue.draw(surface)

class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bg = None
        try:
            img = pygame.image.load(TITLE_IMAGE).convert()
            self.bg = img
            iw, ih = img.get_width(), img.get_height()
            if (game.screen.get_width(), game.screen.get_height()) != (iw, ih):
                game.screen = pygame.display.set_mode((iw, ih))
        except Exception:
            pass

        self.font_btn = load_ui_font(34)
        self.hover_sfx = getattr(game, "hover_sfx", None)

        # botones vino, un poco más abajo
        W, H = game.screen.get_size()
        BTN_W_FRAC, BTN_H_FRAC = 0.28, 0.10
        X_CENTER_FRAC, FIRST_Y_FRAC, GAP_FRAC = 0.78, 0.62, 0.125
        bw = int(W * BTN_W_FRAC); bh = int(H * BTN_H_FRAC)
        cx = int(W * X_CENTER_FRAC)
        y1 = int(H * FIRST_Y_FRAC)
        y2 = int(H * (FIRST_Y_FRAC + GAP_FRAC))
        y3 = int(H * (FIRST_Y_FRAC + 2*GAP_FRAC))
        DARK = (160,0,50)
        self.buttons = [
            Button(pygame.Rect(cx-bw//2, y1-bh//2, bw, bh), "INICIAR",  self.font_btn,
                   self.start_new, bg=(120,0,30), bg_hover=DARK, fg=(255,255,255),
                   hover_sound=self.hover_sfx),
            Button(pygame.Rect(cx-bw//2, y2-bh//2, bw, bh), "REANUDAR", self.font_btn,
                   self.resume_game, bg=(120,0,30), bg_hover=DARK, fg=(255,255,255),
                   hover_sound=self.hover_sfx),
            Button(pygame.Rect(cx-bw//2, y3-bh//2, bw, bh), "AJUSTES",  self.font_btn,
                   self.open_settings, bg=(120,0,30), bg_hover=DARK, fg=(255,255,255),
                   hover_sound=self.hover_sfx),
        ]

    def start_new(self):
        self.game.change_scene(CharacterSelectScene(self.game))

    def resume_game(self):
        if self.game.play_scene is None:
            self.game.play_scene = PlayScene(self.game)
        self.game.change_scene(self.game.play_scene)

    def open_settings(self):
        self.game.change_scene(SettingsScene(self.game))

    def handle_event(self, event):
        for b in self.buttons: b.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill((20,25,35))
        if self.bg: surface.blit(self.bg, (0,0))
        for b in self.buttons: b.draw(surface)

class CharacterSelectScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        try:
            self.bg = pygame.image.load(TITLE_IMAGE).convert()
        except Exception:
            self.bg = None
        self.font_title = load_ui_font(32)
        self.font_btn   = load_ui_font(34)
        W, H = self.game.screen.get_size()
        BTN_W, BTN_H = int(W*0.30), int(H*0.10)
        GAP_X, GAP_Y = int(W*0.04), int(H*0.05)
        cx = W//2; y_top = int(H*0.70); y_bot = y_top + BTN_H + GAP_Y
        r_alumno = pygame.Rect(cx - BTN_W - GAP_X//2, y_top, BTN_W, BTN_H)
        r_maest  = pygame.Rect(cx + GAP_X//2,          y_top, BTN_W, BTN_H)
        r_colab  = pygame.Rect(cx - BTN_W - GAP_X//2,  y_bot, BTN_W, BTN_H)
        r_back   = pygame.Rect(cx + GAP_X//2,          y_bot, BTN_W, BTN_H)
        DARK = (160,0,50)
        hs = getattr(game, "hover_sfx", None)
        self.buttons = [
            Button(r_alumno, "ALUMNO",      self.font_btn, lambda: self.pick_role("ALUMNO"),
                   bg=(120,0,30), bg_hover=DARK, fg=(255,255,255), hover_sound=hs),
            Button(r_maest,  "MAESTRO",     self.font_btn, lambda: self.pick_role("MAESTRO"),
                   bg=(120,0,30), bg_hover=DARK, fg=(255,255,255), hover_sound=hs),
            Button(r_colab,  "COLABORADOR", self.font_btn, lambda: self.pick_role("COLABORADOR"),
                   bg=(120,0,30), bg_hover=DARK, fg=(255,255,255), hover_sound=hs),
            Button(r_back,   "REGRESAR",    self.font_btn, self.go_back,
                   bg=(120,0,30), bg_hover=DARK, fg=(255,255,255), hover_sound=hs),
        ]

    def pick_role(self, role):
        self.game.selected_role = role
        self.game.play_scene = PlayScene(self.game)
        self.game.change_scene(self.game.play_scene)

    def go_back(self):
        self.game.change_scene(MenuScene(self.game))

    def handle_event(self, event):
        for b in self.buttons: b.handle_event(event)

    def update(self, dt): pass

    def draw(self, surface):
        if self.bg: surface.blit(self.bg, (0,0))
        W, H = surface.get_size()
        t = self.font_title.render("ELIGE TU PERSONAJE", True, (255,255,255))
        surface.blit(t, t.get_rect(center=(W//2, int(H*0.62))))
        for b in self.buttons: b.draw(surface)

class SettingsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font = load_ui_font(36)
        self.font_small = load_ui_font(22)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_scene(MenuScene(self.game))

    def update(self, dt): pass

    def draw(self, surface):
        surface.fill((25,30,40))
        msg = self.font.render("AJUSTES (ESC para volver)", True, (240,240,240))
        surface.blit(msg, msg.get_rect(center=surface.get_rect().center))

# -------------------- GAME --------------------

class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        # tamaño ventana según portada
        win_size = (WIDTH, HEIGHT)
        try:
            tmp = pygame.image.load(TITLE_IMAGE)
            win_size = (tmp.get_width(), tmp.get_height())
        except Exception:
            pass

        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode(win_size)
        self.clock = pygame.time.Clock()

        # audio global (opcional)
        self.music_vol = 0.60
        self.sfx_vol   = 0.80
        try:
            if os.path.isfile(MUSIC_FILE):
                pygame.mixer.music.load(MUSIC_FILE)
                pygame.mixer.music.set_volume(self.music_vol)
                pygame.mixer.music.play(-1)
        except Exception:
            pass

        self.hover_sfx = None
        try:
            if os.path.isfile(HOVER_SFX):
                self.hover_sfx = pygame.mixer.Sound(HOVER_SFX)
                self.hover_sfx.set_volume(self.sfx_vol)
        except Exception:
            self.hover_sfx = None

        # estado global
        self.play_scene = None
        self.selected_role = None

        self.scene = None

    def change_scene(self, new_scene):
        self.scene = new_scene

    def run(self):
        while True:
            dt = self.clock.tick(FPS)/1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if self.scene:
                    self.scene.handle_event(event)
            if self.scene:
                self.scene.update(dt)
                self.scene.draw(self.screen)
            pygame.display.flip()

if __name__ == "__main__":
    game = Game()
    game.change_scene(MenuScene(game))
    game.run()
