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
| F0 | Cimientos (repos, Docker, esqueleto backend) | En curso |
| F1 | MVP: cripto en vivo + watchlist + velas + 1 alerta | Parcial (backend base hecho, falta alerta y app) |
| F2 | Acciones/forex, indicadores, dashboard | Pendiente |
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

### F1 (para cerrar el MVP)
- [x] **Cliente Flutter** (ordenador + móvil + web): watchlist en vivo (polling REST) + detalle de activo con velas.
      Carpeta `app/` (solo `lib/` + `pubspec.yaml`; las plataformas se generan con `flutter create .`).
- [x] **WebSocket gateway** (`GET /market/ws`): el worker publica ticks en Redis pub/sub
      (`live:ticks`) y el gateway los reenvía a los clientes. La app se conecta por WS con
      reconexión automática y usa polling REST solo como respaldo.
- [x] Módulo de **alertas**: reglas de cruce de precio evaluadas en el worker por cada tick
      (detecta cruce, no nivel; con cooldown por regla), notificación por **Telegram**, y CRUD por API.
      La app permite crear alertas desde el detalle del activo. El worker recarga reglas cada 30 s.
- [ ] **FCM (push móvil)**: hoy las alertas van por Telegram. FCM requiere proyecto Firebase + credenciales.
- [ ] Backfill histórico de velas al añadir un activo a la watchlist.
- [ ] Recargar suscripciones del worker cuando cambia la watchlist (hoy se leen al arrancar).

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

## 5. Posibles mejoras posteriores (deuda técnica / calidad)

- **Migraciones con Alembic**: hoy el esquema se crea con DDL en `db.py`. Migrar a
  Alembic cuando el modelo se estabilice.
- **Tests**: no hay tests aún. Añadir unitarios (agregador de velas, parser de
  Binance, repositorios) y de integración cuando haya más lógica.
- **ORM en vez de SQL crudo**: los repositorios usan `text()`. Valorar modelos
  SQLAlchemy declarativos si el modelo crece.
- **Backpressure**: el worker procesa tick a tick; si un símbolo es muy activo,
  valorar batching de escritura a Redis.
- **Observabilidad**: métricas (Prometheus) y watchdog que avise a Telegram si la
  ingestión deja de recibir datos.
- **Seguridad**: la API no tiene auth todavía (uso personal local). Antes de exponerla,
  añadir JWT + HTTPS + rate limiting.
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
