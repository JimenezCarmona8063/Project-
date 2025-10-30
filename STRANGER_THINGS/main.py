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

from game.entities import (
    Player,
    NPC,
    Enemy,
    Item,
    Collector,
    Hunter,
    Builder,
    Guardian,
)
from game.dialogue import DialogueBox
from core.tilemap_tmx import TmxMap
from game.actions import ActionPlanner

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
        self.specialists = []

        visible_specs = [
            (Collector, "Sofía", (spawn_x + TILE * 2, spawn_y), True),
            (Hunter, "Diego", (spawn_x + TILE * 4, spawn_y), True),
            (Builder, "María", (spawn_x + TILE * 2, spawn_y + TILE * 2), True),
            (Guardian, "Valentín", (spawn_x + TILE * 4, spawn_y + TILE * 2), True),
            (Collector, "Elena", (spawn_x - TILE * 2, spawn_y + TILE * 2), True),
            (Builder, "Rafael", (spawn_x - TILE * 2, spawn_y), True),
            (Hunter, "Camila", (spawn_x + TILE * 6, spawn_y), True),
            (Guardian, "Lucía", (spawn_x + TILE * 6, spawn_y + TILE * 2), True),
        ]
        for cls, name, pos, visible in visible_specs:
            self.specialists.append(cls(pos[0], pos[1], name, visible=visible))

        extra_classes = [Collector, Hunter, Builder, Guardian]
        while len(self.specialists) < 60:
            idx = len(self.specialists)
            cls = extra_classes[idx % len(extra_classes)]
            name = f"{cls.__name__} Aux {idx+1}"
            self.specialists.append(cls(spawn_x, spawn_y, name, visible=False))
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
        self.message_text = ""
        self.message_timer = 0.0

        self.planner = ActionPlanner(self.specialists, self.map, player=self.player, max_parallel=64)
        self.decision_status = None
        self.font_overlay = load_ui_font(18)
        self.font_overlay_small = load_ui_font(16)
        if self.font_overlay is None:
            self.font_overlay = pygame.font.SysFont("arial", 18, bold=True)
        if self.font_overlay_small is None:
            self.font_overlay_small = pygame.font.SysFont("arial", 16)

    def handle_event(self, event):
        if self.dialogue:
            self.dialogue.handle_event(event)
            if self.dialogue.done:
                self.dialogue = None

    def update(self, dt):
        keys = keydict()
        if not self.dialogue:
            self.player.handle_input(keys)
        self.player.update(dt, self.map)
        player_room = self.map.room_for_rect(self.player.rect)
        self.player.current_room = player_room.get("name") if player_room else None

        for n in self.npcs:
            n.update(dt, self.map)
        for e in self.enemies:
            e.update(dt, self.map, self.player)
        for it in self.items:
            if not it.dead and self.player.rect.colliderect(it.rect):
                it.picked(self.player)
        self.items = [i for i in self.items if not i.dead]

        self.planner.set_player_room(self.player.current_room)
        self.planner.update(dt, self.map)
        for agent in self.specialists:
            if agent.current_action is None:
                agent.idle_step(dt, self.map)

        self.decision_status = self.planner.get_status_snapshot()

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message_text = ""

        if keys["interact"] and not self.interact_hold and not self.dialogue:
            self.interact_hold = True
            if self._try_enter_room():
                self.player.interact_cooldown = 0.6
            elif self._try_support_specialist():
                self.player.interact_cooldown = 0.6
            else:
                for n in self.npcs:
                    if self.player.rect.colliderect(n.rect.inflate(30,30)):
                        lines = self.scripts.get(n.script_id, ["..."])
                        if n.script_id == "npc_guard" and "Tarjeta de Acceso" in self.player.inventory:
                            lines = self.scripts.get("npc_congrats", ["Bien."])
                        self.dialogue = DialogueBox(lines, n.name)
                        break
        if not keys["interact"]:
            self.interact_hold = False

        self.camera.center_on(self.player.rect)

        if not self.message_text:
            near = self._nearest_specialist()
            if near:
                self._set_message(f"{near.name}: {near.status_text()}", 0.5)

    def draw(self, surface):
        surface.fill((15,15,20))
        self.map.draw(surface, self.camera)
        for it in self.items: it.draw(surface, self.camera)
        for n in self.npcs: n.draw(surface, self.camera)
        for agent in self.specialists: agent.draw(surface, self.camera)
        for e in self.enemies: e.draw(surface, self.camera)
        self.player.draw(surface, self.camera)
        draw_hud(surface, self.player, self.decision_status)
        self._draw_action_overlay(surface)
        if self.message_text:
            self._draw_message(surface)
        if self.dialogue: self.dialogue.draw(surface)

    def _nearest_specialist(self):
        best = None
        best_dist = None
        player_center = pygame.Vector2(self.player.rect.center)
        for agent in self.specialists:
            if not getattr(agent, "visible", False):
                continue
            dist = player_center.distance_to(pygame.Vector2(agent.rect.center))
            if dist < 120:
                if best is None or dist < best_dist:
                    best = agent
                    best_dist = dist
        return best

    def _set_message(self, text, duration=2.0):
        if not text:
            return
        self.message_text = text
        self.message_timer = max(duration, 0.1)

    def _try_support_specialist(self):
        for agent in self.specialists:
            if not getattr(agent, "visible", False):
                continue
            if agent.rect.colliderect(self.player.rect.inflate(50, 50)):
                msg = self.planner.boost_character(agent, helper=self.player)
                if msg:
                    self._set_message(msg)
                else:
                    self._set_message(f"{agent.name}: {agent.status_text()}")
                return True
        return False

    def _try_enter_room(self):
        door = self.map.door_for_rect(self.player.rect)
        if door:
            dest_name = door.get("dest")
            target_room = self.map.get_room(dest_name) or self.map.closest_room_to_rect(door.get("rect"))
            rect = target_room.get("rect") if target_room else None
            if rect and isinstance(rect, pygame.Rect):
                self.player.rect.center = rect.center
                self.player.current_room = target_room.get("name")
                self.planner.report_player_entered_room(self.player.current_room)
                self._set_message(f"Entraste a {self.player.current_room}")
                return True
        room = self.map.room_for_rect(self.player.rect)
        if room:
            self.player.current_room = room.get("name")
            self.planner.report_player_entered_room(self.player.current_room)
            self._set_message(f"Estás en {self.player.current_room}")
            return True
        return False

    def _draw_message(self, surface):
        msg_surf = self.font_overlay_small.render(self.message_text, True, (255, 255, 255))
        padding = 12
        bg = pygame.Surface((msg_surf.get_width() + padding * 2, msg_surf.get_height() + padding), pygame.SRCALPHA)
        bg.fill((10, 12, 20, 200))
        y = surface.get_height() - bg.get_height() - 20
        surface.blit(bg, (20, y))
        surface.blit(msg_surf, (20 + padding, y + (padding // 2)))

    def _draw_action_overlay(self, surface):
        if not self.decision_status:
            return
        panel_w, panel_h = 320, 220
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((15, 20, 32, 220))
        y = 12
        title = self.font_overlay.render("Planificador", True, (255, 255, 255))
        panel.blit(title, (12, y))
        y += title.get_height() + 6
        for entry in self.decision_status.get("active", [])[:6]:
            name, category, progress, from_event = entry
            pct = int(progress * 100)
            text = f"{name}: {category} {pct}%"
            if from_event:
                text += " (!)"
            line = self.font_overlay_small.render(text, True, (220, 230, 240))
            panel.blit(line, (12, y))
            y += line.get_height() + 2
        history = self.decision_status.get("history", [])
        if history:
            y += 4
            hist_title = self.font_overlay_small.render("Historial", True, (190, 200, 220))
            panel.blit(hist_title, (12, y))
            y += hist_title.get_height() + 2
            for entry in history:
                line = self.font_overlay_small.render(entry, True, (170, 180, 200))
                panel.blit(line, (16, y))
                y += line.get_height() + 1
                if y > panel_h - 18:
                    break
        surface.blit(panel, (surface.get_width() - panel_w - 18, 16))

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
