# Guía rápida del simulador escolar

Este proyecto es un juego 2D hecho con **pygame** que recrea un campus escolar lleno de misiones, personajes y decisiones. Todo el flujo de actividades está impulsado por un planificador que usa estructuras de datos como `Queue`, `PriorityQueue/heapq`, `deque` y una lista enlazada para dar seguimiento al historial.

## Cómo ejecutar el juego
1. Instala las dependencias (Python 3.10+ recomendado):
   ```bash
   pip install -r requirements.txt
   ```
   > Si no existe un `requirements.txt`, instala `pygame` manualmente: `pip install pygame`.
2. Desde la raíz del repositorio ejecuta:
   ```bash
   python -m STRANGER_THINGS.main
   ```
3. Selecciona tu rol (alumno, maestro o colaborador) y sigue las instrucciones en pantalla.

## Controles principales
| Tecla | Acción |
| ----- | ------ |
| W/A/S/D | Mover al personaje |
| E o ENTER | Interactuar con personas, puertas u objetos |
| Q | Lanzar una "ráfaga" de hasta 100 acciones simultáneas |
| H | Mostrar/Ocultar la ayuda con todos los controles |
| I | Abrir inventario y revisar recursos |
| ESC | Pausar o volver al menú |
| M | Abrir el chat emergente para enviar mensajes |

Al iniciar la partida se muestra un saludo y un resumen con estas teclas. Puedes consultarlas en cualquier momento con **H**.

## Roles y actividades
* **Alumno**: recibe misiones académicas (entregar tareas, estudiar, apoyar a compañeros) y puede subir calificaciones completando actividades.
* **Maestro**: planifica clases, atiende dudas, revisa exámenes y puede mejorar su prestigio académico.
* **Colaborador**: ayuda con logística, cafetería o mantenimiento; mantiene abastecidos los recursos del campus.

El planificador identifica el rol elegido para ajustar las misiones emergentes, los diálogos y las recompensas (salud, hambre, calificaciones o vida social). Al aceptar una actividad aparecen flechas y un autopiloto corto para guiarte hasta el objetivo.

## Cómo funciona el planificador de acciones
1. **Buffer de instrucciones (`Queue`)**: todas las misiones nuevas (emergentes, decisiones del jugador o eventos aleatorios) entran primero en una cola FIFO.
2. **Heap de prioridad (`heapq`)**: las acciones del buffer se extraen y se insertan en un heap que ordena por prioridad, compatibilidad y urgencia. Esto decide qué personajes deben actuar primero.
3. **Rotación de disponibilidad (`deque`)**: los personajes en espera se rotan con un `deque`, así cada uno recibe tareas equilibradamente y se respetan descansos.
4. **Lista enlazada de historial**: cada acción completada se agrega a una lista enlazada simple. El HUD lee esta lista para mostrar los últimos eventos sin usar estructuras costosas.
5. **Acciones activas**: se manejan hasta 100 acciones simultáneas. Cada acción activa incluye un temporizador, progreso y referencia al personaje. Se visualiza con barras y animaciones.
6. **Eventos y recursos**: el planificador vigila recursos (energía, comida, materiales). Si bajan demasiado, genera automáticamente misiones de reabastecimiento.

## Interacciones destacadas
- **Misiones emergentes**: cuando te acercas a un personaje, aparece un popup con las opciones (por ejemplo, "¿Saludar?" con teclas Sí/No). Al aceptar, el planificador asigna la actividad y muestra a los personajes trabajando.
- **Chat emergente**: la tecla **M** abre una ventana flotante en la derecha donde puedes enviar mensajes; los NPC responden de forma dinámica y la conversación se cierra cuando termina.
- **Indicadores visuales**: hay un minimapa, flechas direccionales y ventanas emergentes que explican qué hacer. Los personajes muestran anillos de progreso durante las acciones.
- **Gestión de barras**: salud, hambre, calificaciones y vida social bajan lentamente. Completar misiones según tu rol o aceptar descansos/comedores las recupera. Ignorar tareas hará que algunas barras bajen y, si llegan a cero, la partida termina.
- **Peleas y soporte**: algunas decisiones permiten iniciar discusiones; otras te dejan apoyar a compañeros para acelerar su acción.

## Estructura del proyecto
```
STRANGER_THINGS/
├── core/              # Carga del mapa (TMX, capas de objetos, habitaciones)
├── game/
│   ├── actions.py     # Planificador con Queue + heap + deque + historial enlazado
│   ├── entities.py    # Personajes, roles, IA de movimiento e interacciones
│   ├── ui.py          # HUD, panel izquierdo con scroll, feed inferior, chat emergente
│   └── ...
├── assets/            # Sprites, sonidos y mapas
├── settings.py        # Configuración de pantalla (fullscreen, zoom, minimapa)
└── main.py            # Punto de entrada, bucle del juego y manejo de escenas
```

## Consejos finales
- Revisa el panel inferior para ver qué tecla presionar en cada evento.
- Usa la ráfaga (Q) cuando necesites llenar el campus de actividad rápidamente.
- Mantén equilibradas tus barras haciendo pausas para comer, socializar o estudiar según tu rol.

¡Disfruta explorando el campus y coordinando a todo el equipo! 
