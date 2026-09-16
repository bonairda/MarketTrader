# MarketTracker

Herramienta personal de seguimiento y análisis de mercados (acciones, forex, cripto).
Backend FastAPI + workers de ingestión, TimescaleDB (solo velas), Redis (precio en vivo, caché, colas).

Ver el diseño completo en `../market-tracker-diseno.md`.

## Estructura

```
market-tracker/
├── backend/            # API FastAPI + worker de ingestión
│   ├── app/
│   │   ├── core/       # config, db, redis, logging
│   │   ├── modules/    # dominios: assets, market_data, watchlists, alerts, ...
│   │   ├── providers/  # adaptadores de proveedores de mercado
│   │   ├── api.py      # router raíz
│   │   ├── main.py     # entrypoint API
│   │   └── worker.py   # entrypoint worker de ingestión
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml  # api + worker + postgres(timescale) + redis, con límites de RAM
└── .env.example
```

## Puesta en marcha (local)

1. Copia la config de entorno:
   ```
   cp .env.example .env
   ```
2. Levanta todo:
   ```
   docker compose up --build
   ```
3. API en http://localhost:8000 — documentación en http://localhost:8000/docs

## Servicios

| Servicio | Puerto | RAM límite |
|----------|--------|-----------|
| api      | 8000   | 512 MB    |
| worker   | -      | 512 MB    |
| db (timescale) | 5432 | 1.5 GB |
| redis    | 6379   | 512 MB    |

## Notas de diseño (resumen)

- **No se persisten ticks.** Los ticks entran en Redis (precio en vivo + vela en curso). A la BD solo van las velas cerradas.
- **Suscripción selectiva:** el worker solo escucha los activos de la watchlist.
- **Cripto en vivo** (Binance WS, gratis) para el MVP; acciones/forex se añaden después.
- Tareas async con ARQ / BackgroundTasks (no Celery).

## Calidad de código (backend)

Lint, formato y tests del backend:

```bash
cd backend
ruff check .          # lint (bloqueante en CI)
black .               # aplica formato (recomendado antes de commitear)
pytest -q             # tests
```

Nota: en CI, `black --check` es informativo (no bloquea). Aplica el formato en
local con `black .` y commitea el resultado para mantener el estilo consistente.
