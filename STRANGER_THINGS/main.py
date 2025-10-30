# main.py — versión ordenada para evitar "MenuScene undefined"
import os, sys, json, random, math
from collections import deque
from typing import Callable, Optional

import pygame

from settings import (
    WIDTH, HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, FULLSCREEN,
    FPS, TILE, TITLE,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_INTERACT, KEY_INVENTORY,
    KEY_ACTION_RUSH, KEY_FIGHT, KEY_MESSAGE,
    DEFAULT_MAP_CSV, DIALOGUES_JSON, TITLE_IMAGE, UI_FONT_FILE,
    MUSIC_FILE, HOVER_SFX, DEFAULT_MUSIC_VOL, DEFAULT_SFX_VOL,
    WINE, WINE_HOV, RED, HUD_PANEL_WIDTH
)

from core.engine import Camera2D, Scene, draw_text
from game.ui import (
    draw_hud,
    draw_action_feed,
    Button,
    Slider,
    DecisionPrompt,
    ChatWindow,
)

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
        "rush": keys[getattr(pygame, "K_"+KEY_ACTION_RUSH)],
        "fight": keys[getattr(pygame, "K_"+KEY_FIGHT)],
        "message": keys[getattr(pygame, "K_"+KEY_MESSAGE)],
    }
    return kd

# -------------------- ESCENAS --------------------

class PlayScene(Scene):
    def __init__(self, game):
        super().__init__(game)

        # 1) Cargar TMX
        self.map = TmxMap()  # usa settings.TMX_MAP_FILE

        # 2) Cámara al tamaño del mapa sin el panel lateral y con zoom dinámico
        self.panel_width = HUD_PANEL_WIDTH
        self.bottom_feed_height = 180
        total_w = self.game.screen.get_width()
        total_h = self.game.screen.get_height()
        map_w = max(320, total_w - self.panel_width)
        map_h = max(240, total_h - self.bottom_feed_height)
        self.map_zoom = 1.18
        cam_w = max(160, int(map_w / self.map_zoom))
        cam_h = max(160, int(map_h / self.map_zoom))
        self.camera = Camera2D(*self.map.world_size(), cam_w, cam_h)
        self.map_view = pygame.Rect(self.panel_width, 0, map_w, map_h)
        self.action_feed_rect = pygame.Rect(self.panel_width, self.map_view.bottom, map_w, self.bottom_feed_height)
        self._map_buffer = pygame.Surface((self.camera.screen_w, self.camera.screen_h), pygame.SRCALPHA)


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

        world_w, world_h = self.map.world_size()
        room_spots = []
        for room in getattr(self.map, "rooms", []):
            rect = room.get("rect")
            if isinstance(rect, pygame.Rect):
                room_spots.append((rect.centerx, rect.centery))

        def clamp_pos(px: float, py: float) -> tuple[int, int]:
            return (
                max(TILE, min(world_w - TILE, int(px))),
                max(TILE, min(world_h - TILE, int(py))),
            )

        fallback_spots = [
            (spawn_x + TILE * 8, spawn_y),
            (spawn_x - TILE * 8, spawn_y + TILE * 3),
            (spawn_x + TILE * 4, spawn_y - TILE * 6),
            (spawn_x - TILE * 10, spawn_y - TILE * 2),
            (spawn_x + TILE * 10, spawn_y + TILE * 5),
            (spawn_x - TILE * 6, spawn_y + TILE * 6),
            (spawn_x + TILE * 2, spawn_y + TILE * 9),
            (spawn_x - TILE * 12, spawn_y + TILE * 2),
        ]
        available_spots = [clamp_pos(x, y) for (x, y) in (room_spots or fallback_spots)]
        random.shuffle(available_spots)

        def random_spot() -> tuple[int, int]:
            angle = random.uniform(0.0, math.tau)
            radius = random.uniform(4.0, 12.0) * TILE
            return clamp_pos(spawn_x + math.cos(angle) * radius, spawn_y + math.sin(angle) * radius)

        def ensure_spots(count: int) -> None:
            while len(available_spots) < count:
                available_spots.append(random_spot())

        def pull_spot() -> tuple[int, int]:
            ensure_spots(1)
            return available_spots.pop()

        self.npcs = [
            NPC(8 * TILE, 6 * TILE, "Profe", "npc_prof"),
            NPC(30 * TILE, 20 * TILE, "Guardia", "npc_guard"),
        ]
        npc_blueprints = [
            ("Ana", "npc_student_ana"),
            ("Jorge", "npc_student_jorge"),
            ("Coach", "npc_coach"),
            ("Luz", "npc_artist"),
            ("Mateo", "npc_scientist"),
            ("Rita", "npc_librarian"),
        ]
        ensure_spots(len(npc_blueprints) + 12)
        for name, script_id in npc_blueprints:
            x, y = pull_spot()
            self.npcs.append(NPC(x, y, name, script_id))
        self.enemies = [Enemy(20*TILE, 4*TILE), Enemy(34*TILE, 14*TILE)]
        self.items = [Item(25*TILE, 8*TILE, "Tarjeta de Acceso")]
        self.specialists = []

        specialist_templates = [
            (Collector, "Sofía"),
            (Hunter, "Diego"),
            (Builder, "María"),
            (Guardian, "Valentín"),
            (Collector, "Elena"),
            (Builder, "Rafael"),
            (Hunter, "Camila"),
            (Guardian, "Lucía"),
            (Collector, "Isabela"),
            (Hunter, "Andrés"),
            (Builder, "Iker"),
            (Guardian, "Claudia"),
        ]
        ensure_spots(len(specialist_templates) + 20)
        for cls, name in specialist_templates:
            x, y = pull_spot()
            self.specialists.append(cls(x, y, name, visible=True))

        extra_classes = [Collector, Hunter, Builder, Guardian]
        while len(self.specialists) < 120:
            idx = len(self.specialists)
            cls = extra_classes[idx % len(extra_classes)]
            name = f"{cls.__name__} Aux {idx+1}"
            visible = idx < 16
            px, py = (pull_spot() if visible else random_spot())
            self.specialists.append(cls(px, py, name, visible=visible))
        # diálogos
        default_scripts = {
            "npc_prof": [
                "¡Hey! Bienvenido a UP Adventure.",
                "Trae de la cafetería una *Tarjeta de Acceso* y vuelve conmigo.",
                "Con eso podrás entrar al laboratorio."
            ],
            "npc_guard": [
                "No puedes pasar sin Tarjeta de Acceso.",
                "Regresa cuando la tengas."
            ],
            "npc_congrats": ["¡Eso es! Ya puedes entrar al lab. ¡Suerte!"],
            "npc_student_ana": [
                "Estoy corriendo entre clases, ¿ya hiciste tu tarea?",
                "Dicen que si la saltas baja tu promedio rápido..."
            ],
            "npc_student_jorge": [
                "Hey, vamos al laboratorio juntos.",
                "Si no saludas a la banda luego se enojan."],
            "npc_coach": [
                "Entrenar también cuenta como tarea, ¡mueve esas piernas!",
                "Si te quedas quieto pierdes energía."],
            "npc_artist": [
                "¿Viste las exposiciones del salón de arte?",
                "Siempre hay algo nuevo pasando por aquí."],
            "npc_scientist": [
                "Recolecto datos para la próxima feria de ciencias.",
                "¿Me ayudas a conseguir materiales?"],
            "npc_librarian": [
                "Shh... pero acuérdate de entregar tus tareas a tiempo.",
                "Si no estudias, las calificaciones bajan."],
        }
        if not os.path.isfile(DIALOGUES_JSON):
            os.makedirs(os.path.dirname(DIALOGUES_JSON), exist_ok=True)
            with open(DIALOGUES_JSON, "w", encoding="utf-8") as f:
                json.dump(default_scripts, f, ensure_ascii=False, indent=2)
        with open(DIALOGUES_JSON, "r", encoding="utf-8") as f:
            self.scripts = json.load(f)
        for key, lines in default_scripts.items():
            self.scripts.setdefault(key, lines)
        self.dialogue = None
        self.interact_hold = False
        self.message_text = ""
        self.message_timer = 0.0

        self.planner = ActionPlanner(self.specialists, self.map, player=self.player, max_parallel=80)
        self.decision_status = None
        self.font_overlay = load_ui_font(18)
        self.font_overlay_small = load_ui_font(16)
        if self.font_overlay is None:
            self.font_overlay = pygame.font.SysFont("arial", 18, bold=True)
        if self.font_overlay_small is None:
            self.font_overlay_small = pygame.font.SysFont("arial", 16)
        self.decision_prompt: Optional[DecisionPrompt] = None
        self.chat_window: Optional[ChatWindow] = None
        self.chat_window_target: Optional[dict[str, object]] = None
        self.decision_option_map: dict[str, str] = {}
        self.player_tasks: list[dict[str, object]] = []
        self.random_task_timer = random.uniform(12.0, 22.0)
        self.greeting_timer = random.uniform(6.0, 12.0)
        self.active_greeting: Optional[dict[str, object]] = None
        self.food_prompt_active = False
        self.food_prompt_timer = 0.0
        self.food_prompt_cooldown = 6.0
        self.pending_food_task_key: Optional[str] = None
        self.pending_social_task_key: Optional[str] = None
        self.player_dead = False
        self.rush_cooldown = 0.0
        self.rush_hold = False
        self.fight_hold = False
        self.message_hold = False
        self.recent_task_sources: dict[str, float] = {}
        self.room_task_cooldowns: dict[str, float] = {}
        self.activity_markers: list[dict[str, object]] = []
        self.active_fight: Optional[dict[str, object]] = None
        self.activity_font = load_ui_font(16)
        if self.activity_font is None:
            self.activity_font = pygame.font.SysFont("arial", 16, bold=True)
        self.room_activity_map = self._build_room_activity_map()
        self.action_prompts: list[dict[str, object]] = []
        self.action_history: deque[dict[str, object]] = deque(maxlen=18)
        self.prompt_counter = 0
        self.hud_scroll = 0.0
        self.hud_scroll_max = 0.0
        self.controls_hint = "Controles: WASD moverte | E interactuar | Y/N responder | Q ráfaga | F pelea | M mensajes"
        self.minimap_scale = 0.12
        self.minimap_base = self._build_minimap_surface()
        self.minimap_rect = self.minimap_base.get_rect() if self.minimap_base else pygame.Rect(0, 0, 0, 0)

    def _build_minimap_surface(self) -> pygame.Surface:
        world_w, world_h = self.map.world_size()
        target = 240
        scale = min(self.minimap_scale, target / max(world_w, 1), target / max(world_h, 1))
        scale = max(0.06, min(0.25, scale))
        self.minimap_scale = scale
        width = max(80, int(world_w * scale))
        height = max(80, int(world_h * scale))
        base = pygame.Surface((width, height), pygame.SRCALPHA)
        base.fill((12, 16, 24, 220))
        for room in getattr(self.map, "rooms", []):
            rect = room.get("rect")
            if isinstance(rect, pygame.Rect):
                scaled = pygame.Rect(
                    int(rect.x * scale),
                    int(rect.y * scale),
                    max(2, int(rect.width * scale)),
                    max(2, int(rect.height * scale)),
                )
                pygame.draw.rect(base, (60, 90, 140, 180), scaled, border_radius=4)
        pygame.draw.rect(base, (22, 30, 42, 220), base.get_rect(), width=2, border_radius=8)
        return base

    def _ensure_map_surfaces(self, surface: pygame.Surface) -> None:
        map_width = max(320, surface.get_width() - self.panel_width)
        map_height = max(240, surface.get_height() - self.bottom_feed_height)
        if self.map_view.width != map_width or self.map_view.height != map_height:
            self.map_view.size = (map_width, map_height)
            self.action_feed_rect.topleft = (self.panel_width, self.map_view.bottom)
            self.action_feed_rect.size = (map_width, self.bottom_feed_height)
        buffer_w = max(160, int(self.map_view.width / self.map_zoom))
        buffer_h = max(160, int(self.map_view.height / self.map_zoom))
        if (
            self._map_buffer.get_width() != buffer_w
            or self._map_buffer.get_height() != buffer_h
        ):
            self.camera.screen_w = buffer_w
            self.camera.screen_h = buffer_h
            self.camera.clamp()
            self._map_buffer = pygame.Surface((buffer_w, buffer_h), pygame.SRCALPHA)

    def _push_action_prompt(
        self,
        text: str,
        options: Optional[list[dict[str, object]]] = None,
        duration: Optional[float] = 6.0,
        tag: Optional[str] = None,
        on_timeout: Optional[Callable[[], object]] = None,
    ) -> str:
        self.prompt_counter += 1
        prompt_id = f"P{self.prompt_counter}"
        entry: dict[str, object] = {
            "id": prompt_id,
            "text": text,
            "options": [],
            "timer": duration,
            "tag": tag,
            "on_timeout": on_timeout,
        }
        if options:
            for opt in options:
                opt_dict = dict(opt)
                keycode = opt_dict.get("key")
                if keycode and not opt_dict.get("display"):
                    opt_dict["display"] = pygame.key.name(keycode).upper()
                opt_dict["prompt_id"] = prompt_id
                entry["options"].append(opt_dict)
        self.action_prompts.insert(0, entry)
        return prompt_id

    def _remove_prompt_by_id(self, prompt_id: Optional[str]) -> None:
        if not prompt_id:
            return
        for prompt in list(self.action_prompts):
            if prompt.get("id") == prompt_id:
                self.action_prompts.remove(prompt)
                break

    def _log_action(self, message, color: Optional[tuple[int, int, int]] = None) -> None:
        if not message:
            return
        entry_color = color or (220, 220, 230)
        text = message
        if isinstance(message, tuple):
            text, entry_color = message
        if isinstance(text, (list, dict)):
            text = str(text)
        self.action_history.appendleft({"text": str(text), "color": entry_color})
        while len(self.action_history) > self.action_history.maxlen:
            self.action_history.pop()

    def _update_action_prompts(self, dt: float) -> None:
        if not self.action_prompts:
            return
        for prompt in list(self.action_prompts):
            timer = prompt.get("timer")
            if timer is None:
                continue
            timer = max(0.0, float(timer) - dt)
            prompt["timer"] = timer
            if timer <= 0:
                on_timeout = prompt.get("on_timeout")
                result = on_timeout() if callable(on_timeout) else None
                if result:
                    self._log_action(result)
                if prompt in self.action_prompts:
                    self.action_prompts.remove(prompt)

    def _handle_prompt_key(self, key: int) -> bool:
        handled_prompt = None
        handled_result = None
        for prompt in list(self.action_prompts):
            for option in prompt.get("options", []):
                if option.get("key") == key:
                    callback = option.get("callback")
                    if callable(callback):
                        handled_result = callback()
                    if not handled_result:
                        label = option.get("label")
                        if label:
                            handled_result = label
                    handled_prompt = prompt
                    break
            if handled_prompt:
                break
        if handled_prompt:
            if handled_result:
                self._log_action(handled_result)
            if handled_prompt in self.action_prompts:
                self.action_prompts.remove(handled_prompt)
            return True
        return False

    def _accept_auto_task(self, key: Optional[str]) -> str:
        if not key:
            return ""
        for task in self.player_tasks:
            if task.get("done"):
                continue
            if task.get("auto_key") == key or task.get("name") == key:
                task["accepted"] = True
                if not task.get("status") or task.get("status") in ("Pendiente", "Planificada"):
                    task["status"] = "Aceptada"
                task.pop("prompt_id", None)
                self.player.note_interaction(f"Aceptaste {task['name']}")
                self.player.adjust_relationship("Equipo", 2)
                return f"Aceptaste {task['name']}"
        return ""

    def _reject_auto_task(self, key: Optional[str]) -> str:
        if not key:
            return ""
        name = None
        for task in self.player_tasks:
            if task.get("auto_key") == key or task.get("name") == key:
                name = task.get("name")
                break
        self._complete_auto_task(key, False)
        if name:
            return f"Rechazaste {name}"
        return "Rechazaste la actividad"

    def _auto_task_timeout(self, key: Optional[str]) -> str:
        if not key:
            return ""
        for task in self.player_tasks:
            if task.get("done"):
                continue
            if task.get("auto_key") == key or task.get("name") == key:
                if task.get("accepted"):
                    return ""
                name = task.get("name")
                self._complete_auto_task(key, False)
                if name:
                    return f"Perdiste {name}"
                return "Perdiste una actividad"
        return ""

    def _resolve_greeting_choice(self, accept: bool, manual: bool = True) -> str:
        if not self.active_greeting:
            return ""
        agent = self.active_greeting.get("agent")
        if not agent:
            self.active_greeting = None
            return ""
        if accept:
            if agent.rect.colliderect(self.player.rect.inflate(60, 60)):
                return self._finish_greeting(agent, True, manual)
            self.active_greeting["pending_accept"] = True
            self.active_greeting["manual_accept"] = manual
            wait_text = f"Esperas a que {agent.name} llegue"
            self._set_message(wait_text, 1.4)
            return wait_text
        return self._finish_greeting(agent, False, manual)

    def _resolve_greeting_timeout(self) -> str:
        if not self.active_greeting:
            return ""
        agent = self.active_greeting.get("agent")
        if not agent:
            self.active_greeting = None
            return ""
        return self._finish_greeting(agent, False, manual=False)

    def _finish_greeting(self, agent, success: bool, manual: bool = True) -> str:
        if not agent:
            return ""
        if not self.active_greeting:
            return ""
        prompt_id = self.active_greeting.get("prompt_id")
        task_key = self.active_greeting.get("task_key")
        response = ""
        if success:
            self.active_greeting["responded"] = True
            self.player.resolve_greeting(agent.name, True)
            self.player.adjust_relationship(agent.name, 8)
            response = f"Saludaste a {agent.name}"
            self._set_message(response, 1.8)
            self._add_activity_marker(response, pos=agent.rect.center, color=(200, 220, 255))
            if self.pending_social_task_key and task_key == self.pending_social_task_key:
                self._complete_auto_task(task_key, True)
                self.pending_social_task_key = None
        else:
            self.player.resolve_greeting(agent.name, False)
            penalty = -4 if manual else -6
            self.player.adjust_relationship(agent.name, penalty)
            response = f"Ignoraste a {agent.name}"
            self._set_message(response, 1.8)
            if self.pending_social_task_key and task_key == self.pending_social_task_key:
                self._complete_auto_task(task_key, False)
                self.pending_social_task_key = None
        agent.clear_interaction_request()
        self.active_greeting = None
        if prompt_id:
            self._remove_prompt_by_id(prompt_id)
        return response

    def _draw_minimap(self, surface: pygame.Surface) -> None:
        if not self.minimap_base:
            return
        mini = self.minimap_base.copy()
        scale = self.minimap_scale
        for npc in self.npcs:
            pos = (int(npc.rect.centerx * scale), int(npc.rect.centery * scale))
            pygame.draw.circle(mini, (120, 170, 255), pos, 2)
        for agent in self.specialists:
            if getattr(agent, "visible", True):
                pos = (int(agent.rect.centerx * scale), int(agent.rect.centery * scale))
                pygame.draw.circle(mini, (130, 230, 180), pos, 2)
        pos_player = (int(self.player.rect.centerx * scale), int(self.player.rect.centery * scale))
        pygame.draw.circle(mini, (255, 255, 255), pos_player, 4)
        rect = mini.get_rect()
        rect.topright = (surface.get_width() - 24, 24)
        surface.blit(mini, rect.topleft)
        pygame.draw.rect(surface, (18, 24, 36), rect, width=2, border_radius=8)
        self.minimap_rect = rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if mx <= self.panel_width:
                self.hud_scroll = max(0.0, min(self.hud_scroll_max, self.hud_scroll - event.y * 40))
        if self.player_dead:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game.play_scene = None
                self.game.change_scene(MenuScene(self.game))
            return
        if (
            event.type == pygame.KEYDOWN
            and not self.dialogue
            and not self.decision_prompt
            and not self.chat_window
        ):
            if self._handle_prompt_key(event.key):
                return
        if self.chat_window:
            result = self.chat_window.handle_event(event)
            if result == "__cancel__":
                self.player.note_interaction("Cancelaste el mensaje")
                self._set_message("Mensaje cancelado", 1.0)
                self.chat_window_target = None
                self.chat_window = None
                return
            if result == "__closed__":
                self.chat_window_target = None
                self.chat_window = None
                return
            if isinstance(result, str):
                outcome = self._resolve_message_choice(result)
                if self.chat_window and outcome:
                    for entry in outcome.get("history", []):
                        self.chat_window.add_message(
                            entry.get("author", ""),
                            entry.get("text", ""),
                            entry.get("outbound", False),
                        )
                    self.chat_window.show_outcome(outcome.get("summary", []))
                elif outcome is None:
                    self.chat_window = None
                return
        if self.decision_prompt:
            self.decision_prompt.handle_event(event)
            if self.decision_prompt.finished:
                selection = self.decision_prompt.selection
                self.decision_prompt = None
                self._on_decision_selected(selection)
            return
        if self.dialogue:
            self.dialogue.handle_event(event)
            if self.dialogue.done:
                self.dialogue = None

    def update(self, dt):
        keys = keydict()
        if self.player_dead:
            if self.message_timer > 0:
                self.message_timer -= dt
                if self.message_timer <= 0:
                    self.message_text = ""
            return

        if self.rush_cooldown > 0:
            self.rush_cooldown = max(0.0, self.rush_cooldown - dt)
        for name in list(self.recent_task_sources.keys()):
            self.recent_task_sources[name] = max(0.0, self.recent_task_sources[name] - dt)
            if self.recent_task_sources[name] <= 0:
                # deja listo para una nueva misión al acercarse de nuevo
                self.recent_task_sources[name] = 0.0

        for room_name in list(self.room_task_cooldowns.keys()):
            self.room_task_cooldowns[room_name] = max(0.0, self.room_task_cooldowns[room_name] - dt)
            if self.room_task_cooldowns[room_name] <= 0:
                del self.room_task_cooldowns[room_name]

        if self.food_prompt_cooldown > 0:
            self.food_prompt_cooldown = max(0.0, self.food_prompt_cooldown - dt)
        if not self.dialogue and not self.decision_prompt and not self.chat_window:
            self.player.handle_input(keys)
        else:
            self.player.vx = 0.0
            self.player.vy = 0.0
        self.player.update(dt, self.map)
        player_room = self.map.room_for_rect(self.player.rect)
        self.player.current_room = player_room.get("name") if player_room else None
        self._maybe_activate_food_prompt(dt)

        if keys.get("rush"):
            if not self.rush_hold and self.rush_cooldown <= 0:
                summary = self.planner.trigger_mass_actions(100)
                if summary:
                    self._set_message(summary, 2.6)
                self.player.note_interaction("Activaste una ráfaga de coordinación")
                self.player.adjust_relationship("Equipo", 6)
                self.rush_cooldown = 9.0
            self.rush_hold = True
        else:
            self.rush_hold = False

        if keys.get("fight"):
            if not self.fight_hold and not self.decision_prompt and not self.dialogue and not self.chat_window:
                self._start_fight()
            self.fight_hold = True
        else:
            self.fight_hold = False

        if keys.get("message"):
            if not self.message_hold and not self.dialogue and not self.decision_prompt and not self.chat_window:
                self._open_message_prompt()
            self.message_hold = True
        else:
            self.message_hold = False

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
        self._update_player_tasks()
        self._update_random_events(dt)
        self._check_player_survival()
        self._update_fight(dt)
        self._tick_activity_markers(dt)
        self._update_action_prompts(dt)

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message_text = ""

        if keys["interact"] and not self.interact_hold and not self.dialogue and not self.decision_prompt and not self.chat_window:
            self.interact_hold = True
            handled = False
            if self.food_prompt_active and self._consume_food_prompt():
                handled = True
            elif self._handle_greeting_response():
                handled = True
            elif self._try_enter_room():
                handled = True
            elif self._try_support_specialist():
                handled = True
            else:
                for n in self.npcs:
                    if self.player.rect.colliderect(n.rect.inflate(30,30)):
                        lines = self.scripts.get(n.script_id, ["..."])
                        if n.script_id == "npc_guard" and "Tarjeta de Acceso" in self.player.inventory:
                            lines = self.scripts.get("npc_congrats", ["Bien."])
                        self.dialogue = DialogueBox(lines, n.name)
                        if n.script_id == "npc_guard" and "Tarjeta de Acceso" not in self.player.inventory:
                            self.player.adjust_relationship(n.name, -4)
                            self.player.note_interaction("Guardia desconfía")
                        else:
                            self.player.adjust_relationship(n.name, 6)
                            self.player.note_interaction(f"Conversaste con {n.name}")
                            if self.active_greeting and self.active_greeting.get("agent") is n:
                                self.active_greeting["responded"] = True
                                self.player.resolve_greeting(n.name, True)
                                n.clear_interaction_request()
                        handled = True
                        break
                if not handled and not self.dialogue:
                    self._open_decision_prompt()
                    handled = True
            if handled:
                self.player.interact_cooldown = 0.6
        if not keys["interact"]:
            self.interact_hold = False

        self.camera.center_on(self.player.rect)

        if not self.message_text:
            near = self._nearest_specialist()
            if near:
                self._set_message(f"{near.name}: {near.status_text()}", 0.5)

    def draw(self, surface):
        surface.fill((12, 14, 22))
        self._ensure_map_surfaces(surface)
        self.camera.center_on(self.player.rect)
        map_buffer = self._map_buffer
        map_buffer.fill((18, 20, 28, 255))
        self.map.draw(map_buffer, self.camera)
        for it in self.items:
            it.draw(map_buffer, self.camera)
        for n in self.npcs:
            n.draw(map_buffer, self.camera)
        for agent in self.specialists:
            agent.draw(map_buffer, self.camera)
        for e in self.enemies:
            e.draw(map_buffer, self.camera)
        self.player.draw(map_buffer, self.camera)
        self._draw_activity_markers(map_buffer)
        scaled_map = pygame.transform.smoothscale(map_buffer, self.map_view.size)
        surface.blit(scaled_map, self.map_view.topleft)
        self._draw_minimap(surface)
        max_scroll = draw_hud(surface, self.player, self.decision_status, self.player_tasks, scroll_offset=self.hud_scroll)
        self.hud_scroll_max = max_scroll
        if self.hud_scroll > self.hud_scroll_max:
            self.hud_scroll = self.hud_scroll_max
        draw_action_feed(surface, self.action_feed_rect, self.action_prompts, list(self.action_history), controls_hint=self.controls_hint)
        if self.decision_prompt:
            self.decision_prompt.draw(surface)
        if self.chat_window:
            self.chat_window.draw(surface)
        if self.message_text:
            self._draw_message(surface)
        if self.active_fight:
            self._draw_fight_banner(surface)
        if self.dialogue: self.dialogue.draw(surface)
        if self.player_dead:
            self._draw_game_over(surface)

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
                    self.player.adjust_relationship(agent.name, 6 if "Apoyaste" in msg else 3)
                    self.player.note_interaction(f"Ayudaste a {agent.name}")
                    self._add_activity_marker(f"Ayudando a {agent.name}", pos=agent.rect.center)
                else:
                    self._set_message(f"{agent.name}: {agent.status_text()}")
                    self.player.adjust_relationship(agent.name, 1)
                    self.player.note_interaction(f"Chequeaste a {agent.name}")
                    self._add_activity_marker(f"Revisión de {agent.name}", pos=agent.rect.center, color=(200, 240, 180))
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
                self.player.note_interaction(f"Entraste a {self.player.current_room}")
                return True
        room = self.map.room_for_rect(self.player.rect)
        if room:
            self.player.current_room = room.get("name")
            self.planner.report_player_entered_room(self.player.current_room)
            self._set_message(f"Estás en {self.player.current_room}")
            self.player.note_interaction(f"Estás en {self.player.current_room}")
            return True
        return False

    def _open_decision_prompt(self):
        current_room = self.player.current_room or "el campus"
        question = f"¿Qué quieres coordinar cerca de {current_room}?"
        options = [
            "Planear apoyo académico",
            "Montar un taller",
            "Armar plan de seguridad",
        ]
        self.decision_option_map = {
            "Planear apoyo académico": "Apoyo académico",
            "Montar un taller": "Montar taller",
            "Armar plan de seguridad": "Plan de seguridad",
        }
        self.decision_prompt = DecisionPrompt("Plan inmediato", question, options, self.font_overlay, self.font_overlay_small)

    def _on_decision_selected(self, selection: Optional[str]):
        if not selection:
            self._set_message("Decisión cancelada", 1.2)
            self.player.note_interaction("Decisión cancelada")
            self.player.adjust_relationship("Equipo", -2)
            return
        category = self.decision_option_map.get(selection, selection)
        action = self.planner.plan_player_choice(category, focus_room=self.player.current_room, helper=self.player)
        if action:
            entry = {
                "name": action.name,
                "category": action.category,
                "status": "Planificada",
                "done": False,
                "started": False,
            }
            self.player_tasks.append(entry)
            self.player.adjust_relationship("Equipo", 4)
            self.player.note_interaction(f"Ordenaste {action.category.lower()}")
            self._set_message(f"Planificado: {action.name}")
            self._add_activity_marker(f"Plan: {action.category}")
        else:
            self._set_message("No hay recursos para esa decisión", 2.0)
            self.player.note_interaction("Plan fallido")
            self.player.adjust_relationship("Equipo", -3)

    def _update_player_tasks(self):
        if not self.player_tasks or not self.decision_status:
            return
        active_info = {}
        for char_name, action_name, category, progress, from_event in self.decision_status.get("active", []):
            active_info[action_name] = (char_name, progress, from_event)
        history = self.decision_status.get("history", [])
        for task in self.player_tasks:
            if task.get("done"):
                continue
            name = task["name"]
            if task.get("auto") and task.get("planner_category"):
                if name in active_info:
                    char_name, progress, _ = active_info[name]
                    task["status"] = f"{char_name}: {int(progress * 100)}%"
                    task["started"] = True
                    continue
                if any(f"inició {name}" in h for h in history):
                    task["status"] = "Asignada"
                    task["started"] = True
                    continue
                if any(f"completó {name}" in h for h in history):
                    self._complete_auto_task(task.get("auto_key") or name, True)
                    continue
                continue
            if name in active_info:
                char_name, progress, _ = active_info[name]
                task["status"] = f"{char_name}: {int(progress * 100)}%"
                task["started"] = True
                continue
            if any(f"inició {name}" in h for h in history):
                task["status"] = "Asignada"
                task["started"] = True
                continue
            if any(f"completó {name}" in h for h in history):
                task["status"] = "Completada"
                task["done"] = True
                self.player.adjust_relationship("Equipo", 5)
                self.player.note_interaction(f"{name} completada")

    def _update_random_events(self, dt: float):
        active_names = set()
        if self.decision_status:
            for _, action_name, _, _, _ in self.decision_status.get("active", []):
                active_names.add(action_name)
        proximity_triggered = self._check_proximity_task_spawn()
        if proximity_triggered:
            self.random_task_timer = random.uniform(16.0, 24.0)
        else:
            self.random_task_timer -= dt
            if self.random_task_timer <= 0:
                room_source = self.player.current_room
                self._spawn_random_task(source_name=room_source, focus_room=room_source)
                self.random_task_timer = random.uniform(18.0, 30.0)

        if self.greeting_timer > 0:
            self.greeting_timer -= dt
        if self.greeting_timer <= 0:
            self._trigger_random_greeting()
            self.greeting_timer = random.uniform(8.0, 16.0)

        if self.active_greeting:
            self.active_greeting["timer"] -= dt
            agent = self.active_greeting.get("agent")
            if self.active_greeting.get("pending_accept") and agent:
                if agent.rect.colliderect(self.player.rect.inflate(60, 60)):
                    manual = bool(self.active_greeting.get("manual_accept", True))
                    result = self._finish_greeting(agent, True, manual=manual)
                    if result:
                        self._log_action(result)
            elif self.active_greeting["timer"] <= 0 or not agent:
                result = self._resolve_greeting_timeout()
                if result:
                    self._log_action(result)

        if self.food_prompt_active:
            self.food_prompt_timer -= dt
            if self.food_prompt_timer <= 0:
                self.food_prompt_active = False
                self.food_prompt_cooldown = 10.0
                if self.pending_food_task_key:
                    self._complete_auto_task(self.pending_food_task_key, False)
                    self.pending_food_task_key = None

        expired: list[dict[str, object]] = []
        for task in self.player_tasks:
            if not task.get("auto") or task.get("done"):
                continue
            if task.get("timer") is None:
                continue
            if task.get("planner_category") and task.get("name") in active_names:
                continue
            task["timer"] = float(task.get("timer", 0.0)) - dt
            if task["timer"] <= 0:
                expired.append(task)
        for task in expired:
            key = task.get("auto_key") or task.get("name")
            self._complete_auto_task(key, False)

    def _spawn_random_task(self, source_name: Optional[str] = None, focus_room: Optional[str] = None):
        templates = self._templates_for_room(focus_room)
        if not templates:
            templates = self._templates_for_room(None)
        template = random.choice(templates)
        entry: dict[str, object] = {
            "name": template["name"],
            "status": "Pendiente",
            "done": False,
            "started": False,
            "auto": True,
            "timer": random.uniform(24.0, 40.0),
            "penalty": template.get("penalty", 8),
            "reward": template.get("reward", {}),
            "auto_key": template.get("name"),
            "room": focus_room,
        }
        if template.get("planner_category"):
            action = self.planner.plan_player_choice(
                template["planner_category"],
                focus_room=focus_room or self.player.current_room,
                helper=self.player,
            )
            if action:
                entry["name"] = action.name
                entry["auto_key"] = action.name
                entry["planner_category"] = template["planner_category"]
                entry["status"] = "Planificada"
            else:
                entry["status"] = "Esperando recursos"
                entry["timer"] = random.uniform(20.0, 35.0)
        if source_name:
            entry["origin"] = source_name
            if entry.get("status") == "Planificada":
                entry["status"] = f"{source_name} coordina"
        self.player_tasks.append(entry)
        self._log_action(f"Nueva actividad: {entry['name']}")
        if source_name:
            if focus_room and source_name == focus_room:
                alert = f"Actividades en {source_name}: {entry['name']}"
            else:
                alert = f"{source_name} propone: {entry['name']}"
            self.player.push_alert(alert)
            self.player.note_interaction(f"{source_name} pidió ayuda")
            self._set_message(alert, 2.8)
        else:
            self.player.push_alert(f"Nueva tarea: {entry['name']}")
            self.player.note_interaction(f"Nueva tarea: {entry['name']}")
            self._set_message(f"¡Nueva misión!: {entry['name']}", 2.6)
        if template.get("type") == "food":
            self.pending_food_task_key = entry["auto_key"]
            self._activate_food_prompt(force=True)
        elif template.get("type") == "social":
            self.pending_social_task_key = entry["auto_key"]
            self._trigger_random_greeting(force=True, task_key=entry["auto_key"])
        marker_color = (200, 220, 255) if focus_room else (245, 240, 200)
        self._add_activity_marker(entry["name"], pos=pygame.Vector2(self.player.rect.center), color=marker_color)
        if entry.get("auto"):
            auto_key = entry.get("auto_key")
            prompt_id = self._push_action_prompt(
                text=f"¿Ayudar con {entry['name']}?",
                options=[
                    {"key": pygame.K_y, "display": "Y", "label": "Aceptar", "callback": lambda key=auto_key: self._accept_auto_task(key)},
                    {"key": pygame.K_n, "display": "N", "label": "Rechazar", "callback": lambda key=auto_key: self._reject_auto_task(key)},
                ],
                duration=8.0,
                tag="task",
                on_timeout=lambda key=auto_key: self._auto_task_timeout(key),
            )
            entry["prompt_id"] = prompt_id
        return entry

    def _check_proximity_task_spawn(self) -> bool:
        player_center = pygame.Vector2(self.player.rect.center)
        closest: Optional[tuple[object, float]] = None
        for npc in self.npcs:
            dist = player_center.distance_to(pygame.Vector2(npc.rect.center))
            if dist <= 150:
                if closest is None or dist < closest[1]:
                    closest = (npc, dist)
        for agent in self.specialists:
            if not getattr(agent, "visible", True):
                continue
            dist = player_center.distance_to(pygame.Vector2(agent.rect.center))
            if dist <= 160:
                if closest is None or dist < closest[1]:
                    closest = (agent, dist)
        if not closest:
            player_room = self.player.current_room
            if player_room:
                cooldown = self.room_task_cooldowns.get(player_room, 0.0)
                if cooldown <= 0.0:
                    self._spawn_random_task(source_name=player_room, focus_room=player_room)
                    self.room_task_cooldowns[player_room] = random.uniform(22.0, 32.0)
                    return True
            return False
        entity, _ = closest
        name = getattr(entity, "name", "Alumno")
        cooldown = self.recent_task_sources.get(name, 0.0)
        if cooldown > 0.0:
            return False
        room = self.map.room_for_rect(entity.rect)
        room_name = room.get("name") if room else None
        self._spawn_random_task(source_name=name, focus_room=room_name)
        self.recent_task_sources[name] = random.uniform(18.0, 28.0)
        if room_name:
            self.room_task_cooldowns[room_name] = random.uniform(16.0, 24.0)
        return True

    def _activate_food_prompt(self, force: bool = False) -> None:
        if self.food_prompt_active:
            return
        if not force:
            if self.player.hunger > 40:
                return
            if self.food_prompt_cooldown > 0:
                return
        self.food_prompt_active = True
        self.food_prompt_timer = 12.0
        self.food_prompt_cooldown = 6.0
        self.player.push_alert("Presiona E para comer ahora")
        self._set_message("Tienes hambre. Pulsa E para comer.", 2.8)

    def _maybe_activate_food_prompt(self, dt: float) -> None:
        if self.food_prompt_active:
            return
        if self.player.hunger <= 32 and self.food_prompt_cooldown <= 0:
            self._activate_food_prompt()

    def _consume_food_prompt(self) -> bool:
        if not self.food_prompt_active:
            return False
        self.food_prompt_active = False
        self.food_prompt_timer = 0.0
        self.food_prompt_cooldown = 20.0
        self.player.restore_hunger(45.0)
        self.player.adjust_grades(+2.0)
        self.player.note_interaction("Tomaste un snack energético")
        self._set_message("Comiste algo rápido", 1.6)
        self._add_activity_marker("Snack rápido")
        if self.pending_food_task_key:
            self._complete_auto_task(self.pending_food_task_key, True)
            self.pending_food_task_key = None
        return True

    def _handle_greeting_response(self) -> bool:
        if not self.active_greeting or self.active_greeting.get("responded"):
            return False
        result = self._resolve_greeting_choice(True, manual=True)
        if result:
            self._log_action(result)
            return True
        return False

    def _trigger_random_greeting(self, force: bool = False, task_key: Optional[str] = None) -> None:
        if self.active_greeting:
            return
        candidates = []
        for npc in self.npcs:
            if not force:
                if abs(npc.rect.centerx - self.player.rect.centerx) > 360:
                    continue
                if abs(npc.rect.centery - self.player.rect.centery) > 260:
                    continue
            candidates.append(npc)
        for agent in self.specialists:
            if not getattr(agent, "visible", True):
                continue
            if agent.current_action is not None and not force:
                continue
            if force or pygame.Vector2(agent.rect.center).distance_to(self.player.rect.center) < 420:
                candidates.append(agent)
        if not candidates:
            return
        greeter = random.choice(candidates)
        greeter.request_interaction(lambda: self.player.rect.center, duration=6.0)
        prompt_id = self._push_action_prompt(
            text=f"{greeter.name} te saluda",
            options=[
                {"key": pygame.K_y, "display": "Y", "label": "Saludar", "callback": lambda: self._resolve_greeting_choice(True, manual=True)},
                {"key": pygame.K_n, "display": "N", "label": "Ignorar", "callback": lambda: self._resolve_greeting_choice(False, manual=True)},
            ],
            duration=6.0,
            tag="greeting",
            on_timeout=self._resolve_greeting_timeout,
        )
        self.active_greeting = {
            "agent": greeter,
            "timer": 6.0,
            "responded": False,
            "task_key": task_key,
            "prompt_id": prompt_id,
            "pending_accept": False,
        }
        self.player.begin_greeting(greeter.name)
        self.player.note_interaction(f"{greeter.name} te saludó")
        self._log_action(f"{greeter.name} te saluda")
        self._set_message(f"{greeter.name} se acerca a saludarte", 2.5)
        self.greeting_timer = random.uniform(10.0, 18.0)

    def _complete_auto_task(self, key: Optional[str], success: bool) -> None:
        if not key:
            return
        for task in self.player_tasks:
            if task.get("done"):
                continue
            matches = task.get("auto_key") == key or task.get("name") == key
            if not matches:
                continue
            task["done"] = True
            reward = task.get("reward", {})
            penalty = float(task.get("penalty", 8))
            if success:
                task["status"] = "Completada"
                task["started"] = True
                if "grades" in reward:
                    self.player.adjust_grades(float(reward["grades"]))
                if "social" in reward:
                    self.player.adjust_social(float(reward["social"]))
                if "hunger" in reward:
                    self.player.restore_hunger(float(reward["hunger"]))
                self.player.adjust_relationship("Equipo", 5)
                self.player.note_interaction(f"Tarea {task['name']} completada")
                self._add_activity_marker(f"✔ {task['name']}")
                self._log_action((f"Completada: {task['name']}", (140, 220, 160)))
            else:
                task["status"] = "Fallida"
                task["started"] = True
                self.player.adjust_grades(-penalty * 0.6)
                self.player.adjust_social(-penalty * 0.3)
                self.player.take_damage(penalty * 0.2)
                self.player.push_alert(f"Fallaste {task['name']}")
                self.player.note_interaction(f"Perdiste la tarea {task['name']}")
                self._add_activity_marker(f"✖ {task['name']}", color=(255, 120, 120))
                self._log_action((f"Fallida: {task['name']}", (240, 150, 150)))
            prompt_id = task.pop("prompt_id", None)
            if prompt_id:
                self._remove_prompt_by_id(prompt_id)
            return

    def _check_player_survival(self) -> None:
        if self.player_dead:
            return
        if getattr(self.player, "hp", 0) <= 0:
            self.player_dead = True
            self.dialogue = None
            self.decision_prompt = None
            self._set_message("Te desplomaste por agotamiento", 4.5)
            self.player.note_interaction("La jornada terminó por agotamiento")
            self.planner.history.prepend("El jugador colapsó por fatiga")
    def _draw_message(self, surface):
        msg_surf = self.font_overlay_small.render(self.message_text, True, (255, 255, 255))
        padding = 12
        bg = pygame.Surface((msg_surf.get_width() + padding * 2, msg_surf.get_height() + padding), pygame.SRCALPHA)
        bg.fill((10, 12, 20, 200))
        area_top = self.action_feed_rect.top if hasattr(self, "action_feed_rect") else surface.get_height()
        y = area_top - bg.get_height() - 16
        x = self.panel_width + 20
        surface.blit(bg, (x, y))
        surface.blit(msg_surf, (x + padding, y + (padding // 2)))

    def _draw_game_over(self, surface):
        width = surface.get_width() - self.panel_width
        overlay = pygame.Surface((width, surface.get_height()), pygame.SRCALPHA)
        overlay.fill((12, 8, 8, 180))
        surface.blit(overlay, (self.panel_width, 0))
        title = self.font_overlay.render("Juego terminado", True, (240, 80, 80))
        subtitle = self.font_overlay_small.render("Presiona ESC para volver al menú", True, (245, 245, 245))
        center_x = self.panel_width + width // 2
        surface.blit(title, title.get_rect(center=(center_x, surface.get_height() // 2 - 24)))
        surface.blit(subtitle, subtitle.get_rect(center=(center_x, surface.get_height() // 2 + 12)))

    def _tick_activity_markers(self, dt: float) -> None:
        if not self.activity_markers:
            return
        remaining: list[dict[str, object]] = []
        for marker in self.activity_markers:
            marker["timer"] -= dt
            if marker["timer"] <= 0:
                continue
            pos = marker.get("pos")
            if isinstance(pos, pygame.Vector2):
                marker["pos"] = pos + pygame.Vector2(0, -12 * dt)
            remaining.append(marker)
        self.activity_markers = remaining[-24:]

    def _add_activity_marker(self, text: str, pos=None, color=(245, 240, 180)) -> None:
        if not text or self.activity_font is None:
            return
        vector = pygame.Vector2(self.player.rect.center) if pos is None else pygame.Vector2(pos)
        marker = {"text": text, "pos": vector, "timer": 3.2, "color": color}
        self.activity_markers.append(marker)
        if len(self.activity_markers) > 24:
            self.activity_markers = self.activity_markers[-24:]

    def _draw_activity_markers(self, surface: pygame.Surface) -> None:
        if not self.activity_markers or self.activity_font is None:
            return
        for marker in self.activity_markers:
            pos: pygame.Vector2 = marker.get("pos", pygame.Vector2(self.player.rect.center))
            rect = pygame.Rect(int(pos.x) - 6, int(pos.y) - 6, 12, 12)
            screen_rect = self.camera.apply(rect)
            label = marker.get("text", "")
            color = marker.get("color", (255, 255, 255))
            text_surf = self.activity_font.render(label, True, color)
            bg = pygame.Surface((text_surf.get_width() + 6, text_surf.get_height() + 4), pygame.SRCALPHA)
            bg.fill((12, 16, 24, 170))
            surface.blit(bg, (screen_rect.x - 2, screen_rect.y - 28))
            surface.blit(text_surf, (screen_rect.x + 1, screen_rect.y - 26))

    def _update_fight(self, dt: float) -> None:
        if not self.active_fight:
            return
        target = self.active_fight.get("target")
        if target and getattr(target, "dead", False):
            self.active_fight = None
            return
        phase = self.active_fight.get("phase", "windup")
        self.active_fight["timer"] -= dt
        if phase == "windup" and self.active_fight["timer"] <= 0:
            self._resolve_fight()
        elif phase == "cooldown" and self.active_fight["timer"] <= 0:
            self.active_fight = None

    def _start_fight(self) -> None:
        if self.active_fight:
            self._set_message("Ya estás en una pelea", 1.2)
            return
        target_info = self._nearest_fight_target()
        if not target_info:
            self._set_message("No hay nadie cerca para pelear", 1.4)
            return
        target, _ = target_info
        name = getattr(target, "name", "Adversario")
        if hasattr(target, "request_interaction"):
            target.request_interaction(lambda: self.player.rect.center, duration=6.0)
        self.player.add_social_message(name, "¿Qué pasa? ¿Quieres problemas?")
        self.player.adjust_social(-6)
        self.player.adjust_relationship(name, -5)
        self.player.note_interaction(f"Iniciaste una pelea con {name}")
        self.player.push_alert(f"Pelea iniciada con {name}")
        self._add_activity_marker(f"Pelea con {name}")
        self.active_fight = {
            "target": target,
            "name": name,
            "timer": 2.6,
            "phase": "windup",
            "text": "",
            "result": "",
        }

    def _resolve_fight(self) -> None:
        if not self.active_fight:
            return
        name = self.active_fight.get("name", "Adversario")
        target = self.active_fight.get("target")
        roll = random.random()
        if roll < 0.45:
            self.active_fight["result"] = "derrota"
            self.active_fight["text"] = f"{name} te supera"
            self.player.take_damage(10.0)
            self.player.adjust_social(-8)
            self.player.adjust_relationship(name, -8)
            self.player.add_social_message(name, random.choice([
                "Te dije que no te metieras conmigo",
                "Tranquilo, pero piensa dos veces antes de pelear",
            ]))
            self._add_activity_marker(f"Perdiste contra {name}", color=(255, 110, 110))
        else:
            self.active_fight["result"] = "victoria"
            self.active_fight["text"] = f"Dominas a {name}"
            self.player.adjust_social(+6)
            self.player.adjust_relationship(name, -3)
            self.player.note_interaction(f"Ganaste la pelea con {name}")
            if target and hasattr(target, "take_damage"):
                target.take_damage(12.0)
            self.player.add_social_message(name, random.choice([
                "Está bien, ganaste esta vez...",
                "Ok, respeto tu determinación",
            ]))
            self._add_activity_marker(f"Ganaste a {name}", color=(255, 200, 140))
        if target and hasattr(target, "clear_interaction_request"):
            target.clear_interaction_request()
        self.active_fight["phase"] = "cooldown"
        self.active_fight["timer"] = 2.8

    def _draw_fight_banner(self, surface: pygame.Surface) -> None:
        if not self.active_fight or self.font_overlay_small is None:
            return
        phase = self.active_fight.get("phase", "windup")
        name = self.active_fight.get("name", "Adversario")
        timer = max(0.0, self.active_fight.get("timer", 0.0))
        if phase == "windup":
            color = (210, 120, 40, 180)
            text = f"Pelea con {name}: resolviendo en {timer:0.1f}s"
        else:
            result = self.active_fight.get("result")
            color = (180, 40, 40, 180) if result == "derrota" else (60, 170, 100, 180)
            text = self.active_fight.get("text") or f"Pelea con {name} resuelta"
        width = surface.get_width() - self.panel_width
        banner = pygame.Surface((width, 46), pygame.SRCALPHA)
        banner.fill(color)
        text_surf = self.font_overlay_small.render(text, True, (255, 255, 255))
        surface.blit(banner, (self.panel_width, 12))
        surface.blit(text_surf, (self.panel_width + 16, 22))

    def _nearest_fight_target(self):
        player_center = pygame.Vector2(self.player.rect.center)
        best = None
        best_dist = None
        candidates = list(self.npcs) + list(self.enemies)
        candidates += [agent for agent in self.specialists if getattr(agent, "visible", True)]
        for entity in candidates:
            center = pygame.Vector2(entity.rect.center)
            dist = player_center.distance_to(center)
            if dist <= 180:
                if best is None or dist < best_dist:
                    best = entity
                    best_dist = dist
        if best is None:
            return None
        return best, best_dist

    def _open_message_prompt(self) -> None:
        target = self._choose_message_target()
        if not target:
            self._set_message("No tienes a quién enviar mensaje ahora", 1.4)
            return
        self.chat_window_target = target
        name = target["name"]
        question = f"¿Qué mensaje envías a {name}?"
        options = [
            "Enviar mensaje motivador",
            "Mandar chisme divertido",
            "Pedir ayuda con tarea",
            "Invitar a comer después",
        ]
        self.chat_window = ChatWindow(
            "Red social",
            name,
            question,
            options,
            self.font_overlay,
            self.font_overlay_small,
        )
        saludo = random.choice([
            "¡Hola! Justo estaba pensando en ti.",
            "Hey, ¿cómo va tu día?",
            "¿Listo para las actividades de hoy?",
            "¿Qué tal todo por el campus?",
        ])
        self.chat_window.add_message(name, saludo)

    def _resolve_message_choice(self, selection: Optional[str]) -> Optional[dict[str, object]]:
        target = self.chat_window_target
        self.chat_window_target = None
        if not selection or not target:
            self._set_message("Mensaje cancelado", 1.0)
            self.player.note_interaction("Cancelaste el mensaje")
            return None
        name = target["name"]
        entity = target.get("entity")
        response = ""
        out_text = ""
        summary_lines: list[str] = []
        if selection == "Enviar mensaje motivador":
            out_text = "¡Tú puedes con los pendientes de hoy!"
            response = random.choice([
                "Gracias, justo necesitaba ese ánimo",
                "¡Eso! Ahora sí voy motivado",
            ])
            self.player.adjust_social(+6)
            self.player.adjust_relationship(name, +5)
            self.player.note_interaction(f"Animaste a {name}")
            summary_lines.append("Motivaste a tu contacto (+ánimo social)")
        elif selection == "Mandar chisme divertido":
            out_text = "¿Supiste lo que pasó en la cafetería?"
            if random.random() < 0.45:
                response = random.choice([
                    "No estoy para chismes ahora",
                    "Mejor concéntrate en tus tareas",
                ])
                self.player.adjust_social(-4)
                self.player.adjust_relationship(name, -3)
                self.player.take_damage(1.0)
                summary_lines.append("El chisme salió mal (-relación, -ánimo)")
            else:
                response = random.choice([
                    "Jajaja, cuéntame más",
                    "¡Qué risa! Gracias por avisar",
                ])
                self.player.adjust_social(+4)
                self.player.adjust_relationship(name, +2)
                summary_lines.append("Compartiste una anécdota divertida (+vida social)")
        elif selection == "Pedir ayuda con tarea":
            out_text = "¿Me compartes tus apuntes para la tarea?"
            if random.random() < 0.3:
                response = random.choice([
                    "Lo siento, aún no la termino",
                    "Estoy ocupado, luego te aviso",
                ])
                self.player.adjust_social(-2)
                self.player.adjust_relationship(name, -2)
                self.player.note_interaction(f"{name} no pudo ayudarte")
                summary_lines.append("No recibiste apoyo esta vez (-relación)")
            else:
                response = random.choice([
                    "Claro, te los mando en un rato",
                    "Sí, veamos después de clases",
                ])
                self.player.adjust_social(+5)
                self.player.adjust_relationship(name, +4)
                self.player.adjust_grades(+3)
                summary_lines.append("Conseguirás apuntes frescos (+calificaciones)")
        elif selection == "Invitar a comer después":
            out_text = "¿Vamos a comer algo después de clase?"
            if random.random() < 0.2:
                response = random.choice([
                    "No puedo, tengo mil pendientes",
                    "Hoy no, quizá mañana",
                ])
                self.player.adjust_social(-2)
                self.player.adjust_relationship(name, -2)
                summary_lines.append("La invitación no se concretó (-relación)")
            else:
                response = random.choice([
                    "¡Sí! Me hace falta un descanso",
                    "Va, nos vemos en la cafetería",
                ])
                self.player.adjust_social(+6)
                self.player.adjust_relationship(name, +3)
                self.player.restore_hunger(+10)
                summary_lines.append("Planearon comer juntos (+hambre, +vida social)")
        else:
            self._set_message("Mensaje sin enviar", 1.0)
            return None

        self.player.add_social_message(name, out_text, outbound=True)
        conversation = [{"author": "Tú", "text": out_text, "outbound": True}]
        if response:
            self.player.add_social_message(name, response)
            self.player.push_alert(f"{name}: {response}")
            conversation.append({"author": name, "text": response, "outbound": False})
            summary_lines.insert(0, f"{name}: {response}")
        else:
            summary_lines.insert(0, f"{name} vio tu mensaje")
        if entity and hasattr(entity, "request_interaction"):
            entity.request_interaction(lambda: self.player.rect.center, duration=4.0)
        self._set_message(f"Mensaje enviado a {name}", 1.8)
        self._add_activity_marker(f"Mensaje a {name}")
        summary_lines.append("Pulsa ENTER para cerrar el chat")
        return {"history": conversation, "summary": summary_lines}

    def _choose_message_target(self) -> Optional[dict[str, object]]:
        player_center = pygame.Vector2(self.player.rect.center)
        best = None
        best_dist = None
        for entity in list(self.npcs) + [agent for agent in self.specialists if getattr(agent, "visible", True)]:
            center = pygame.Vector2(entity.rect.center)
            dist = player_center.distance_to(center)
            if dist <= 480:
                if best is None or dist < best_dist:
                    best = entity
                    best_dist = dist
        if best:
            return {"name": getattr(best, "name", "Contacto"), "entity": best}
        top = self.player.top_relationships(1)
        if top:
            return {"name": top[0][0], "entity": None}
        if self.npcs:
            npc = random.choice(self.npcs)
            return {"name": npc.name, "entity": npc}
        return None

    def _build_room_activity_map(self) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {}
        for room in getattr(self.map, "rooms", []):
            name = room.get("name")
            if not name:
                continue
            tags = set(tag.lower() for tag in room.get("tags", []))
            layer_name = (room.get("layer") or "").lower()
            tags.update(layer_name.replace("-", " ").replace("_", " ").split())
            for token in name.lower().replace("-", " ").replace("_", " ").split():
                if len(token) >= 3:
                    tags.add(token)
            props = room.get("props") or {}
            for key in ("category", "focus", "tema", "type", "area"):
                value = props.get(key)
                if isinstance(value, str):
                    for part in value.replace("/", " ").replace(",", " ").split():
                        token = part.strip().lower()
                        if len(token) >= 3:
                            tags.add(token)
            mapping[name] = tags
        return mapping

    def _room_tags(self, room_name: Optional[str]) -> set[str]:
        if not room_name:
            return set()
        tags = set(self.room_activity_map.get(room_name, set()))
        if not tags and hasattr(self.map, "room_tags"):
            tags.update(tag.lower() for tag in self.map.room_tags(room_name))
        return tags

    def _templates_for_room(self, room_name: Optional[str]) -> list[dict[str, object]]:
        base = [
            {"name": "Apoyo académico urgente", "planner_category": "Apoyo académico", "penalty": 10, "reward": {"grades": 5}},
            {"name": "Montar taller relámpago", "planner_category": "Montar taller", "penalty": 9, "reward": {"grades": 3, "social": 4}},
            {"name": "Plan rápido de seguridad", "planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 4}},
            {"name": "Comer algo rápido", "type": "food", "penalty": 8, "reward": {"hunger": 35}},
            {"name": "Charla con aliados", "type": "social", "penalty": 9, "reward": {"social": 9}},
        ]

        templates = [dict(tpl) for tpl in base]
        tags = self._room_tags(room_name)

        def with_room(title: str, payload: dict[str, object]) -> dict[str, object]:
            tpl = dict(payload)
            tpl["name"] = title if not room_name else f"{title} en {room_name}"
            return tpl

        if tags:
            if any(tag in tags for tag in ("cafeteria", "comedor", "food", "cafe")):
                templates.append(with_room("Break en la cafetería", {"type": "food", "penalty": 7, "reward": {"hunger": 40, "social": 4}}))
                templates.append(with_room("Servicio de bandejas", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 5}}))
            if any(tag in tags for tag in ("laboratorio", "lab", "ciencia", "ingenieria")):
                templates.append(with_room("Experimento guiado", {"planner_category": "Apoyo académico", "penalty": 8, "reward": {"grades": 6}}))
                templates.append(with_room("Mantenimiento seguro", {"planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 3}}))
            if any(tag in tags for tag in ("biblioteca", "library", "lectura", "estudio")):
                templates.append(with_room("Club de lectura", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"grades": 5, "social": 2}}))
            if any(tag in tags for tag in ("gimnasio", "deporte", "cancha", "pista")):
                templates.append(with_room("Entrenamiento express", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 5, "grades": 1}}))
            if any(tag in tags for tag in ("auditorio", "teatro", "arte", "musica", "danza")):
                templates.append(with_room("Ensayo creativo", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 6}}))
            if any(tag in tags for tag in ("seguridad", "guardia", "administracion", "prefectura")):
                templates.append(with_room("Simulacro coordinado", {"planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 5}}))
            if any(tag in tags for tag in ("residencia", "dormitorio", "descanso", "salon")):
                templates.append(with_room("Ronda de bienestar", {"type": "social", "penalty": 8, "reward": {"social": 8}}))

        if room_name and not any(room_name in tpl["name"] for tpl in templates):
            templates.append(with_room("Actividad rápida", {"planner_category": "Apoyo académico", "penalty": 8, "reward": {"grades": 4}}))

        unique: list[dict[str, object]] = []
        seen_names: set[str] = set()
        for tpl in templates:
            name_tpl = tpl.get("name")
            if name_tpl in seen_names:
                continue
            seen_names.add(name_tpl)
            unique.append(tpl)
        return unique

class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bg = None
        try:
            img = pygame.image.load(TITLE_IMAGE).convert()
            self.bg = img
            iw, ih = img.get_width(), img.get_height()
            iw = max(iw, WINDOW_WIDTH)
            ih = max(ih, WINDOW_HEIGHT)
            if not FULLSCREEN and (game.screen.get_width(), game.screen.get_height()) != (iw, ih):
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
        win_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        try:
            tmp = pygame.image.load(TITLE_IMAGE)
            win_w = max(tmp.get_width(), WINDOW_WIDTH)
            win_h = max(tmp.get_height(), WINDOW_HEIGHT)
            win_size = (win_w, win_h)
        except Exception:
            pass

        pygame.display.set_caption(TITLE)
        if FULLSCREEN:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
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
