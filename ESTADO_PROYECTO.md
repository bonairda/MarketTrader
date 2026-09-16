# Estado del proyecto — MarketTracker

> Documento de contexto para retomar el proyecto en cualquier momento.
> Última actualización: fase F0/F1 inicial (esqueleto de backend).

## 1. Resumen

MarketTracker es una herramienta personal de seguimiento y análisis de mercados
(acciones, forex y cripto) con backend siempre activo, ingestión de datos y, más
adelante, señales explicables y notificaciones push.

El diseño completo está en `../market-tracker-diseno.md`. Este documento describe
qué está hecho, qué se puede mejorar y qué queda pendiente.

Filosofía: proyecto de un solo desarrollador, recursos limitados (~4 GB RAM).
Se prioriza tenerlo funcionando pronto y barato sobre la exhaustividad.

## 2. Estado por fases

| Fase | Descripción | Estado |
|------|-------------|--------|
| F0 | Cimientos (repos, Docker, esqueleto backend) + consolidación (bloques A/B/C) | Completa |
| F1 | MVP: cripto en vivo + watchlist + velas + alertas + app | Completa |
| F2 | Acciones/forex, indicadores, dashboard | Pendiente (siguiente) |
| F3 | Señales, riesgo, mercados llamativos | Pendiente |
| F4 | Backtesting, cartera/simulación | Pendiente |
| F5 | Multiusuario, roles, producto comercial | Pendiente |

## 3. Apartados implementados

### Infraestructura
- `docker-compose.yml` con 4 servicios y límites de RAM:
  - `db` (TimescaleDB/PostgreSQL, 1.5 GB)
  - `redis` (512 MB, `maxmemory-policy allkeys-lru`)
  - `api` (FastAPI, 512 MB)
  - `worker` (ingestión, 512 MB)
- Healthchecks y `restart: unless-stopped`.
- `.env.example` con configuración por variables de entorno.

### Backend (Python / FastAPI)
- **core/**: configuración (`config.py`), logging, cliente Redis, y `db.py`
  (crea esquema mínimo e intenta convertir `price_bars` en hypertable de Timescale).
- **providers/**: contrato común `MarketDataProvider` (`base.py`) y adaptador de
  cripto `BinanceProvider` (`binance.py`) vía WebSocket público, con reconexión
  (backoff + jitter) y suscripción selectiva a los símbolos indicados.
- **modules/market_data/**:
  - `live.py`: precio en vivo en Redis (no en BD).
  - `bars.py`: repositorio de velas (única serie temporal persistida).
  - `aggregator.py`: construye velas de 1m en memoria y las persiste al cerrarse.
  - `routes.py`: endpoints de precios en vivo y velas.
- **modules/watchlists/**: repositorio + endpoints (define el universo suscrito).
- **modules/alerts/**: `repository.py` (CRUD de reglas), `engine.py` (evaluación por tick con
  detección de cruce + cooldown) y `routes.py` (API).
- **modules/notifications/**: `telegram.py` (envío por bot de Telegram; si no está configurado,
  solo registra en log).
- **main.py**: API FastAPI con `/health` y routers de módulos.
- **worker.py**: ingestión (watchlist -> Redis + agregador de velas + motor de alertas).

### Decisiones de diseño ya materializadas en el código
- Los **ticks NO se persisten**: van a Redis; a la BD solo velas cerradas.
- **Suscripción selectiva**: el worker solo escucha los activos de la watchlist.
- **Cripto en vivo gratis** (Binance WS) como punto de partida.
- Sin Celery: async puro (FastAPI/asyncio).

### Endpoints disponibles (F1)
- `GET /health`
- `GET /market/prices` — precios en vivo de la watchlist
- `GET /market/prices/{symbol}`
- `GET /market/bars/{symbol}?interval=1m&limit=200`
- `WS  /market/ws` — stream de precios en vivo (Redis pub/sub -> WebSocket)
- `GET /watchlist` · `POST /watchlist` · `DELETE /watchlist/{asset_id}`
- `GET /alerts` · `POST /alerts` · `PUT /alerts/{id}/enabled` · `DELETE /alerts/{id}`

## 4. Desarrollos pendientes

### F1 — COMPLETA
- [x] **Cliente Flutter** (ordenador + móvil + web): watchlist en vivo + detalle de activo con velas.
      Carpeta `app/` (solo `lib/` + `pubspec.yaml`; las plataformas se generan con `flutter create .`).
- [x] **WebSocket gateway** (`GET /market/ws`): el worker publica ticks en Redis pub/sub
      (`live:ticks`), broadcaster con una suscripción por proceso y fan-out a clientes. La app se
      conecta por WS con reconexión automática y usa polling REST solo como respaldo.
- [x] Módulo de **alertas**: reglas de cruce de precio evaluadas en el worker por cada tick
      (detecta cruce, no nivel; cooldown atómico en Redis), notificación por los canales
      configurados, y CRUD por API. La app crea alertas desde el detalle del activo.
- [x] **Gestión de watchlist desde la app**: añadir (botón +) y quitar (swipe) símbolos.
- [x] **Resuscripción en caliente**: al cambiar la watchlist se publica un evento (`watchlist:changed`)
      y el worker se resuscribe a los nuevos símbolos sin reiniciarse.
- [x] **Backfill histórico**: al añadir un activo se cargan sus velas recientes (Binance klines REST)
      en segundo plano, para tener gráfico desde el primer momento.
- [x] **Abstracción de notificaciones**: interfaz `Notifier` + despachador que envía por todos los
      canales configurados. Telegram implementado; **FCM** dejado como stub documentado.

Pendiente futuro (no bloquea F1):
- [ ] **FCM (push móvil)**: completar `FcmNotifier` (requiere proyecto Firebase + credenciales y
      registro de tokens de dispositivo). La abstracción ya está lista; solo falta la implementación.

### F2
- [ ] Adaptador de acciones/forex (Twelve Data o Polygon), aceptando retraso ~15 min.
- [ ] Indicadores técnicos (SMA/EMA, RSI, MACD, ATR, Bollinger) sobre velas.
- [ ] Dashboard de inicio (estado global, top movers, mapa de calor).
- [ ] Más tipos de alerta (%, volatilidad, volumen, cruce de indicador).

### F3
- [ ] Motor de señales por reglas (BUY/SELL/HOLD/WATCH) con explicación (`rationale`).
- [ ] Puntuación de riesgo.
- [ ] Detección de "mercados llamativos" + push.

### F4 / F5
- [ ] Backtesting y evaluación de señales.
- [ ] Cartera/posiciones (manual/simulado).
- [ ] Autenticación (JWT), roles (OWNER/ANALYST/VIEWER), multiusuario.

## 5. Consolidación de la base (Bloques A, B y C — hechos)

Trabajo de robustez y calidad aplicado sobre F0/F1 para tener una base estable y escalable.

### Bloque A — Correctitud
- [x] **Migraciones con Alembic**: esquema en `alembic/versions/` (migración 0001 con
  hypertable). Modelos declarativos en `core/models.py`. El servicio `migrate` de
  docker-compose aplica `alembic upgrade head` antes de arrancar api/worker.
- [x] **Agregador de velas robusto**: `flush_stale` (cierra velas vencidas aunque no
  lleguen ticks) + `flush_all` (persiste la vela en curso al apagar). Worker con tarea
  de mantenimiento concurrente.
- [x] **Estado de alertas en Redis**: `last_price` y cooldown fuera de memoria;
  cooldown atómico con `SET NX EX` (anti-duplicados, multi-worker, sobrevive reinicios).
- [x] **Tests** (`tests/`): parser de Binance, agregador de velas y motor de alertas
  (con `fakeredis`). Ejecutar con `pytest`.

### Bloque B — Robustez API / operativa
- [x] **CORS** configurable (`CORS_ORIGINS`).
- [x] **Healthcheck real** (`GET /health`): comprueba BD y Redis; devuelve 503 si falla.
- [x] **Errores centralizados** (`core/errors.py`): respuestas consistentes y sin filtrar
  trazas al cliente.
- [x] **Watchdog de ingestión**: avisa por Telegram si no llegan ticks en X segundos
  (`INGESTION_STALE_SECONDS`), y se rearma al recuperarse.
- [x] **WebSocket gateway con broadcaster**: una sola suscripción a Redis por proceso y
  fan-out en memoria a los clientes (escala con muchos clientes; backpressure por cola).

### Bloque C — Tooling / calidad
- [x] **ruff + black** configurados en `pyproject.toml`.
- [x] **CI en GitHub Actions** (`.github/workflows/ci.yml`): lint + tests del backend y
  `flutter analyze` de la app en cada push/PR.

## 6. Mejoras pendientes (deuda técnica / calidad)

- **ORM en vez de SQL crudo**: los repositorios aún usan `text()`. Los modelos
  declarativos ya existen (`core/models.py`); migrar los repos a ORM cuando compense.
- **Backpressure**: el worker procesa tick a tick; si un símbolo es muy activo,
  valorar batching de escritura a Redis.
- **Observabilidad**: métricas (Prometheus).
- **Seguridad**: la API no tiene auth todavía (uso personal local). Antes de exponerla,
  añadir JWT + HTTPS + rate limiting.
- **FCM (push móvil)**: hoy las alertas van por Telegram.
- **Config del universo**: hoy el worker lee la watchlist al arrancar; conviene un
  canal (Redis pub/sub) para resuscribir en caliente.
- **Múltiples intervalos de vela**: hoy solo 1m; añadir 5m/1h/1d por agregación.

## 6. Cómo arrancar

```bash
cd market-tracker
cp .env.example .env
docker compose up --build
```

API en http://localhost:8000/docs

## 7. Notas de validación

- El código no se ha podido compilar/ejecutar en el entorno de desarrollo actual
  (sin Python funcional ni Docker disponibles). La validación real se hace al
  ejecutar `docker compose up --build`, que instala dependencias y arranca los servicios.
- Versiones fijadas en `backend/requirements.txt` (FastAPI 0.115, Pydantic 2,
  SQLAlchemy async, redis 5, websockets 13).
