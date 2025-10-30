# main.py — versión ordenada para evitar "MenuScene undefined"
import os, sys, json, random, math
from typing import Optional

import pygame

from settings import (
    WIDTH, HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, FULLSCREEN,
    FPS, TILE, TITLE,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_INTERACT, KEY_INVENTORY,
    DEFAULT_MAP_CSV, DIALOGUES_JSON, TITLE_IMAGE, UI_FONT_FILE,
    MUSIC_FILE, HOVER_SFX, DEFAULT_MUSIC_VOL, DEFAULT_SFX_VOL,
    WINE, WINE_HOV, RED, HUD_PANEL_WIDTH
)

from core.engine import Camera2D, Scene, draw_text
from game.ui import draw_hud, Button, Slider, DecisionPrompt

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

        # 2) Cámara al tamaño del mapa sin el panel lateral
        view_w = max(320, self.game.screen.get_width() - HUD_PANEL_WIDTH)
        view_h = self.game.screen.get_height()
        self.camera = Camera2D(*self.map.world_size(), view_w, view_h)
        self.panel_width = HUD_PANEL_WIDTH
        self.map_view = pygame.Rect(self.panel_width, 0, view_w, view_h)


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
        while len(self.specialists) < 60:
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

        self.planner = ActionPlanner(self.specialists, self.map, player=self.player, max_parallel=64)
        self.decision_status = None
        self.font_overlay = load_ui_font(18)
        self.font_overlay_small = load_ui_font(16)
        if self.font_overlay is None:
            self.font_overlay = pygame.font.SysFont("arial", 18, bold=True)
        if self.font_overlay_small is None:
            self.font_overlay_small = pygame.font.SysFont("arial", 16)
        self.decision_prompt: Optional[DecisionPrompt] = None
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

    def handle_event(self, event):
        if self.player_dead:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game.play_scene = None
                self.game.change_scene(MenuScene(self.game))
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

        if self.food_prompt_cooldown > 0:
            self.food_prompt_cooldown = max(0.0, self.food_prompt_cooldown - dt)
        if not self.dialogue and not self.decision_prompt:
            self.player.handle_input(keys)
        else:
            self.player.vx = 0.0
            self.player.vy = 0.0
        self.player.update(dt, self.map)
        player_room = self.map.room_for_rect(self.player.rect)
        self.player.current_room = player_room.get("name") if player_room else None
        self._maybe_activate_food_prompt(dt)

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

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message_text = ""

        if keys["interact"] and not self.interact_hold and not self.dialogue and not self.decision_prompt:
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
        map_width = max(1, surface.get_width() - self.panel_width)
        if self.map_view.width != map_width or self.map_view.height != surface.get_height():
            self.map_view.size = (map_width, surface.get_height())
            self.camera.screen_w = map_width
            self.camera.screen_h = surface.get_height()
        map_surface = surface.subsurface(self.map_view)
        map_surface.fill((18, 20, 28))
        self.map.draw(map_surface, self.camera)
        for it in self.items:
            it.draw(map_surface, self.camera)
        for n in self.npcs:
            n.draw(map_surface, self.camera)
        for agent in self.specialists:
            agent.draw(map_surface, self.camera)
        for e in self.enemies:
            e.draw(map_surface, self.camera)
        self.player.draw(map_surface, self.camera)
        draw_hud(surface, self.player, self.decision_status, self.player_tasks)
        if self.decision_prompt:
            self.decision_prompt.draw(surface)
        if self.message_text:
            self._draw_message(surface)
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
                else:
                    self._set_message(f"{agent.name}: {agent.status_text()}")
                    self.player.adjust_relationship(agent.name, 1)
                    self.player.note_interaction(f"Chequeaste a {agent.name}")
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
            "Coordinar recolección",
            "Impulsar construcción",
            "Organizar defensa",
        ]
        self.decision_option_map = {
            "Coordinar recolección": "Recolectar",
            "Impulsar construcción": "Construir",
            "Organizar defensa": "Defender/Resguardarse",
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
        self.random_task_timer -= dt
        if self.random_task_timer <= 0:
            self._spawn_random_task()
            self.random_task_timer = random.uniform(14.0, 24.0)

        if self.greeting_timer > 0:
            self.greeting_timer -= dt
        if self.greeting_timer <= 0:
            self._trigger_random_greeting()
            self.greeting_timer = random.uniform(8.0, 16.0)

        if self.active_greeting:
            self.active_greeting["timer"] -= dt
            agent = self.active_greeting.get("agent")
            if self.active_greeting["timer"] <= 0 or not agent:
                if agent and not self.active_greeting.get("responded"):
                    self.player.resolve_greeting(agent.name, False)
                    self.player.adjust_relationship(agent.name, -6)
                    if self.pending_social_task_key and self.active_greeting.get("task_key") == self.pending_social_task_key:
                        self._complete_auto_task(self.pending_social_task_key, False)
                        self.pending_social_task_key = None
                if agent:
                    agent.clear_interaction_request()
                self.active_greeting = None

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

    def _spawn_random_task(self):
        templates = [
            {
                "name": "Recolecta urgente",
                "planner_category": "Coordinar recolección",
                "penalty": 12,
                "reward": {"grades": 4},
            },
            {
                "name": "Fortificar salones",
                "planner_category": "Impulsar construcción",
                "penalty": 10,
                "reward": {"grades": 5},
            },
            {
                "name": "Simulacro de refugio",
                "planner_category": "Organizar defensa",
                "penalty": 9,
                "reward": {"social": 4},
            },
            {
                "name": "Comer algo rápido",
                "type": "food",
                "penalty": 10,
                "reward": {"hunger": 40},
            },
            {
                "name": "Charla con aliados",
                "type": "social",
                "penalty": 11,
                "reward": {"social": 10},
            },
        ]
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
        }
        if template.get("planner_category"):
            action = self.planner.plan_player_choice(template["planner_category"], focus_room=self.player.current_room, helper=self.player)
            if action:
                entry["name"] = action.name
                entry["auto_key"] = action.name
                entry["planner_category"] = template["planner_category"]
                entry["status"] = "Planificada"
            else:
                entry["status"] = "Esperando recursos"
                entry["timer"] = random.uniform(20.0, 35.0)
        self.player_tasks.append(entry)
        self.player.push_alert(f"Nueva tarea: {entry['name']}")
        self.player.note_interaction(f"Nueva tarea: {entry['name']}")
        self._set_message(f"¡Nueva misión!: {entry['name']}", 2.6)
        if template.get("type") == "food":
            self.pending_food_task_key = entry["auto_key"]
            self._activate_food_prompt(force=True)
        elif template.get("type") == "social":
            self.pending_social_task_key = entry["auto_key"]
            self._trigger_random_greeting(force=True, task_key=entry["auto_key"])

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
        if self.pending_food_task_key:
            self._complete_auto_task(self.pending_food_task_key, True)
            self.pending_food_task_key = None
        return True

    def _handle_greeting_response(self) -> bool:
        if not self.active_greeting or self.active_greeting.get("responded"):
            return False
        agent = self.active_greeting.get("agent")
        if not agent:
            return False
        if agent.rect.colliderect(self.player.rect.inflate(60, 60)):
            self.active_greeting["responded"] = True
            agent.clear_interaction_request()
            self.player.resolve_greeting(agent.name, True)
            self.player.adjust_relationship(agent.name, 8)
            if self.pending_social_task_key and self.active_greeting.get("task_key") == self.pending_social_task_key:
                self._complete_auto_task(self.pending_social_task_key, True)
                self.pending_social_task_key = None
            self._set_message(f"Saludaste a {agent.name}", 1.8)
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
        self.active_greeting = {"agent": greeter, "timer": 6.0, "responded": False, "task_key": task_key}
        self.player.begin_greeting(greeter.name)
        self.player.note_interaction(f"{greeter.name} te saludó")
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
            else:
                task["status"] = "Fallida"
                task["started"] = True
                self.player.adjust_grades(-penalty)
                self.player.adjust_social(-penalty * 0.4)
                self.player.hp = max(0.0, self.player.hp - penalty * 0.3)
                self.player.push_alert(f"Fallaste {task['name']}")
                self.player.note_interaction(f"Perdiste la tarea {task['name']}")
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
        y = surface.get_height() - bg.get_height() - 20
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
