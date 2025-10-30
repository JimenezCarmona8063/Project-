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
    ) -> None:
        self.characters: List["Character"] = list(characters)
        self.rotation: deque["Character"] = deque(self.characters)
        self.tilemap = tilemap
        self.player = player
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
        self.event_timer = random.uniform(18.0, 28.0)

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

    def get_status_snapshot(self) -> Dict[str, object]:
        active_snapshot = []
        for active in self.active[:8]:
            active_snapshot.append(
                (
                    active.character.name,
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

        for _ in range(32):
            self.enqueue_action(self._make_recolectar_action(room_choices, variant="cosecha"))
        for _ in range(22):
            self.enqueue_action(self._make_recolectar_action(room_choices, variant="caza"))
        for _ in range(16):
            self.enqueue_action(self._make_construir_action(room_choices))

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
            if active.action.variant == "caza":
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
    def _make_recolectar_action(self, rooms: List[str], variant: str = "cosecha") -> Action:
        room = random.choice(rooms) if rooms else None
        if variant == "caza":
            name = f"Caza coordinada en {room or 'exterior'}"
            required = {"Recolectar - Caza"}
            compat = {"naturaleza", "seguridad"}
            cost = {"energia": 8.0, "comida": 6.0}
            duration = random.uniform(10.0, 16.0)
            priority = random.uniform(1.2, 3.2)
        else:
            name = f"Recolectar recursos en {room or 'campus'}"
            required = {"Recolectar"}
            compat = {"naturaleza", "equipo"}
            cost = {"energia": 6.0, "comida": 4.0}
            duration = random.uniform(8.0, 14.0)
            priority = random.uniform(1.6, 3.8)
        return Action(
            name=name,
            category="Recolectar",
            duration=duration,
            priority=priority,
            compatibility=compat,
            required_aptitudes=required,
            resource_cost=cost,
            target_room=room,
            variant=variant,
        )

    def _make_construir_action(self, rooms: List[str]) -> Action:
        room = random.choice(rooms) if rooms else None
        name = f"Construir defensas en {room or 'patio central'}"
        return Action(
            name=name,
            category="Construir",
            duration=random.uniform(12.0, 20.0),
            priority=random.uniform(1.0, 2.4),
            compatibility={"infraestructura"},
            required_aptitudes={"Construir"},
            resource_cost={"energia": 10.0, "materiales": 12.0},
            target_room=room,
        )

    def _make_defensa_action(self, room: Optional[str]) -> Action:
        name = f"Resguardarse en {room or 'zona segura'}"
        return Action(
            name=name,
            category="Defender/Resguardarse",
            duration=random.uniform(6.0, 10.0),
            priority=0.6,
            compatibility={"seguridad", "resguardo"},
            required_aptitudes={"Defender/Resguardarse"},
            resource_cost={"energia": 9.0, "materiales": 6.0},
            target_room=room,
            generated_by_event=True,
        )

    def _make_followup_action(self, character: Optional["Character"] = None) -> Action:
        rooms = list(self.rooms_by_name.keys()) or ["Patio"]
        if character and character.aptitudes & {"Construir"}:
            return self._make_construir_action(rooms)
        if character and character.aptitudes & {"Defender/Resguardarse"}:
            return self._make_defensa_action(random.choice(rooms))
        variant = "caza" if character and "Recolectar - Caza" in character.aptitudes else "cosecha"
        return self._make_recolectar_action(rooms, variant=variant)

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
        self.last_event = f"Alerta en {room_name}"
        count = random.randint(4, 7)
        for _ in range(count):
            self.enqueue_action(self._make_defensa_action(room_name))
