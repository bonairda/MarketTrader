# Guía del proyecto — MarketTracker

> Documento de referencia para desarrolladores y arquitectos. Describe qué es
> MarketTracker, cómo está construido, cómo fluyen los datos y qué hace cada
> componente. Para configurar el entorno consulta la
> [Guía de configuración](02-guia-de-configuracion.md); para desplegar, la
> [Guía de despliegue](03-guia-de-despliegue.md).

## 1. ¿Qué es MarketTracker?

MarketTracker es una herramienta personal de **seguimiento y análisis de mercados
financieros**. Permite vigilar precios en vivo de criptomonedas, forex y acciones,
generar alertas, analizar señales técnicas, hacer backtesting, llevar un libro de
operaciones con informes fiscales (FIFO, en euros) y operar en modo simulado
(*paper trading*) sin dinero real.

El sistema está pensado para autohospedaje: un único despliegue sirve a uno o
varios usuarios con autenticación propia, y consume proveedores de datos
públicos o de plan gratuito (Binance para cripto, Twelve Data para acciones/forex,
Banco Central Europeo para tipos de cambio).

### Capacidades principales

- **Precios en vivo** vía WebSocket, con respaldo por *polling* REST.
- **Velas históricas** (1m, 5m, 1h, 1d) y gráfico de velas nativo.
- **Watchlists** por usuario: la lista de activos que quieres seguir.
- **Alertas** por cruce de precio, cambio porcentual o cruce de indicadores.
- **Señales** técnicas explicables (votos ponderados de compra/venta).
- **Backtesting** de estrategias sin *lookahead*.
- **Cartera**: posiciones valoradas con precio en vivo y cartera derivada FIFO en EUR.
- **Operaciones**: libro fiscal con importación/exportación e informes anuales.
- **Eventos corporativos**: dividendos (con retención) y splits.
- **Paper trading** con Alpaca (opt-in, siempre contra el entorno de *paper*).
- **Notificaciones** opcionales por Telegram.

## 2. Arquitectura general

MarketTracker es un **mono-repo** con dos artefactos desplegables (backend y app)
apoyados en dos almacenes de datos (TimescaleDB y Redis).

```
                        ┌─────────────────────────────┐
                        │     App Flutter (web)        │
                        │  Nginx sirve el build web    │
                        │  config.json en runtime      │
                        └──────────────┬──────────────┘
                             HTTPS/WSS │ (REST + WebSocket)
                                       ▼
        ┌──────────────────────────────────────────────────────┐
        │                  Backend (Python)                     │
        │                                                        │
        │   ┌──────────────┐        ┌────────────────────────┐  │
        │   │  API FastAPI │        │  Worker de ingestión   │  │
        │   │ (uvicorn)    │        │  (python -m app.worker)│  │
        │   │  REST + WS   │        │  streams + agregación  │  │
        │   └──────┬───────┘        └───────────┬────────────┘  │
        └──────────┼────────────────────────────┼───────────────┘
                   │                             │
          ┌────────▼─────────┐         ┌─────────▼──────────┐
          │   TimescaleDB    │         │       Redis        │
          │ (PostgreSQL)     │         │ precio en vivo,    │
          │ velas cerradas,  │         │ vela en curso,     │
          │ usuarios, etc.   │         │ pub/sub, caché,    │
          │                  │         │ heartbeat          │
          └──────────────────┘         └────────────────────┘
                   ▲                             ▲
                   │                             │  ingestión
                   │                     ┌───────┴──────────┐
                   │                     │ Proveedores      │
                   │                     │ Binance (WS)     │
                   │                     │ Twelve Data (REST)│
                   │                     │ BCE (FX)         │
                   └─────────────────────┴──────────────────┘
```

### Componentes desplegables (servicios)

| Servicio | Comando | Rol | Puerto |
|----------|---------|-----|--------|
| `api` | `uvicorn app.main:app` | API REST + WebSocket, documentación OpenAPI | 8000 |
| `worker` | `python -m app.worker` | Ingesta de precios, agrega velas, evalúa alertas, watchdog | — |
| `db` | TimescaleDB (PostgreSQL) | Persistencia de velas cerradas y datos de usuario | 5432 |
| `redis` | Redis 7 | Precio en vivo, vela en curso, pub/sub, caché, heartbeat | 6379 |
| `migrate` | `alembic upgrade head` | Aplica el esquema y termina (efímero) | — |
| `app` | Nginx + build web | Sirve la app Flutter compilada a web | 8080 |
| `backup` | Script + rclone | Copias periódicas de la base de datos (solo producción) | — |

`api` y `worker` dependen de que `db` y `redis` estén sanos y de que `migrate`
haya terminado correctamente.

## 3. Principios de diseño clave

Estos principios explican decisiones que se repiten por todo el código; conviene
tenerlos claros antes de tocar nada.

### 3.1 Los ticks no se persisten

Los *ticks* (cada precio puntual recibido de un proveedor) **nunca se guardan en
la base de datos**. Viven en Redis como:

- `live:price:<symbol>` — último precio conocido.
- la **vela en construcción** del minuto actual (en memoria del worker + Redis).

A la base de datos solo se escriben **velas cerradas** (OHLCV de 1 minuto), y de
ahí se derivan agregaciones a 5m/1h/1d. Esto mantiene la BD pequeña y la escritura
acotada, y hace que Redis sea la fuente de la verdad para "lo que pasa ahora mismo".

### 3.2 Una sola ingestión para todos los usuarios

El worker no ingesta por usuario. Resuelve el **universo de símbolos** como la
**unión de todas las watchlists** de todos los usuarios (y usa
`DEFAULT_CRYPTO_SYMBOLS` si no hay ninguna). Así una única suscripción sirve a
todos. Cuando alguien añade o quita un activo, se publica un evento en un canal
Redis y el worker **resuscribe en caliente** sin reiniciar el proceso.

### 3.3 Enrutado por proveedor

Cada símbolo se enruta a su proveedor según su prefijo/tipo:

- **Cripto** → `BinanceProvider` (WebSocket público, gratis).
- **Acciones / forex** → `TwelveDataProvider` (*polling* REST, porque el plan
  gratuito no ofrece WebSocket).

El worker agrupa los símbolos por proveedor y lanza un stream por cada uno.

### 3.4 Concurrencia con asyncio (sin Celery)

Todo el procesamiento en segundo plano es **asyncio** dentro de un único proceso
worker. No hay Celery ni un scheduler externo: la periodicidad la gestiona el
propio bucle de mantenimiento del worker. La API usa `BackgroundTasks` y el ciclo
de vida (`lifespan`) de FastAPI para tareas puntuales.

### 3.5 Una imagen web para todos los entornos

La app Flutter web se compila **una sola vez**. La URL de la API **no se
compila**: Nginx la inyecta en runtime en `/config.json` a partir de la variable
`PUBLIC_API_BASE_URL`. La misma imagen sirve para desarrollo, staging y producción.

### 3.6 Arranque seguro en producción

Al iniciar, el backend llama a `assert_safe_for_production()`. Si
`ENVIRONMENT=production`, **impide arrancar** con configuración insegura:
`JWT_SECRET` débil (< 32 caracteres o placeholder), `CORS_ORIGINS` vacío, con `*`
o sin HTTPS, o contraseñas débiles de PostgreSQL/Redis.

## 4. El backend en detalle

Framework: **FastAPI 0.115** sobre **uvicorn**, con **Pydantic 2** y
**pydantic-settings**. Acceso a datos con **SQLAlchemy 2 async** + **asyncpg**,
migraciones con **Alembic**. Autenticación con **PyJWT** + **bcrypt**. Requiere
**Python 3.12+**. Calidad: **ruff** (lint), **black** (formato), **pytest** +
**fakeredis** (tests).

### 4.1 Puntos de entrada

- **`app/main.py`** — crea la aplicación FastAPI (`MarketTracker API`, v0.1.0).
  En su `lifespan` arranca y detiene el `broadcaster` (la única suscripción a
  `live:ticks` por proceso API) y cierra Redis al terminar. Ejecuta
  `assert_safe_for_production()`, configura CORS desde `CORS_ORIGINS`, registra
  los manejadores de error e incluye el router raíz. Expone dos *healthchecks*:
  - `GET /health` — comprueba base de datos y Redis.
  - `GET /health/system` — además comprueba el *heartbeat* del worker.
  Ambos devuelven `503` si alguna dependencia falla.

- **`app/api.py`** — el `api_router` que agrupa los routers de los 12 módulos.

- **`app/worker.py`** — el worker de ingestión (ver sección 6).

### 4.2 Núcleo (`app/core/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `config.py` | `Settings` de pydantic-settings; lee `.env`. Propiedades derivadas (`database_url`, `redis_url`, `crypto_symbols`, `cors_origin_list`) y `assert_safe_for_production()`. |
| `db.py` | Engine async de SQLAlchemy (pool 5 + overflow 5), `SessionLocal`, `get_session()`. |
| `redis_client.py` | Singleton perezoso `get_redis()` (con `decode_responses=True`) y `close_redis()`. |
| `security.py` | `hash_password`/`verify_password` (bcrypt), `create_access_token` (JWT HS256 con `sub`, `role`, `iat`, `exp`), `decode_access_token`. |
| `health.py` | `check_database` (SELECT 1), `check_redis` (ping), `health_report(include_worker=)`. |
| `worker_health.py` | `write_worker_heartbeat` (clave `worker:heartbeat` con TTL) y `worker_is_healthy`. |
| `errors.py`, `logging.py`, `models.py` | Manejo de errores, logging estructurado y modelos/base comunes. |

### 4.3 Proveedores de datos (`app/providers/`)

| Archivo | Rol |
|---------|-----|
| `base.py` | Interfaz `MarketDataProvider` (contrato `stream_ticks`). |
| `binance.py` | `BinanceProvider`: WebSocket público de Binance para cripto. |
| `twelve_data.py` | `TwelveDataProvider`: *polling* REST para acciones y forex. |
| `symbols.py` | `ProviderKind`, `group_by_provider`, `normalize_asset_id`; enrutado por prefijo. |

## 5. Módulos de negocio (`app/modules/`)

Cada módulo agrupa `routes.py` (endpoints), `service.py`/`engine.py` (lógica) y
`repository.py` (acceso a datos) según corresponda. Todos los endpoints, salvo
login y registro, requieren un JWT `Bearer`.

| Módulo | Prefijo | Qué hace | Endpoints destacados |
|--------|---------|----------|----------------------|
| **auth** | `/auth` | Registro, login y validación de sesión. | `POST /register`, `POST /login`, `GET /me` |
| **market_data** | `/market` | Precios en vivo, velas, indicadores y WebSocket. | `GET /prices`, `GET /prices/{symbol}`, `GET /bars/{symbol}`, `GET /indicators/{symbol}`, `WS /ws` |
| **watchlists** | `/watchlist` | Gestión de la lista de activos seguidos. | `GET`, `POST` (201), `DELETE /{asset_id}` (204) |
| **alerts** | `/alerts` | Reglas de alerta por cruce. | `GET`, `POST` (201), `PUT /{rule_id}/enabled`, `DELETE /{rule_id}` (204) |
| **dashboard** | `/dashboard` | Resumen agregado de la watchlist. | `GET` (con `?fresh`) |
| **signals** | `/signals` | Señales técnicas explicables. | `GET /{symbol}` |
| **backtest** | `/backtest` | Backtesting de estrategias. | `GET /{symbol}` |
| **portfolio** | `/portfolio` | Cartera y cartera derivada FIFO. | `GET`, `GET /derived`, `POST /positions` (201), `DELETE /positions/{id}` (204) |
| **operations** | (sin prefijo) | Libro de operaciones e informes fiscales. | `GET/POST /operations`, `GET /operations/export`, `POST /operations/import`, importadores de broker, `GET /tax/reports/{year}` (+ `/csv`) |
| **corporate** | `/corporate-events` | Dividendos (con retención) y splits. | `GET`, `POST` (201), `DELETE /{event_id}` (204) |
| **fx** | `/fx` | Tipos de cambio a EUR (feeds del BCE). | `GET /rate` |
| **paper_trading** | `/paper-trading` | Operativa simulada con Alpaca (opt-in). | `GET /status`, `GET /account`, `GET /positions`, `GET /orders`, `POST /orders` |
| **notifications** | `/notifications` | Telegram por usuario (vincular chat) + envío. | `GET /telegram`, `POST /telegram/link`, `POST /telegram/enabled`, `DELETE /telegram`, `POST /telegram/webhook` |
| **admin** | `/admin` | Gestión de usuarios (solo SUPERADMIN). | `GET /users`, `POST /users` (201), `PUT /users/{id}/role`, `PUT /users/{id}/active`, `DELETE /users/{id}` (204) |

### Detalles de la lógica por módulo

- **alerts** (`engine.py`): motor por **cruce** (no por nivel). Tipos válidos:
  `PRICE_CROSS`, `PERCENT_CHANGE`, `INDICATOR_CROSS`. El worker recarga las reglas
  periódicamente y las evalúa por tick y por vela cerrada.
- **signals** (`engine.py` + `hotmarkets_service.py`): señal explicable con votos
  ponderados de compra/venta y análisis de riesgo bajo demanda. Los "mercados
  llamativos" se evalúan periódicamente con *cooldown* por símbolo y motivo.
- **backtest** (`engine.py`): backtesting **sin lookahead**; en el MVP sin
  comisiones ni *slippage*.
- **portfolio** (`service.py`): valora posiciones con el precio en vivo y calcula
  la **cartera derivada** aplicando FIFO en euros a partir de las operaciones.
- **operations** (`service.py`): libro transaccional de compras/ventas con
  informes fiscales FIFO, importación/exportación (CSV genérico e importadores
  por broker) y registro de auditoría.
- **corporate** (`service.py`): dividendos con retención y splits, con conversión
  FX y resumen fiscal.
- **fx** (`service.py`): tipos de cambio a EUR desde los feeds del BCE (diario e
  histórico de 90 días), con caché en Redis (12 h) y *fallback* al último día hábil.
- **dashboard** (`service.py`): agrega el estado de la watchlist (contadores,
  *top movers*, más volátiles), cacheado en Redis.
- **notifications** (`dispatcher.py`, `telegram.py`, `repository.py`): envío por
  canales. `notify(text, user_id=None)` dirige la alerta al chat de Telegram
  **del usuario** dueño de la regla (bot único del sistema, `chat_id` por usuario
  en `user_telegram_links`); sin `user_id`, usa el chat global (watchdog). La
  vinculación se hace con un código de un solo uso (Redis) y `/start <código>`.
- **admin** (`service.py`): gestión de usuarios restringida a `SUPERADMIN` (crear,
  cambiar rol, activar/desactivar, borrar), con salvaguardas para no auto-
  degradarse/desactivarse/borrarse.

## 6. El worker de ingestión

El worker (`app/worker.py`) es un único proceso asyncio con un **bucle supervisor**
y varias tareas concurrentes:

1. **`_resolve_symbols`** — calcula la unión de watchlists (o los símbolos por
   defecto) y los agrupa por proveedor.
2. **`_ingest`** (una por proveedor) — consume el stream de ticks; por cada tick
   actualiza el precio en vivo en Redis, alimenta el agregador de velas y evalúa
   las alertas por precio.
3. **`_maintenance`** (cada 5 s) — escribe el *heartbeat*, cierra velas vencidas
   (`flush_stale`), evalúa alertas basadas en velas/indicadores y ejecuta el
   *watchdog*. Cada 30 s recarga las reglas de alerta y evalúa los mercados
   llamativos.
4. **`_watch_watchlist`** — escucha el canal Redis de cambios de watchlist y
   dispara la **resuscripción en caliente**.

El **watchdog** (`IngestionMonitor`) registra cuándo llegó el último tick; si
pasan `INGESTION_STALE_SECONDS` sin datos, avisa por notificaciones (si están
configuradas). Al apagar, el worker persiste las velas en construcción
(`flush_all`). Su salud se comprueba con `python -m app.worker_healthcheck`, que
verifica que el *heartbeat* en Redis no haya caducado.

## 7. La app Flutter

Paquete `market_tracker` (v0.1.0). SDK Dart `>=3.4.0 <4.0.0`; Flutter 3.35.2 en
CI. Dependencias: `http`, `intl`, `web_socket_channel`, `shared_preferences`.
Una sola base de código para web, escritorio y móvil.

### 7.1 Arranque y sesión

`main.dart` llama a `AppConfig.initialize()` antes de `runApp`, crea `MarketApi`
y `AuthService`, y usa un `_AuthGate` que decide la pantalla inicial: *splash*
mientras valida el token guardado, `LoginScreen` sin sesión y `HomeScreen` con
sesión válida. Si cualquier llamada recibe un `401`, se hace *logout* y se vuelve
al login.

### 7.2 Configuración (`lib/core/config.dart`)

- **Web:** carga `/config.json` en runtime (lo genera Nginx desde
  `PUBLIC_API_BASE_URL`) y valida que `apiBaseUrl` sea una URL absoluta http/https.
- **Móvil/escritorio:** usa `--dart-define=API_BASE_URL` (por defecto
  `http://localhost:8000`).
- `REQUIRE_RUNTIME_CONFIG=true` fuerza fallo si no puede cargar la config (evita
  apuntar a localhost por error en producción).
- `liveWsUrl` deriva la URL `ws(s)://.../market/ws`; `livePollInterval` = 5 s de
  respaldo si el WebSocket cae.

### 7.3 Servicios (`lib/services/`)

- **`market_api.dart`** (`MarketApi`): cliente HTTP que añade
  `Authorization: Bearer` salvo en login/registro y traduce los `401` a
  `UnauthorizedException`. Cubre todos los endpoints del backend.
- **`auth_service.dart`** (`AuthService`): login/registro/logout, persiste token y
  email en `SharedPreferences`, y valida la sesión con `/auth/me`.
- **`live_stream.dart`** (`LiveStream`): WebSocket a `/market/ws` con el token en
  la query, stream *broadcast* de `LivePrice`, reconexión automática (3 s) y
  `reconnect()` para recargar la watchlist tras altas/bajas.

### 7.4 Pantallas (`lib/screens/`)

| Pantalla | Función |
|----------|---------|
| `login_screen` | Inicio de sesión y registro. |
| `home_screen` | Navegación entre mercado, watchlist, cartera y operaciones. |
| `dashboard_screen` | Resumen: contadores, *top movers*, más volátiles. |
| `watchlist_screen` | Precios en vivo de los activos seguidos. |
| `asset_detail_screen` | Gráfico de velas con selector de intervalo (1m/5m/1h/1d). |
| `portfolio_screen` | Posiciones valoradas y P&L. |
| `operations_screen` | Libro fiscal de compras/ventas (FIFO). |
| `tax_report_screen` | Informe fiscal anual FIFO; CSV al portapapeles. |
| `corporate_events_screen` | Dividendos y splits. |
| `paper_trading_screen` | Órdenes simuladas con Alpaca. |

El gráfico de velas (`lib/widgets/candlestick_chart.dart`) es propio
(`CustomPainter`), sin librerías externas.

## 8. Modelo de datos (migraciones Alembic)

Las migraciones viven en `backend/alembic/versions/` y forman la cadena
`0001 → 0006`:

| Revisión | Cambios |
|----------|---------|
| `0001_initial_schema` | `assets`, `price_bars` (hypertable de Timescale), `watchlist_items`, `alert_rules`. |
| `0002_alert_types` | Añade `indicator` y `timeframe` (default `1m`) a `alert_rules`. |
| `0003_positions` | Tabla `positions` (cartera simulada). |
| `0004_users_and_ownership` | Tabla `users` y `user_id` en watchlist_items (PK compuesta), alert_rules y positions, con índices por usuario. |
| `0005_operations` | `operations` (libro fiscal, índice único parcial por `external_id`) y `operation_audit_log`. |
| `0006_corporate_events` | `corporate_events` (dividendos con retención y splits). |
| `0007_user_telegram_links` | `user_telegram_links` (chat de Telegram por usuario para alertas personales). |

La tabla `price_bars` es una **hypertable de TimescaleDB**, optimizada para series
temporales; solo contiene velas **cerradas**.

## 9. Flujo de datos de extremo a extremo

1. El **worker** se suscribe a la unión de watchlists y recibe *ticks* de Binance
   (cripto) y Twelve Data (acciones/forex).
2. Por cada tick: actualiza `live:price:<symbol>` en Redis, alimenta la vela de 1m
   en construcción y evalúa alertas de precio. Publica el tick en `live:ticks`.
3. Al cerrarse un minuto, la vela se persiste en `price_bars` (TimescaleDB).
4. La **API** mantiene una única suscripción a `live:ticks` (el `broadcaster`) y
   reparte los precios a los clientes conectados por WebSocket, filtrando por la
   watchlist de cada usuario.
5. La **app Flutter** muestra los precios en vivo (WebSocket, con respaldo REST),
   pide velas e indicadores por REST y opera con el resto de módulos.
6. El **watchdog** vigila que sigan llegando ticks y avisa por Telegram si la
   ingestión se detiene.

## 10. Pila tecnológica (resumen)

| Capa | Tecnología |
|------|------------|
| App | Flutter / Dart 3.4+, servida como web tras Nginx |
| API | FastAPI + uvicorn (Python 3.12) |
| Ingestión | Worker asyncio propio |
| ORM / migraciones | SQLAlchemy 2 async + asyncpg + Alembic |
| Base de datos | TimescaleDB (PostgreSQL 16) |
| Caché / tiempo real | Redis 7 |
| Auth | JWT (PyJWT, HS256) + bcrypt |
| Proveedores | Binance (WS), Twelve Data (REST), BCE (FX), Alpaca (paper) |
| Notificaciones | Telegram (opcional), FCM |
| CI/CD | GitHub Actions → GHCR → Coolify (Oracle Cloud) |
| Contenedores | Docker / Docker Compose |

---

_Siguiente: [Guía de configuración](02-guia-de-configuracion.md)_
