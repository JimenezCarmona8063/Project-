"""Sistema de planificación de acciones con colas, heap y listas enlazadas."""
from __future__ import annotations

import heapq
import random
from collections import deque
from dataclasses import dataclass
from queue import Queue
from typing import Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .entities import Character


@dataclass
class Action:
    name: str
    category: str
    duration: float
    priority: float
    compatibility: set[str]
    required_aptitudes: set[str]
    resource_cost: Dict[str, float]
    target_room: Optional[str] = None
    generated_by_event: bool = False
    variant: str = ""


@dataclass
class ActiveAction:
    character: "Character"
    action: Action
    remaining: float
    total: float
    target: Optional[Tuple[float, float]] = None

    def progress(self) -> float:
        if self.total <= 0:
            return 1.0
        return 1.0 - max(0.0, self.remaining) / self.total


class _HistoryNode:
    def __init__(self, text: str, nxt: Optional["_HistoryNode"] = None):
        self.text = text
        self.next = nxt


class ActionHistory:
    """Lista enlazada simple para guardar el historial de acciones."""

    def __init__(self) -> None:
        self.head: Optional[_HistoryNode] = None

    def prepend(self, text: str) -> None:
        self.head = _HistoryNode(text, self.head)

    def to_list(self, limit: int = 10) -> List[str]:
        out: List[str] = []
        node = self.head
        while node and len(out) < limit:
            out.append(node.text)
            node = node.next
        return out


class ActionPlanner:
    """Planificador que integra Queue -> Heap -> ejecución simultánea."""

    def __init__(
        self,
        characters: Iterable["Character"],
        tilemap,
        player: Optional["Character"] = None,
        max_parallel: int = 64,
        role_profile: Optional[dict] = None,
    ) -> None:
        self.characters: List["Character"] = list(characters)
        self.rotation: deque["Character"] = deque(self.characters)
        self.tilemap = tilemap
        self.player = player
        self.role_styles = dict(role_profile.get("planner_styles", {})) if role_profile else {}
        self.player_room: Optional[str] = None

        self.world_w, self.world_h = self.tilemap.world_size()
        self.rooms = getattr(self.tilemap, "rooms", [])
        self.rooms_by_name = {room.get("name"): room for room in self.rooms if room.get("name")}

        self.instruction_buffer: Queue[Action] = Queue()
        self.action_heap: List[Tuple[float, int, Action]] = []
        self.heap_order = 0
        self.active: List[ActiveAction] = []
        self.history = ActionHistory()

        self.resources: Dict[str, float] = {
            "energia": 420.0,
            "materiales": 260.0,
            "comida": 320.0,
        }
        self.resource_caps: Dict[str, float] = {
            "energia": 520.0,
            "materiales": 320.0,
            "comida": 360.0,
        }

        self.max_parallel = max_parallel
        self.last_event: Optional[str] = None
        self.event_timer = random.uniform(14.0, 22.0)

        self.populate_initial_actions()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, dt: float, tilemap) -> None:
        self._ingest_buffer()
        self._assign_actions()
        self._update_active(dt, tilemap)
        self._recover_resources(dt)
        self._update_events(dt)
        self._ensure_supply()

    def set_player_room(self, room_name: Optional[str]) -> None:
        self.player_room = room_name

    def report_player_entered_room(self, room_name: str) -> None:
        if room_name:
            self.history.prepend(f"El jugador entró a {room_name}")
            self.set_player_room(room_name)

    def boost_character(self, character: "Character", helper: Optional["Character"] = None) -> Optional[str]:
        helper_name = getattr(helper, "name", "Jugador") if helper else "Jugador"
        for active in self.active:
            if active.character is character:
                reduction = max(0.0, active.total * 0.25)
                active.remaining = max(0.0, active.remaining - reduction)
                character.boost_action(f"{helper_name} apoya")
                self.history.prepend(f"{helper_name} apoyó a {character.name} en {active.action.name}")
                return f"Apoyaste a {character.name} ({active.action.category})"
        if character.current_action is None:
            action = self._make_followup_action(character)
            self.enqueue_action(action)
            character.boost_action("Solicitó nueva tarea")
            return f"Se planificó una tarea para {character.name}"
        return None

    def enqueue_action(self, action: Action) -> None:
        self.instruction_buffer.put(action)

    def trigger_mass_actions(self, target_parallel: int = 100) -> str:
        """Eleva el cupo y rellena acciones para alcanzar la ráfaga solicitada."""
        self.max_parallel = max(self.max_parallel, target_parallel)
        pending_total = len(self.active) + len(self.action_heap) + self.instruction_buffer.qsize()
        needed = max(0, target_parallel - pending_total)
        for _ in range(needed):
            self.enqueue_action(self._make_followup_action())
        self.history.prepend(f"Ráfaga programada: {target_parallel} acciones")
        return f"Ráfaga de {target_parallel} acciones activada"

    def plan_player_choice(
        self,
        category: str,
        focus_room: Optional[str] = None,
        helper: Optional["Character"] = None,
    ) -> Optional[Action]:
        rooms = [room.get("name") for room in self.rooms if room.get("name")]
        action: Optional[Action] = None
        lowered = category.lower()
        if lowered.startswith("apoyo") or lowered.startswith("tutori"):
            variant = random.choice(["apoyo_rapido", "tutoria_intensiva"])
            action = self._make_apoyo_action(rooms, variant=variant)
        elif lowered.startswith("montar") or lowered.startswith("taller"):
            action = self._make_taller_action(rooms)
        elif lowered.startswith("plan") or lowered.startswith("seguridad"):
            focus = focus_room or (rooms[0] if rooms else None)
            action = self._make_seguridad_action(focus)
            action.generated_by_event = False
        if not action:
            return None
        action = self._style_action_for_role(action, category, focus_room)
        action.compatibility = set(action.compatibility)
        action.compatibility.add("lider")
        if focus_room:
            action.target_room = focus_room
            if " en " in action.name:
                base, _, _ = action.name.partition(" en ")
                action.name = f"{base} en {focus_room}"
            else:
                action.name = f"{action.name} en {focus_room}"
        if helper:
            action.priority = max(0.1, action.priority * 0.75)
        else:
            action.priority = max(0.2, action.priority)
        self.history.prepend(f"El jugador decidió {action.name}")
        self.last_event = f"Decisión jugador: {action.category}"
        self.enqueue_action(action)
        return action

    def start_visual_preview(
        self,
        category: Optional[str],
        focus_room: Optional[str] = None,
        performer: Optional["Character"] = None,
        target_hint: Optional[Tuple[float, float]] = None,
        duration: float = 4.0,
    ) -> Optional[ActiveAction]:
        """Dispara una acción corta para que un personaje visible la represente."""
        if not category:
            return None
        if len(self.active) >= self.max_parallel:
            return None
        chosen: Optional["Character"] = None
        if performer and performer in self.characters:
            if performer.current_action is None and performer.availability >= 0.99 and not getattr(performer, "dead", False):
                chosen = performer
        if chosen is None:
            candidates = [
                char
                for char in self.characters
                if char.current_action is None
                and char.availability >= 0.99
                and not getattr(char, "dead", False)
                and getattr(char, "visible", True)
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda c: (c.importance, random.random()))
            chosen = candidates[0]
        if chosen is None or chosen.current_action is not None:
            return None
        action = self._make_preview_action(category, focus_room, chosen)
        action.duration = max(2.8, min(8.0, float(duration)))
        action.priority = min(action.priority, 1.0)
        action.generated_by_event = False
        if focus_room:
            action.target_room = focus_room
        target: Optional[Tuple[float, float]] = None
        if target_hint is not None:
            if isinstance(target_hint, pygame.Vector2):
                target = (float(target_hint.x), float(target_hint.y))
            elif isinstance(target_hint, (tuple, list)) and len(target_hint) >= 2:
                target = (float(target_hint[0]), float(target_hint[1]))
        if target is None:
            target = self._target_for_action(action, chosen)
        chosen.assign_action(action, target=target)
        preview = ActiveAction(
            character=chosen,
            action=action,
            remaining=action.duration,
            total=action.duration,
            target=target,
        )
        self.active.append(preview)
        self.history.prepend(f"{chosen.name} demuestra {action.name}")
        return preview

    def _style_action_for_role(
        self,
        action: Action,
        original_category: str,
        focus_room: Optional[str],
    ) -> Action:
        if not self.role_styles:
            return action
        base_key = action.category
        style = self.role_styles.get(base_key) or self.role_styles.get(original_category)
        if not style:
            return action
        room_name = focus_room or action.target_room or "el campus"
        display_category = style.get("category")
        if display_category:
            action.category = display_category
        name_options = style.get("names") or []
        if name_options:
            template = random.choice(name_options)
            action.name = template.replace("{room}", room_name)
        else:
            rename = style.get("name")
            if isinstance(rename, str):
                action.name = rename.replace("{room}", room_name)
        extra_priority = style.get("priority_bonus")
        if isinstance(extra_priority, (int, float)):
            action.priority = max(0.1, action.priority + float(extra_priority))
        return action

    def get_status_snapshot(self) -> Dict[str, object]:
        active_snapshot = []
        for active in self.active[:8]:
            active_snapshot.append(
                (
                    active.character.name,
                    active.action.name,
                    active.action.category,
                    round(active.progress(), 2),
                    active.action.generated_by_event,
                )
            )
        snapshot = {
            "active": active_snapshot,
            "active_total": len(self.active),
            "queue": len(self.action_heap),
            "buffer": self.instruction_buffer.qsize(),
            "resources": dict(self.resources),
            "history": self.history.to_list(6),
            "last_event": self.last_event,
            "max_parallel": self.max_parallel,
        }
        return snapshot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def populate_initial_actions(self) -> None:
        room_choices = [room.get("name") for room in self.rooms if room.get("name")]
        if not room_choices:
            room_choices = ["Patio", "Laboratorio", "Biblioteca"]

        for _ in range(36):
            self.enqueue_action(self._make_apoyo_action(room_choices, variant="apoyo_rapido"))
        for _ in range(24):
            self.enqueue_action(self._make_apoyo_action(room_choices, variant="tutoria_intensiva"))
        for _ in range(18):
            self.enqueue_action(self._make_taller_action(room_choices))

    def _ingest_buffer(self) -> None:
        while not self.instruction_buffer.empty():
            action = self.instruction_buffer.get()
            heapq.heappush(self.action_heap, (action.priority, self.heap_order, action))
            self.heap_order += 1

    def _assign_actions(self) -> None:
        if not self.action_heap:
            return
        available_slots = max(0, self.max_parallel - len(self.active))
        if available_slots <= 0:
            return
        for _ in range(len(self.rotation)):
            char = self.rotation[0]
            self.rotation.rotate(-1)
            if getattr(char, "dead", False):
                continue
            if char.current_action is not None:
                continue
            if char.availability < 0.99:
                continue
            action = self._extract_action_for(char)
            if not action:
                continue
            target = self._target_for_action(action, char)
            char.assign_action(action, target=target)
            if action.target_room:
                char.set_room(action.target_room)
            self._consume_resources(action)
            assignment = ActiveAction(
                character=char,
                action=action,
                remaining=action.duration,
                total=action.duration,
                target=target,
            )
            self.active.append(assignment)
            self.history.prepend(f"{char.name} inició {action.name}")
            if len(self.active) >= self.max_parallel:
                break

    def _update_active(self, dt: float, tilemap) -> None:
        finished: List[ActiveAction] = []
        for active in self.active:
            char = active.character
            char.update_action(dt, tilemap)
            speed = 1.0 + char.importance * 0.05
            if active.action.variant == "tutoria_intensiva":
                speed += 0.15
            if active.action.generated_by_event:
                speed += 0.25
            if self.player_room and active.action.target_room == self.player_room:
                speed += 0.2
            active.remaining -= dt * speed
            if active.remaining <= 0:
                finished.append(active)
        for active in finished:
            self._finish_action(active)

    def _finish_action(self, active: ActiveAction) -> None:
        char = active.character
        if active in self.active:
            self.active.remove(active)
        char.clear_action()
        char.set_room(None)
        if active.action.generated_by_event:
            char.hp = max(12.0, char.hp - 6.0)
        else:
            char.hp = min(char.max_hp, char.hp + 4.0)
        for resource, cost in active.action.resource_cost.items():
            cap = self.resource_caps.get(resource, 400.0)
            self.resources[resource] = min(cap, self.resources.get(resource, 0.0) + cost * 0.6)
        self.history.prepend(f"{char.name} completó {active.action.name}")
        self.enqueue_action(self._make_followup_action(char))

    def _recover_resources(self, dt: float) -> None:
        for key, cap in self.resource_caps.items():
            current = self.resources.get(key, 0.0)
            if current < cap:
                self.resources[key] = min(cap, current + dt * 1.2)

    def _update_events(self, dt: float) -> None:
        self.event_timer -= dt
        if self.event_timer <= 0:
            self._trigger_defense_event()
            self.event_timer = random.uniform(24.0, 32.0)

    def _ensure_supply(self) -> None:
        pending = len(self.action_heap) + self.instruction_buffer.qsize()
        if pending < 40:
            for _ in range(10):
                self.enqueue_action(self._make_followup_action())

    # ------------------------------------------------------------------
    # Action factories
    # ------------------------------------------------------------------
    def _make_apoyo_action(self, rooms: List[str], variant: str = "apoyo_rapido") -> Action:
        room = random.choice(rooms) if rooms else None
        if variant == "tutoria_intensiva":
            name = f"Tutoría intensiva en {room or 'sala de estudio'}"
            required = {"Tutoría intensiva"}
            compat = {"academia", "emergencia"}
            cost = {"energia": 7.5, "comida": 5.0}
            duration = random.uniform(4.5, 6.2)
            priority = random.uniform(1.2, 2.6)
        else:
            name = f"Apoyo exprés en {room or 'el campus'}"
            required = {"Apoyo académico"}
            compat = {"academia", "colaboracion"}
            cost = {"energia": 5.0, "comida": 3.5}
            duration = random.uniform(3.6, 5.2)
            priority = random.uniform(1.6, 3.2)
        return Action(
            name=name,
            category="Apoyo académico",
            duration=duration,
            priority=priority,
            compatibility=compat,
            required_aptitudes=required,
            resource_cost=cost,
            target_room=room,
            variant=variant,
        )

    def _make_taller_action(self, rooms: List[str]) -> Action:
        room = random.choice(rooms) if rooms else None
        name = f"Montar taller en {room or 'patio central'}"
        return Action(
            name=name,
            category="Montar taller",
            duration=random.uniform(6.0, 9.0),
            priority=random.uniform(0.9, 2.0),
            compatibility={"logistica"},
            required_aptitudes={"Logística escolar"},
            resource_cost={"energia": 8.0, "materiales": 10.0},
            target_room=room,
        )

    def _make_seguridad_action(self, room: Optional[str]) -> Action:
        name = f"Plan de seguridad en {room or 'zona segura'}"
        return Action(
            name=name,
            category="Plan de seguridad",
            duration=random.uniform(5.0, 7.5),
            priority=0.7,
            compatibility={"bienestar", "resguardo"},
            required_aptitudes={"Plan de seguridad"},
            resource_cost={"energia": 7.0, "materiales": 5.0},
            target_room=room,
            generated_by_event=True,
        )

    def _make_preview_action(
        self,
        category: str,
        focus_room: Optional[str],
        character: "Character",
    ) -> Action:
        room_list = []
        if focus_room:
            room_list = [focus_room]
        elif self.rooms_by_name:
            room_list = list(self.rooms_by_name.keys())
        else:
            room_list = ["Patio"]
        lowered = category.lower()
        if any(token in lowered for token in ("seguridad", "bienestar", "resguardo")):
            room_name = focus_room or random.choice(room_list)
            action = self._make_seguridad_action(room_name)
            action.generated_by_event = False
        elif any(token in lowered for token in ("taller", "logística", "logistica", "club", "evento")):
            action = self._make_taller_action(room_list)
        else:
            variant = "tutoria_intensiva" if any(token in lowered for token in ("tutor", "intens", "asesor")) else "apoyo_rapido"
            action = self._make_apoyo_action(room_list, variant=variant)
        action = self._style_action_for_role(action, category, focus_room)
        if focus_room:
            action.target_room = focus_room
        if not action.compatibility:
            action.compatibility = set(getattr(character, "compatibility", []))
        return action

    def _make_followup_action(self, character: Optional["Character"] = None) -> Action:
        rooms = list(self.rooms_by_name.keys()) or ["Patio"]
        if character and character.aptitudes & {"Logística escolar"}:
            return self._make_taller_action(rooms)
        if character and character.aptitudes & {"Plan de seguridad"}:
            return self._make_seguridad_action(random.choice(rooms))
        variant = (
            "tutoria_intensiva"
            if character and "Tutoría intensiva" in character.aptitudes
            else "apoyo_rapido"
        )
        return self._make_apoyo_action(rooms, variant=variant)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _extract_action_for(self, char: "Character") -> Optional[Action]:
        if not self.action_heap:
            return None
        best: Optional[Tuple[float, int, Action]] = None
        others: List[Tuple[float, int, Action]] = []
        while self.action_heap:
            base_prio, order, action = heapq.heappop(self.action_heap)
            if not char.can_perform(action):
                others.append((base_prio + 1.2, order, action))
                continue
            if not self._has_resources(action):
                others.append((base_prio + 0.9, order, action))
                continue
            effective = base_prio - char.importance * 0.25
            if action.required_aptitudes and char.aptitudes & action.required_aptitudes:
                effective -= 1.1
            if action.compatibility and char.compatibility & action.compatibility:
                effective -= 0.6
            if self.player_room and action.target_room == self.player_room:
                effective -= 0.4
            candidate = (effective, order, action)
            if best is None or effective < best[0]:
                if best is not None:
                    others.append(best)
                best = candidate
            else:
                others.append(candidate)
        for item in others:
            heapq.heappush(self.action_heap, item)
        if best is None:
            return None
        return best[2]

    def _target_for_action(self, action: Action, character: "Character") -> Optional[Tuple[float, float]]:
        if not character.visible or character.virtual_only:
            return None
        if action.target_room and action.target_room in self.rooms_by_name:
            rect = self.rooms_by_name[action.target_room]["rect"]
            if isinstance(rect, pygame.Rect):
                return rect.center
        return (
            random.uniform(0, max(1, self.world_w - character.rect.w)),
            random.uniform(0, max(1, self.world_h - character.rect.h)),
        )

    def _has_resources(self, action: Action) -> bool:
        for res, cost in action.resource_cost.items():
            if self.resources.get(res, 0.0) < cost:
                return False
        return True

    def _consume_resources(self, action: Action) -> None:
        for res, cost in action.resource_cost.items():
            self.resources[res] = max(0.0, self.resources.get(res, 0.0) - cost)

    def _trigger_defense_event(self) -> None:
        if self.rooms:
            room = random.choice(self.rooms)
            room_name = room.get("name")
        else:
            room_name = "Patio central"
        self.last_event = f"Recordatorio de seguridad en {room_name}"
        count = random.randint(4, 7)
        for _ in range(count):
            self.enqueue_action(self._make_seguridad_action(room_name))
