# main.py — versión ordenada para evitar "MenuScene undefined"
import os, sys, json, random, math
from collections import deque
from typing import Callable, Optional

import pygame

from settings import (
    WIDTH, HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, FULLSCREEN,
    FPS, TILE, TITLE,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_INTERACT, KEY_INVENTORY,
    KEY_ACTION_RUSH, KEY_FIGHT, KEY_MESSAGE, KEY_HELP,
    DEFAULT_MAP_CSV, DIALOGUES_JSON, TITLE_IMAGE, UI_FONT_FILE,
    MUSIC_FILE, HOVER_SFX, DEFAULT_MUSIC_VOL, DEFAULT_SFX_VOL,
    WINE, WINE_HOV, RED, HUD_PANEL_WIDTH
)

from core.engine import Camera2D, Scene, draw_text
from game.ui import (
    draw_hud,
    draw_action_feed,
    draw_action_popup,
    Button,
    Slider,
    DecisionPrompt,
    ChatWindow,
    draw_interaction_bubble,
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

# Configuración de roles jugables
ROLE_PROFILES = {
    "ALUMNO": {
        "role_key": "ALUMNO",
        "color": (235, 200, 40),
        "compatibility": ["lider", "academia", "colaboracion", "estudiante"],
        "aptitudes": ["Apoyo académico", "Tutoría intensiva"],
        "greeting": "¡Bienvenido al campus como alumno!",
        "intro_lines": [
            "Acércate a compañeros para recibir tareas aleatorias.",
            "Responde saludos con Y/N para mantener tu vida social.",
        ],
        "instructions": [
            "WASD: moverte por el campus",
            "E o ENTER: interactuar, aceptar tareas, comer y descansar",
            "Q: ráfaga de coordinación (lanza 100 acciones del equipo)",
            "Si ves un aviso de descanso o comida, pulsa E para recuperarte",
            "F: iniciar una pelea amistosa de práctica",
            "M: abrir la red social y mandar mensajes",
            "I: abrir tu inventario",
            "ESC: pausar o volver al menú",
            "H: mostrar/ocultar esta guía",
        ],
        "decision_options": [
            ("Resolver tarea pendiente", "Apoyo académico"),
            ("Unirte a actividad de club", "Montar taller"),
            ("Apoyar bienestar estudiantil", "Plan de seguridad"),
        ],
        "controls_hint": "WASD moverte | E interactuar | Y/N responder | Q ráfaga | F pelea | M mensajes | H ayuda",
        "planner_styles": {
            "Apoyo académico": {
                "category": "Estudio guiado",
                "names": [
                    "Estudiar en equipo en {room}",
                    "Resolver tarea pendiente en {room}",
                    "Preparar examen en {room}",
                ],
            },
            "Montar taller": {
                "category": "Club estudiantil",
                "names": [
                    "Organizar club creativo en {room}",
                    "Coordinar práctica deportiva en {room}",
                    "Montar proyecto estudiantil en {room}",
                ],
            },
            "Plan de seguridad": {
                "category": "Bienestar estudiantil",
                "names": [
                    "Supervisar convivencia en {room}",
                    "Apoyar orientación en {room}",
                    "Cuidar equipo escolar en {room}",
                ],
            },
        },
    },
    "MAESTRO": {
        "role_key": "MAESTRO",
        "color": (200, 200, 255),
        "compatibility": ["lider", "docencia", "academia"],
        "aptitudes": ["Apoyo académico", "Tutoría intensiva", "Plan de seguridad"],
        "greeting": "¡Listo para inspirar a tu clase!",
        "intro_lines": [
            "Coordina asesorías para subir el rendimiento del grupo.",
            "Visita laboratorios y aulas para detonar actividades docentes.",
        ],
        "instructions": [
            "WASD: moverte entre salones",
            "E o ENTER: interactuar, iniciar clases y descansar",
            "Q: lanzar coordinación docente (100 acciones)",
            "Aprovecha los avisos para tomar café o descansar con E",
            "F: iniciar dinámica de disciplina",
            "M: enviar mensajes al personal o alumnos",
            "I: consultar materiales",
            "ESC: pausar o volver al menú",
            "H: mostrar/ocultar esta guía",
        ],
        "decision_options": [
            ("Preparar clase interactiva", "Apoyo académico"),
            ("Dirigir taller didáctico", "Montar taller"),
            ("Supervisar seguridad del campus", "Plan de seguridad"),
        ],
        "controls_hint": "WASD moverte | E interactuar | Y/N responder | Q coordinación | F disciplina | M mensajes | H ayuda",
        "planner_styles": {
            "Apoyo académico": {
                "category": "Preparación docente",
                "names": [
                    "Planear clase magistral en {room}",
                    "Revisar exámenes en {room}",
                    "Guiar asesoría personalizada en {room}",
                ],
            },
            "Montar taller": {
                "category": "Taller docente",
                "names": [
                    "Organizar taller didáctico en {room}",
                    "Montar laboratorio demostrativo en {room}",
                    "Coordinar clínica académica en {room}",
                ],
            },
            "Plan de seguridad": {
                "category": "Supervisión escolar",
                "names": [
                    "Revisar protocolos en {room}",
                    "Coordinar simulacro en {room}",
                    "Atender incidentes en {room}",
                ],
            },
        },
    },
    "COLABORADOR": {
        "role_key": "COLABORADOR",
        "color": (255, 170, 110),
        "compatibility": ["lider", "logistica", "servicio"],
        "aptitudes": ["Logística escolar", "Plan de seguridad"],
        "greeting": "¡Gracias por apoyar las operaciones del campus!",
        "intro_lines": [
            "Atiende puntos de servicio y mantén los suministros al día.",
            "Coordina eventos y seguridad cuando los alumnos lo pidan.",
        ],
        "instructions": [
            "WASD: moverte por las áreas de servicio",
            "E o ENTER: atender solicitudes, comer y descansar",
            "Q: organizar un impulso logístico (100 acciones)",
            "Sigue los avisos y pulsa E para recuperar salud o energía",
            "F: calmar conflictos con presencia",
            "M: mandar mensajes a equipos de apoyo",
            "I: revisar inventario",
            "ESC: pausar o volver al menú",
            "H: mostrar/ocultar esta guía",
        ],
        "decision_options": [
            ("Atender servicio a estudiantes", "Apoyo académico"),
            ("Organizar logística del campus", "Montar taller"),
            ("Revisar protocolos de seguridad", "Plan de seguridad"),
        ],
        "controls_hint": "WASD moverte | E interactuar | Y/N responder | Q logística | F intervenir | M mensajes | H ayuda",
        "planner_styles": {
            "Apoyo académico": {
                "category": "Servicio a estudiantes",
                "names": [
                    "Atender ventanilla en {room}",
                    "Resolver trámites en {room}",
                    "Orientar visitantes en {room}",
                ],
            },
            "Montar taller": {
                "category": "Logística de eventos",
                "names": [
                    "Reabastecer kiosko en {room}",
                    "Organizar exhibición en {room}",
                    "Preparar stand de apoyo en {room}",
                ],
            },
            "Plan de seguridad": {
                "category": "Supervisión operativa",
                "names": [
                    "Revisar rutas de evacuación en {room}",
                    "Coordinar mantenimiento en {room}",
                    "Asegurar inventario en {room}",
                ],
            },
        },
    },
}

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
        "help": keys[getattr(pygame, "K_"+KEY_HELP)],
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
        self.map_zoom = 1.62
        cam_w = max(160, int(map_w / self.map_zoom))
        cam_h = max(160, int(map_h / self.map_zoom))
        self.camera = Camera2D(*self.map.world_size(), cam_w, cam_h)
        self.map_view = pygame.Rect(self.panel_width, 0, map_w, map_h)
        self.action_feed_rect = pygame.Rect(self.panel_width, self.map_view.bottom, map_w, self.bottom_feed_height)
        self._map_buffer = pygame.Surface((self.camera.screen_w, self.camera.screen_h), pygame.SRCALPHA)
        self._rebuild_map_backdrop()


        # 3) Player en el spawn del TMX
        spawn_x, spawn_y = self.map.player_spawn
        selected_role = getattr(self.game, "selected_role", None) or "ALUMNO"
        self.role_profile = ROLE_PROFILES.get(selected_role, ROLE_PROFILES["ALUMNO"])
        self.selected_role = selected_role
        self.player = Player(
            spawn_x,
            spawn_y,
            role=selected_role,
            role_profile=self.role_profile,
        )
        player_color = self.role_profile.get("color")
        if player_color:
            self.player.color = player_color

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

        self.planner = ActionPlanner(
            self.specialists,
            self.map,
            player=self.player,
            max_parallel=80,
            role_profile=self.role_profile,
        )
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
        self.rest_prompt_active = False
        self.rest_prompt_timer = 0.0
        self.rest_prompt_cooldown = 8.0
        self.pending_food_task_key: Optional[str] = None
        self.pending_social_task_key: Optional[str] = None
        self.pending_health_task_key: Optional[str] = None
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
        profile_hint = self.role_profile.get("controls_hint")
        if profile_hint:
            self.controls_hint = profile_hint
        else:
            self.controls_hint = "Controles: WASD moverte | E interactuar | Y/N responder | Q ráfaga | F pelea | M mensajes | H ayuda"
        self.default_controls_hint = self.controls_hint
        self.minimap_scale = 0.10
        self.minimap_base = self._build_minimap_surface()
        self.minimap_rect = self.minimap_base.get_rect() if self.minimap_base else pygame.Rect(0, 0, 0, 0)
        self.map_backdrop: Optional[pygame.Surface] = None
        self.interaction_hint: Optional[dict[str, object]] = None
        self.interaction_font = load_ui_font(16)
        if self.interaction_font is None:
            self.interaction_font = pygame.font.SysFont("arial", 16, bold=True)
        self.controls_overlay_lines = list(self.role_profile.get("instructions", []))
        if not self.controls_overlay_lines:
            self.controls_overlay_lines = [
                "WASD: moverte",
                "E: interactuar",
                "H: abrir/cerrar ayuda",
            ]
        self.controls_overlay_title = {
            "ALUMNO": "Guía para alumnos",
            "MAESTRO": "Guía para maestros",
            "COLABORADOR": "Guía para colaboradores",
        }.get(selected_role, "Guía del campus")
        self.show_controls_overlay = False
        self.help_hold = False
        self.help_overlay_auto = False
        self.help_auto_timer = 0.0
        self.autopilot: Optional[dict[str, object]] = None
        self.guidance_arrow_phase = 0.0
        self.guidance_hint_timer = 0.0
        self._show_role_intro()

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

    def _show_role_intro(self) -> None:
        greeting = self.role_profile.get("greeting")
        if greeting:
            self._set_message(greeting, 4.0)
            self.player.push_alert(greeting)
            self.player.note_interaction(greeting)
        intro_lines = list(self.role_profile.get("intro_lines", []))
        if intro_lines:
            for line in intro_lines:
                self._log_action(line)
        self._log_action(f"Rol seleccionado: {self.selected_role.title()}")
        if self.controls_overlay_lines:
            self.show_controls_overlay = True
            self.help_overlay_auto = True
            self.help_auto_timer = 8.0
        help_hint = self.role_profile.get("help_hint") or "Pulsa H para volver a ver los controles cuando quieras."
        self.player.push_alert(help_hint)

    def _rebuild_map_backdrop(self) -> None:
        if self._map_buffer is None:
            self.map_backdrop = None
            return
        width, height = self._map_buffer.get_size()
        if width <= 0 or height <= 0:
            self.map_backdrop = None
            return
        gradient = pygame.Surface((width, height), pygame.SRCALPHA)
        top = pygame.Color(26, 30, 44, 255)
        bottom = pygame.Color(14, 16, 26, 255)
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top.r * (1 - t) + bottom.r * t)
            g = int(top.g * (1 - t) + bottom.g * t)
            b = int(top.b * (1 - t) + bottom.b * t)
            pygame.draw.line(gradient, (r, g, b, 255), (0, y), (width, y))
        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(
            vignette,
            (0, 0, 0, 120),
            (-width * 0.25, height * 0.4, width * 1.5, height * 1.2),
        )
        gradient.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        pygame.draw.rect(gradient, (255, 255, 255, 30), gradient.get_rect(), width=2, border_radius=24)
        self.map_backdrop = gradient

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
            self._rebuild_map_backdrop()

    def _draw_map_backdrop(self, surface: pygame.Surface) -> None:
        if self.map_backdrop:
            surface.blit(self.map_backdrop, (0, 0))

    def _push_action_prompt(
        self,
        text: str,
        options: Optional[list[dict[str, object]]] = None,
        duration: Optional[float] = 6.0,
        tag: Optional[str] = None,
        on_timeout: Optional[Callable[[], object]] = None,
        detail: Optional[str] = None,
        target: Optional[object] = None,
        follow: Optional[object] = None,
    ) -> str:
        self.prompt_counter += 1
        prompt_id = f"P{self.prompt_counter}"
        entry: dict[str, object] = {
            "id": prompt_id,
            "text": text,
            "options": [],
            "timer": float(duration) if duration is not None else None,
            "duration": float(duration) if duration is not None else None,
            "tag": tag,
            "on_timeout": on_timeout,
            "detail": detail,
            "target": target,
            "follow": follow,
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

    def _activate_guidance(
        self,
        target: Optional[object] = None,
        follow: Optional[object] = None,
        room: Optional[str] = None,
        label: Optional[str] = None,
        arrival_text: Optional[str] = None,
    ) -> None:
        guide_target: Optional[pygame.Vector2] = None
        if follow is not None and hasattr(follow, "rect"):
            guide_target = pygame.Vector2(getattr(follow, "rect").center)
        elif target is not None:
            if isinstance(target, pygame.Vector2):
                guide_target = target.copy()
            elif isinstance(target, (tuple, list)) and len(target) >= 2:
                guide_target = pygame.Vector2(float(target[0]), float(target[1]))
        elif room:
            room_def = self.map.get_room(room)
            if room_def:
                rect = room_def.get("rect")
                if isinstance(rect, pygame.Rect):
                    guide_target = pygame.Vector2(rect.center)
        if guide_target is None:
            return
        self.autopilot = {
            "follow": follow,
            "target": guide_target,
            "room": room,
            "label": label or "En camino",
            "arrival_text": arrival_text,
            "radius": 42 if follow else 36,
        }
        self.guidance_arrow_phase = 0.0
        self.autopilot["indicator"] = guide_target
        self.player.push_alert("Sigue las flechas para llegar a tu actividad")
        self.controls_hint = "Flechas activas: deja que te guíen o usa WASD para cancelar"
        self.guidance_hint_timer = 6.0
        self._set_message(self.autopilot.get("label"), 2.0)

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

    def _accept_auto_task_guided(
        self,
        key: Optional[str],
        target: Optional[object] = None,
        follow: Optional[object] = None,
        room: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        response = self._accept_auto_task(key)
        if response:
            task_info = self._find_task_by_key(key)
            arrival = None
            guide_label = "En ruta a la actividad"
            if location:
                arrival = f"Has llegado a {location}. Busca la indicación y presiona E para ayudar."
                guide_label = f"Camino hacia {location}"
            self._activate_guidance(
                target=target,
                follow=follow,
                room=room,
                label=guide_label,
                arrival_text=arrival,
            )
            if task_info:
                focus_room = task_info.get("room") or room
                category = task_info.get("planner_category") or task_info.get("name")
                performer = follow if hasattr(follow, "current_action") else None
                self.planner.start_visual_preview(
                    category,
                    focus_room=focus_room,
                    performer=performer,
                    target_hint=target,
                    duration=5.0,
                )
        return response

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

    def _find_task_by_key(self, key: Optional[str]) -> Optional[dict[str, object]]:
        if not key:
            return None
        for task in self.player_tasks:
            if task.get("auto_key") == key or task.get("name") == key:
                return task
        return None

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

    def _update_autopilot(self, dt: float, base_keys: dict[str, bool]) -> Optional[dict[str, bool]]:
        if not self.autopilot:
            return None
        if any(base_keys.get(k, False) for k in ("up", "down", "left", "right")):
            self.autopilot = None
            self.controls_hint = self.default_controls_hint
            self.guidance_hint_timer = 0.0
            self.player.push_alert("Cancelaste la guía manualmente")
            return None
        indicator: Optional[pygame.Vector2] = None
        follow = self.autopilot.get("follow") if isinstance(self.autopilot, dict) else None
        if follow is not None and hasattr(follow, "rect"):
            indicator = pygame.Vector2(getattr(follow, "rect").center)
        else:
            raw_target = None
            if isinstance(self.autopilot, dict):
                raw_target = self.autopilot.get("target")
            if isinstance(raw_target, pygame.Vector2):
                indicator = raw_target.copy()
            elif isinstance(raw_target, (tuple, list)) and len(raw_target) >= 2:
                indicator = pygame.Vector2(float(raw_target[0]), float(raw_target[1]))
            room = None
            if isinstance(self.autopilot, dict):
                room = self.autopilot.get("room")
            if room:
                room_def = self.map.get_room(room)
                if room_def:
                    rect = room_def.get("rect")
                    if isinstance(rect, pygame.Rect):
                        indicator = pygame.Vector2(rect.center)
        if indicator is None:
            self.autopilot = None
            self.controls_hint = self.default_controls_hint
            self.guidance_hint_timer = 0.0
            return None
        self.autopilot["indicator"] = indicator
        player_pos = pygame.Vector2(self.player.rect.center)
        distance = player_pos.distance_to(indicator)
        if distance <= self.autopilot.get("radius", 36):
            arrival = self.autopilot.get("arrival_text")
            if arrival:
                self._set_message(arrival, 2.4)
            self.autopilot = None
            self.controls_hint = self.default_controls_hint
            self.guidance_hint_timer = 0.0
            return None
        direction = indicator - player_pos
        if direction.length_squared() <= 1.0:
            return None
        direction = direction.normalize()
        autop_keys = dict(base_keys)
        autop_keys.update({"up": False, "down": False, "left": False, "right": False})
        autop_keys["up"] = direction.y < -0.28
        autop_keys["down"] = direction.y > 0.28
        autop_keys["left"] = direction.x < -0.28
        autop_keys["right"] = direction.x > 0.28
        self.autopilot["vector"] = direction
        self.autopilot["distance"] = distance
        self.guidance_arrow_phase = (self.guidance_arrow_phase + dt * 3.2) % (math.tau)
        return autop_keys

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

    def _draw_controls_overlay(self, surface: pygame.Surface) -> None:
        if not self.show_controls_overlay:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((10, 12, 20, 160))
        screen_rect = surface.get_rect()
        panel_w = min(520, screen_rect.width - 160)
        panel_h = min(460, screen_rect.height - 160)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (18, 26, 38, 240), panel.get_rect(), border_radius=24)
        pygame.draw.rect(panel, (86, 120, 180, 255), panel.get_rect(), width=3, border_radius=24)
        title = self.font_overlay.render(self.controls_overlay_title, True, (240, 245, 255))
        panel.blit(title, (28, 24))
        y = 24 + title.get_height() + 12
        small = self.font_overlay_small
        for line in self.controls_overlay_lines:
            text = small.render(str(line), True, (220, 230, 240))
            panel.blit(text, (32, y))
            y += text.get_height() + 6
            if y > panel_h - 80:
                break
        footer_text = self.role_profile.get("help_footer") or "Pulsa H para cerrar la ayuda"
        footer = small.render(footer_text, True, (200, 210, 230))
        panel.blit(footer, (32, panel_h - footer.get_height() - 32))
        overlay.blit(panel, panel.get_rect(center=screen_rect.center))
        surface.blit(overlay, (0, 0))

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
        if self.rest_prompt_cooldown > 0:
            self.rest_prompt_cooldown = max(0.0, self.rest_prompt_cooldown - dt)
        if self.help_overlay_auto:
            self.help_auto_timer = max(0.0, self.help_auto_timer - dt)
            if self.help_auto_timer <= 0:
                self.help_overlay_auto = False
                self.show_controls_overlay = False
        if self.guidance_hint_timer > 0:
            self.guidance_hint_timer = max(0.0, self.guidance_hint_timer - dt)
            if self.guidance_hint_timer <= 0:
                self.controls_hint = self.default_controls_hint
        autop_keys = self._update_autopilot(dt, keys)
        if autop_keys:
            keys = autop_keys
        if not self.dialogue and not self.decision_prompt and not self.chat_window and not self.show_controls_overlay:
            self.player.handle_input(keys)
        else:
            self.player.vx = 0.0
            self.player.vy = 0.0
        self.player.update(dt, self.map)
        player_room = self.map.room_for_rect(self.player.rect)
        self.player.current_room = player_room.get("name") if player_room else None
        self._maybe_activate_food_prompt(dt)
        self._maybe_activate_rest_prompt(dt)

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

        if keys.get("help"):
            if not self.help_hold:
                self.show_controls_overlay = not self.show_controls_overlay
                if self.show_controls_overlay:
                    self.help_overlay_auto = False
            self.help_hold = True
        else:
            self.help_hold = False

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

        if (
            keys["interact"]
            and not self.interact_hold
            and not self.dialogue
            and not self.decision_prompt
            and not self.chat_window
            and not self.show_controls_overlay
        ):
            self.interact_hold = True
            handled = False
            if self.rest_prompt_active and self._consume_rest_prompt():
                handled = True
            elif self.food_prompt_active and self._consume_food_prompt():
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
        self._update_interaction_hint()

    def draw(self, surface):
        surface.fill((12, 14, 22))
        self._ensure_map_surfaces(surface)
        self.camera.center_on(self.player.rect)
        map_buffer = self._map_buffer
        map_buffer.fill((0, 0, 0, 0))
        self._draw_map_backdrop(map_buffer)
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
        self._draw_interaction_hint(map_buffer)
        self._draw_guidance_indicator(map_buffer)
        self._draw_activity_markers(map_buffer)
        scaled_map = pygame.transform.smoothscale(map_buffer, self.map_view.size)
        surface.blit(scaled_map, self.map_view.topleft)
        pygame.draw.rect(surface, (18, 22, 34), self.map_view, width=3, border_radius=18)
        self._draw_minimap(surface)
        max_scroll = draw_hud(surface, self.player, self.decision_status, self.player_tasks, scroll_offset=self.hud_scroll)
        self.hud_scroll_max = max_scroll
        if self.hud_scroll > self.hud_scroll_max:
            self.hud_scroll = self.hud_scroll_max
        draw_action_feed(surface, self.action_feed_rect, self.action_prompts, list(self.action_history), controls_hint=self.controls_hint)
        pygame.draw.rect(surface, (18, 22, 34), self.action_feed_rect, width=2, border_radius=16)
        draw_action_popup(surface, self.action_prompts, self.action_feed_rect)
        if self.decision_prompt:
            self.decision_prompt.draw(surface)
        if self.chat_window:
            self.chat_window.draw(surface)
        if self.message_text:
            self._draw_message(surface)
        if self.active_fight:
            self._draw_fight_banner(surface)
        if self.dialogue: self.dialogue.draw(surface)
        self._draw_controls_overlay(surface)
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
        role_options = self.role_profile.get("decision_options") or [
            ("Planear apoyo académico", "Apoyo académico"),
            ("Montar un taller", "Montar taller"),
            ("Armar plan de seguridad", "Plan de seguridad"),
        ]
        options = [label for (label, _cat) in role_options]
        self.decision_option_map = {label: cat for (label, cat) in role_options}
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
        if self.rest_prompt_active:
            self.rest_prompt_timer -= dt
            if self.rest_prompt_timer <= 0:
                self.rest_prompt_active = False
                self.rest_prompt_cooldown = 12.0
                self.player.push_alert("Necesitabas descansar y lo pospusiste")
                self.player.take_damage(6.0)
                if self.pending_health_task_key:
                    self._complete_auto_task(self.pending_health_task_key, False)
                    self.pending_health_task_key = None

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

    def _spawn_random_task(
        self,
        source_name: Optional[str] = None,
        focus_room: Optional[str] = None,
        guide_entity: Optional[object] = None,
    ):
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
        location_label: Optional[str] = None
        target_point: Optional[tuple[float, float]] = None
        follow_target: Optional[object] = None
        if guide_entity is not None and hasattr(guide_entity, "rect"):
            follow_target = guide_entity
            rect = getattr(guide_entity, "rect")
            target_point = (float(rect.centerx), float(rect.centery))
            location_label = getattr(guide_entity, "name", source_name)
        if location_label is None and focus_room:
            location_label = focus_room
        if target_point is None and focus_room:
            room_def = self.map.get_room(focus_room)
            if room_def:
                room_rect = room_def.get("rect")
                if isinstance(room_rect, pygame.Rect):
                    target_point = (float(room_rect.centerx), float(room_rect.centery))
        if location_label is None and source_name:
            location_label = source_name
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
        if target_point:
            entry["target_pos"] = target_point
        if location_label:
            entry["location"] = location_label
        if template.get("type") == "food":
            self.pending_food_task_key = entry["auto_key"]
            self._activate_food_prompt(force=True)
        elif template.get("type") == "social":
            self.pending_social_task_key = entry["auto_key"]
            self._trigger_random_greeting(force=True, task_key=entry["auto_key"])
        elif template.get("type") == "health":
            self.pending_health_task_key = entry["auto_key"]
            self._activate_rest_prompt(force=True)
        marker_color = (200, 220, 255) if focus_room else (245, 240, 200)
        self._add_activity_marker(entry["name"], pos=pygame.Vector2(self.player.rect.center), color=marker_color)
        if entry.get("auto"):
            auto_key = entry.get("auto_key")
            detail_text = None
            if location_label:
                detail_text = f"Pulsa Y para aceptar y sigue las flechas hacia {location_label}."
            prompt_id = self._push_action_prompt(
                text=f"¿Ayudar con {entry['name']}?",
                options=[
                    {
                        "key": pygame.K_y,
                        "display": "Y",
                        "label": "Aceptar",
                        "callback": lambda key=auto_key, pos=target_point, follow=follow_target, room=focus_room, loc=location_label: self._accept_auto_task_guided(key, pos, follow, room, loc),
                    },
                    {"key": pygame.K_n, "display": "N", "label": "Rechazar", "callback": lambda key=auto_key: self._reject_auto_task(key)},
                ],
                duration=8.0,
                tag="task",
                on_timeout=lambda key=auto_key: self._auto_task_timeout(key),
                detail=detail_text,
                target=target_point,
                follow=follow_target,
            )
            entry["prompt_id"] = prompt_id
        preview_category = entry.get("planner_category")
        if preview_category:
            performer = guide_entity if hasattr(guide_entity, "current_action") else None
            self.planner.start_visual_preview(
                preview_category,
                focus_room=focus_room,
                performer=performer,
                target_hint=target_point,
                duration=4.2,
            )
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
        self._spawn_random_task(source_name=name, focus_room=room_name, guide_entity=entity)
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

    def _maybe_activate_rest_prompt(self, dt: float) -> None:
        if self.rest_prompt_active:
            return
        if not getattr(self.player, "hp", 0):
            return
        if getattr(self.player, "hp", 0) <= 45 and self.rest_prompt_cooldown <= 0:
            self._activate_rest_prompt()

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

    def _activate_rest_prompt(self, force: bool = False) -> None:
        if self.rest_prompt_active:
            return
        if not force:
            if getattr(self.player, "hp", 100.0) > 45:
                return
            if self.rest_prompt_cooldown > 0:
                return
        self.rest_prompt_active = True
        self.rest_prompt_timer = 14.0 if force else 10.0
        self.rest_prompt_cooldown = 18.0
        self.player.push_alert("Presiona E para tomar un descanso y recuperar salud")
        self._set_message("Necesitas un descanso. Pulsa E para recuperar salud.", 3.0)
        self._log_action("Descanso disponible: pulsa E para recuperarte")

    def _consume_rest_prompt(self) -> bool:
        if not self.rest_prompt_active:
            return False
        self.rest_prompt_active = False
        self.rest_prompt_timer = 0.0
        self.rest_prompt_cooldown = 18.0
        self.player.restore_health(35.0)
        self.player.adjust_social(+2.0)
        self.player.note_interaction("Tomaste un descanso reparador")
        self._set_message("Descansaste y recuperaste salud", 1.8)
        self._add_activity_marker("Descanso recuperador", color=(180, 220, 200))
        if self.pending_health_task_key:
            self._complete_auto_task(self.pending_health_task_key, True)
            self.pending_health_task_key = None
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
            detail=f"Pulsa Y para devolver el saludo o N para ignorar a {greeter.name}",
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
                if "health" in reward:
                    self.player.restore_health(float(reward["health"]))
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
            if self.pending_health_task_key and key == self.pending_health_task_key:
                self.pending_health_task_key = None
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

    def _draw_guidance_indicator(self, surface: pygame.Surface) -> None:
        if not self.autopilot:
            return
        indicator = None
        if isinstance(self.autopilot, dict):
            indicator = self.autopilot.get("indicator")
        if indicator is None:
            return
        player_pos = pygame.Vector2(self.player.rect.center)
        target_vec = pygame.Vector2(indicator)
        direction = target_vec - player_pos
        if direction.length_squared() <= 4.0:
            return
        direction = direction.normalize()
        start = pygame.Vector2(player_pos.x - self.camera.x, player_pos.y - self.camera.y)
        arrow_color = (120, 190, 255)
        base = start + direction * 28
        dynamic_length = 42 + 8 * math.sin(self.guidance_arrow_phase)
        tip = start + direction * dynamic_length
        pygame.draw.line(surface, arrow_color, base, tip, 4)
        perp = pygame.Vector2(-direction.y, direction.x)
        wing1 = tip - direction * 14 + perp * 8
        wing2 = tip - direction * 14 - perp * 8
        pygame.draw.polygon(surface, arrow_color, [tip, wing1, wing2])
        target_screen = pygame.Vector2(target_vec.x - self.camera.x, target_vec.y - self.camera.y)
        pulse = 18 + int(4 * math.sin(self.guidance_arrow_phase * 1.6))
        pygame.draw.circle(surface, (70, 130, 220, 120), (int(target_screen.x), int(target_screen.y)), max(14, pulse), width=3)

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

    def _update_interaction_hint(self) -> None:
        if self.dialogue or self.decision_prompt or self.chat_window or self.player_dead:
            self.interaction_hint = None
            return
        hint_text = None
        anchor = pygame.Vector2(self.player.rect.midtop)
        accent = (120, 180, 255)
        if self.food_prompt_active:
            hint_text = "E: Comer algo rápido"
        elif self.active_greeting and not self.active_greeting.get("responded"):
            agent = self.active_greeting.get("agent")
            if agent:
                name = getattr(agent, "name", "Compañero")
                hint_text = f"Saludar a {name} (E)"
                anchor = pygame.Vector2(agent.rect.midtop)
                accent = (210, 170, 255)
        if not hint_text:
            door = self.map.door_for_rect(self.player.rect.inflate(10, 10))
            if door:
                dest = door.get("dest") or "un salón"
                hint_text = f"Entrar a {dest} (E)"
        if not hint_text:
            for npc in self.npcs:
                if self.player.rect.colliderect(npc.rect.inflate(48, 48)):
                    hint_text = f"Hablar con {npc.name} (E)"
                    anchor = pygame.Vector2(npc.rect.midtop)
                    accent = (180, 210, 255)
                    break
        if not hint_text:
            for item in self.items:
                if self.player.rect.colliderect(item.rect.inflate(24, 24)):
                    hint_text = "E: Recoger objeto"
                    anchor = pygame.Vector2(item.rect.midtop)
                    accent = (170, 230, 190)
                    break
        if not hint_text:
            near_spec = self._nearest_specialist()
            if near_spec and self.player.rect.colliderect(near_spec.rect.inflate(80, 80)):
                hint_text = f"Apoyar a {near_spec.name} (E)"
                anchor = pygame.Vector2(near_spec.rect.midtop)
                accent = (220, 200, 140)
        if not hint_text and self.rush_cooldown <= 0:
            hint_text = "Q: Lanzar coordinación masiva"
            accent = (255, 160, 120)
        if hint_text:
            self.interaction_hint = {"text": hint_text, "pos": anchor, "accent": accent}
        else:
            self.interaction_hint = None

    def _draw_interaction_hint(self, surface: pygame.Surface) -> None:
        if not self.interaction_hint or not self.interaction_hint.get("text"):
            return
        pos = self.interaction_hint.get("pos")
        if pos is None:
            return
        if not isinstance(pos, pygame.Vector2):
            try:
                pos = pygame.Vector2(pos)
            except Exception:
                pos = pygame.Vector2(self.player.rect.midtop)
        bubble_rect = pygame.Rect(int(pos.x), int(pos.y), 4, 4)
        screen_rect = self.camera.apply(bubble_rect)
        bubble_pos = (screen_rect.centerx, screen_rect.top)
        accent = self.interaction_hint.get("accent", (120, 180, 255))
        draw_interaction_bubble(surface, bubble_pos, self.interaction_hint["text"], self.interaction_font, accent=accent)

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
        role = getattr(self.player, "role", "ALUMNO")
        if role == "MAESTRO":
            base = [
                {"name": "Preparar evaluación", "planner_category": "Apoyo académico", "penalty": 8, "reward": {"grades": 6}},
                {"name": "Laboratorio demostrativo", "planner_category": "Montar taller", "penalty": 8, "reward": {"grades": 4, "social": 3}},
                {"name": "Supervisión docente", "planner_category": "Plan de seguridad", "penalty": 7, "reward": {"social": 4}},
                {"name": "Pausa para café", "type": "food", "penalty": 6, "reward": {"hunger": 30, "health": 10}},
                {"name": "Descanso en sala de maestros", "type": "health", "penalty": 5, "reward": {"health": 30}},
                {"name": "Mentoría con alumno", "type": "social", "penalty": 7, "reward": {"social": 8, "grades": 2}},
            ]
        elif role == "COLABORADOR":
            base = [
                {"name": "Atender ventanilla saturada", "planner_category": "Apoyo académico", "penalty": 8, "reward": {"social": 5}},
                {"name": "Organizar stand de apoyo", "planner_category": "Montar taller", "penalty": 8, "reward": {"social": 5, "grades": 2}},
                {"name": "Inspección de seguridad", "planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 4}},
                {"name": "Refuerzo de energía", "type": "food", "penalty": 6, "reward": {"hunger": 35, "health": 5}},
                {"name": "Pausa de hidratación", "type": "health", "penalty": 5, "reward": {"health": 30}},
                {"name": "Charla con el equipo", "type": "social", "penalty": 7, "reward": {"social": 9}},
            ]
        else:
            base = [
                {"name": "Estudio urgente", "planner_category": "Apoyo académico", "penalty": 10, "reward": {"grades": 6}},
                {"name": "Club relámpago", "planner_category": "Montar taller", "penalty": 8, "reward": {"social": 5, "grades": 2}},
                {"name": "Brigada estudiantil", "planner_category": "Plan de seguridad", "penalty": 7, "reward": {"social": 4}},
                {"name": "Snack revitalizante", "type": "food", "penalty": 6, "reward": {"hunger": 40}},
                {"name": "Descanso de biblioteca", "type": "health", "penalty": 6, "reward": {"health": 28}},
                {"name": "Charla con compañeros", "type": "social", "penalty": 7, "reward": {"social": 10}},
            ]

        templates = [dict(tpl) for tpl in base]
        tags = self._room_tags(room_name)

        def with_room(title: str, payload: dict[str, object]) -> dict[str, object]:
            tpl = dict(payload)
            tpl["name"] = title if not room_name else f"{title} en {room_name}"
            return tpl

        if tags:
            if any(tag in tags for tag in ("cafeteria", "comedor", "food", "cafe")):
                if role == "MAESTRO":
                    templates.append(with_room("Café con colegas", {"type": "social", "penalty": 6, "reward": {"social": 6}}))
                    templates.append(with_room("Plan de clase en cafetería", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"grades": 5}}))
                elif role == "COLABORADOR":
                    templates.append(with_room("Reabastecer cafetería", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 5}}))
                    templates.append(with_room("Atención express de pedidos", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"social": 4}}))
                else:
                    templates.append(with_room("Repaso en la cafetería", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"grades": 5}}))
                    templates.append(with_room("Snack con amigos", {"type": "food", "penalty": 6, "reward": {"hunger": 30, "social": 4}}))
            if any(tag in tags for tag in ("laboratorio", "lab", "ciencia", "ingenieria")):
                if role == "MAESTRO":
                    templates.append(with_room("Supervisar experimento", {"planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 4}}))
                    templates.append(with_room("Diseñar práctica guiada", {"planner_category": "Montar taller", "penalty": 8, "reward": {"grades": 5}}))
                elif role == "COLABORADOR":
                    templates.append(with_room("Abastecer laboratorio", {"planner_category": "Montar taller", "penalty": 8, "reward": {"social": 4, "grades": 2}}))
                else:
                    templates.append(with_room("Experimento guiado", {"planner_category": "Apoyo académico", "penalty": 8, "reward": {"grades": 6}}))
            if any(tag in tags for tag in ("biblioteca", "library", "lectura", "estudio")):
                if role == "MAESTRO":
                    templates.append(with_room("Revisión de bibliografía", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"grades": 5}}))
                elif role == "COLABORADOR":
                    templates.append(with_room("Ordenar estanterías", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 4}}))
                else:
                    templates.append(with_room("Club de lectura", {"planner_category": "Apoyo académico", "penalty": 7, "reward": {"grades": 5, "social": 2}}))
            if any(tag in tags for tag in ("gimnasio", "deporte", "cancha", "pista")):
                if role == "COLABORADOR":
                    templates.append(with_room("Revisar equipo deportivo", {"planner_category": "Plan de seguridad", "penalty": 7, "reward": {"social": 4}}))
                else:
                    templates.append(with_room("Entrenamiento express", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 5, "grades": 1}}))
            if any(tag in tags for tag in ("auditorio", "teatro", "arte", "musica", "danza")):
                if role == "COLABORADOR":
                    templates.append(with_room("Montar evento cultural", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 6}}))
                else:
                    templates.append(with_room("Ensayo creativo", {"planner_category": "Montar taller", "penalty": 7, "reward": {"social": 6}}))
            if any(tag in tags for tag in ("seguridad", "guardia", "administracion", "prefectura")):
                templates.append(with_room("Simulacro coordinado", {"planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 5}}))
            if any(tag in tags for tag in ("residencia", "dormitorio", "descanso", "salon")):
                if role == "COLABORADOR":
                    templates.append(with_room("Supervisar residencias", {"planner_category": "Plan de seguridad", "penalty": 8, "reward": {"social": 4}}))
                else:
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
