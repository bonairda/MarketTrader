# Estado del proyecto — MarketTracker

> Documento de contexto para retomar el proyecto en cualquier momento.
> Última actualización: F5 completa (autenticación, usuarios/roles y filtrado por usuario).

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
| F2 | Acciones/forex, indicadores, dashboard, tipos de alerta | Completa |
| F3 | Señales, riesgo, mercados llamativos | Completa |
| F4 | Backtesting, cartera/simulación | Completa |
| F5 | Autenticación (JWT), usuarios/roles, filtro por usuario en toda la BD | Completa |
| F6 | Operaciones + fiscalidad (Hacienda, FIFO); integración broker (Alpaca) | Pendiente |

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

### Endpoints disponibles

> Desde F5, **todos los endpoints requieren token JWT** (cabecera
> `Authorization: Bearer <token>`) salvo `GET /health`, `POST /auth/register`,
> `POST /auth/login` y el WebSocket `WS /market/ws` (solo emite ticks públicos).
> Los endpoints de datos personales (watchlist, alertas, cartera, dashboard,
> precios) filtran SIEMPRE por el `user_id` del token.

- `GET /health`
- `POST /auth/register` · `POST /auth/login` · `GET /auth/me` — autenticación (F5)
- `GET /market/prices` — precios en vivo de la watchlist
- `GET /market/prices/{symbol}`
- `GET /market/bars/{symbol}?interval=1m&limit=200`
- `GET /market/indicators/{symbol}?interval=1m&limit=500` — indicadores técnicos (F2)
- `GET /dashboard?fresh=false` — resumen del mercado seguido (F2)
- `GET /signals/{symbol}?interval=1m` — señal + riesgo del activo (F3)
- `GET /backtest/{symbol}?interval=1m&limit=1000` — métricas de la estrategia sobre velas (F4)
- `GET /portfolio` — posiciones valoradas con precio en vivo + resumen P&L (F4)
- `POST /portfolio/positions` · `DELETE /portfolio/positions/{id}` — CRUD de posiciones (F4)
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

### F2 — COMPLETA
- [x] **Indicadores técnicos** (SMA/EMA, RSI, MACD, ATR, Bollinger, retornos) en Python puro
      (`market_data/indicators.py`), calculados bajo demanda vía `GET /market/indicators/{symbol}`
      (`indicators_service.py`). Con tests de valores conocidos y casos borde.
      La app los muestra en el detalle del activo (panel con RSI y su estado, medias, MACD, ATR, Bollinger).
- [x] **Adaptador de acciones/forex** (Twelve Data, plan free -> polling REST, retraso ~15 min).
      Enrutado por prefijo (`providers/symbols.py`): cripto `btcusdt`, acciones `stock:AAPL`,
      forex `fx:EUR/USD`. El worker agrupa por proveedor y lanza un stream por cada uno
      (Binance en vivo + Twelve Data por polling) a la vez. Backfill usa el proveedor correcto.
      Requiere `TWELVE_DATA_API_KEY` en `.env`.
- [x] **Dashboard de inicio** (`GET /dashboard`, caché Redis 10s): resumen de la watchlist
      (cambio %, máx/mín, volatilidad), top movers (subidas/bajadas) y más volátiles.
      Métricas puras en `dashboard/metrics.py` con tests. La app tiene pantalla de Mercado
      con navegación inferior (Mercado / Watchlist).
- [x] **Más tipos de alerta**: además de cruce de precio (`PRICE_CROSS`), ahora hay
      variación porcentual (`PERCENT_CHANGE`) y cruce de indicador (`INDICATOR_CROSS`,
      p. ej. RSI14 por encima de 70). Los de precio se evalúan por tick; los de velas/indicador
      periódicamente en el worker. La app permite elegir el tipo en el diálogo de alerta.

### F3 — COMPLETA
- [x] **Motor de señales por reglas** (BUY/SELL/HOLD/WATCH) con score, confianza y `rationale`
      explicable (RSI + tendencia SMA20/50 + MACD). `GET /signals/{symbol}`. Puro y testeado.
- [x] **Puntuación de riesgo** (volatilidad + drawdown -> 0-100, nivel LOW/MEDIUM/HIGH),
      adjunta a cada señal. La app muestra un panel destacado con acción, fuerza, confianza,
      riesgo y motivos, con aviso de que no es asesoramiento financiero.
- [x] **Detección de "mercados llamativos"**: movimiento atípico, volumen inusual y rupturas,
      evaluados periódicamente en el worker y notificados por los canales configurados
      (con cooldown por símbolo+motivo).

### F4 — COMPLETA
- [x] **Motor de backtesting** puro y sin lookahead (`backtest/engine.py`): recorre las velas
      en orden y en cada paso evalúa la misma estrategia de señales usando SOLO los datos
      disponibles hasta ese momento. Estrategia long-only (entra en BUY, sale en SELL, cierra
      al final). Warmup de 50 velas para los indicadores lentos. Métricas: nº de operaciones,
      win rate, retorno total compuesto, retorno medio por operación y máximo drawdown de la
      curva de equity. Sin comisiones ni slippage (documentado como mejora futura).
- [x] **Endpoint** `GET /backtest/{symbol}` (`backtest/service.py` + `routes.py`) que ejecuta
      el backtest sobre las velas almacenadas.
- [x] **Cartera simulada (manual)**: modelo `Position` (`core/models.py`) + migración
      `0003_positions`. Repositorio CRUD (`portfolio/repository.py`), valoración pura
      (`portfolio/valuation.py`: valor de mercado, coste, P&L absoluto y %) y servicio que
      valora cada posición con el precio en vivo (`portfolio/service.py`). Endpoints
      `GET /portfolio`, `POST /portfolio/positions`, `DELETE /portfolio/positions/{id}`.
- [x] **Tests**: backtesting (`tests/test_backtest.py`: return_pct, warmup insuficiente,
      compuesto, win rate, drawdown, integridad de una serie larga) y valoración de cartera
      (`tests/test_portfolio_valuation.py`: ganancia/pérdida/sin precio y totales del resumen).
- [x] **App Flutter**: botón de backtest en el detalle del activo (diálogo con las métricas
      y aviso de que es un resultado simulado, no asesoramiento) y nueva pestaña **Cartera**
      (lista de posiciones valoradas con P&L, resumen global y alta/baja de posiciones).

### F5 — COMPLETA
- [x] **Autenticación JWT**: `core/security.py` (hash de contraseñas con bcrypt +
      sal aleatoria; creación/validación de tokens JWT HS256 con caducidad).
      Módulo `modules/auth/` con repositorio de usuarios, servicio (registro/login)
      y rutas `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.
- [x] **Usuarios y roles**: modelo `User` (email único, hash, rol, activo) +
      migración `0004_users_and_ownership`. Rol por defecto `OWNER`; dependencia
      `require_role(...)` lista para restringir endpoints por rol en el futuro.
      El registro se puede cerrar con `allow_registration=False` (permite solo el
      primer usuario "bootstrap").
- [x] **Filtro por usuario por defecto en toda la BD de datos personales**: se
      añadió `user_id` a `watchlist_items` (PK compuesta con `asset_id`),
      `alert_rules` y `positions`. TODOS los repositorios de datos personales
      filtran por `user_id`; los borrados/actualizaciones validan la pertenencia
      (devuelven 404 si la fila no es del usuario, sin revelar si existe). Los
      datos de mercado (`assets`, `price_bars`) siguen siendo **compartidos**.
- [x] **Dependencia `get_current_user`**: extrae el usuario del token Bearer y se
      inyecta en cada ruta protegida (401 si falta/caduca, 403 si está desactivado).
- [x] **Worker e ingestión**: al ser un proceso de sistema (sin usuario), ingiere
      la **unión** de las watchlists de todos los usuarios (`list_all_symbols`) y el
      motor de alertas evalúa **todas** las reglas (`list_all_rules`), cada una con su
      `user_id`. Los "mercados llamativos" son condiciones globales de mercado.
- [x] **App Flutter**: pantalla de login/registro, token guardado en
      `SharedPreferences`, envío automático de `Authorization: Bearer` en todas las
      llamadas, y gate de sesión (splash -> login o app). Botón de cerrar sesión.

### F6 — PENDIENTE (siguiente)
- [ ] **Módulo de operaciones + fiscalidad (Hacienda)**: registrar compras/ventas
      (manuales o importadas) sobre la cartera, con cálculo de plusvalías por
      **FIFO** en EUR (incluyendo divisa y tipo de cambio), y export anual para la
      declaración. Base para la trazabilidad fiscal.
- [ ] **Integración con broker (opcional)**: **Alpaca** en modo *paper trading*
      primero (sin dinero real), y solo después operativa real con confirmación
      explícita por orden. Las entidades citadas (CaixaBank, Revolut, Trade Republic)
      **no ofrecen API de trading para terceros**, así que con ellas la vía es
      importar/registrar las operaciones manualmente.
- [ ] Roles adicionales y producto comercial multiusuario.

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
- **Seguridad**: la API ya tiene **auth JWT** (F5). Pendiente antes de exponerla a
  Internet: **HTTPS**, **rate limiting** y rotar `JWT_SECRET` (por variable de entorno;
  el valor por defecto es solo para desarrollo). El WebSocket `/market/ws` aún no
  autentica (solo emite ticks públicos); añadir token por query param si se quiere cerrar.
- **FCM (push móvil)**: hoy las alertas van por Telegram.
- **Config del universo**: hoy el worker lee la watchlist al arrancar; conviene un
  canal (Redis pub/sub) para resuscribir en caliente.
- **Múltiples intervalos de vela**: hoy solo 1m; añadir 5m/1h/1d por agregación.

## 6. Cómo arrancar

```bash
cd market-tracker
cp .env.example .env
# Edita .env y define un JWT_SECRET propio (cadena larga y aleatoria).
docker compose up --build
```

API en http://localhost:8000/docs

Primer uso: registra tu usuario con `POST /auth/register` (el primero es OWNER),
copia el `token` de la respuesta y úsalo como `Authorization: Bearer <token>` en el
resto de llamadas (en Swagger, botón "Authorize"). La app Flutter lo gestiona sola
tras el login.

## 7. Notas de validación

- El código no se ha podido compilar/ejecutar en el entorno de desarrollo actual
  (sin Python funcional ni Docker disponibles). La validación real se hace al
  ejecutar `docker compose up --build`, que instala dependencias y arranca los servicios.
- Versiones fijadas en `backend/requirements.txt` (FastAPI 0.115, Pydantic 2,
  SQLAlchemy async, redis 5, websockets 13).
