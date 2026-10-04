# Pato Pistolero

Juego pixel art hecho con Python y pygame: un pato con pistola dispara a globos, latas, dianas y estrellas.

## Jugar

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python pato.py
```

## Controles

- `A`/`D` o flechas: mover
- Mouse: apuntar, click o `Espacio`: disparar
- `R`: recargar
- `T`: tienda (en los menus)
- `Esc`: salir / volver

## Como se juega

- 10 etapas de 60 s: supera 600 puntos en cada una.
- Tras la etapa 10 hay un jefe final: Astronauta si tienes el fondo Espacio equipado, Granjero con cualquier otro.
- Cada acierto da monedas para comprar skins de pato, arma y fondo en la tienda.
- El progreso se guarda en `.save.json`.

Codigo: `pato.py` (juego), `skins.py` (skins y fondos), `boss.py` (jefes).
