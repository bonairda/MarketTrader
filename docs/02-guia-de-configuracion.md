# Guía de configuración — MarketTracker

> Referencia completa de todas las variables de entorno del backend y de la app,
> con recomendaciones de seguridad e integraciones opcionales. Para desplegar
> usando esta configuración, ve a la [Guía de despliegue](03-guia-de-despliegue.md).

## 1. De dónde sale la configuración

- **Backend:** todas las opciones se definen en `backend/app/core/config.py`
  (clase `Settings`, basada en `pydantic-settings`). Los valores se leen de
  **variables de entorno** y, en desarrollo, del fichero `.env`. Si una variable
  no está definida, se usa el valor por defecto del propio `config.py`.
- **App Flutter:** en **web** la configuración pública llega en runtime a través
  de `/config.json` (lo genera Nginx a partir de `PUBLIC_API_BASE_URL`); en
  **móvil/escritorio** se pasa con `--dart-define`.

### Plantillas incluidas en el repositorio

| Fichero | Uso |
|---------|-----|
| `.env.example` | Plantilla para **desarrollo local**. Cópiala a `.env`. |
| `.env.production.example` | Plantilla para **producción / Coolify**. No contiene secretos reales. |

```bash
# Desarrollo local
cp .env.example .env
```

> Importante: `.env` no debe subirse al repositorio (contiene secretos). Revisa el
> `.gitignore` antes de commitear.

## 2. Variables del backend

Las tablas siguientes agrupan las variables por área. La columna "Por defecto"
refleja el valor de `config.py` cuando la variable no está presente.

### 2.1 Base de datos (TimescaleDB / PostgreSQL)

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `POSTGRES_USER` | `market` | Usuario de la base de datos. |
| `POSTGRES_PASSWORD` | `market` | Contraseña. **Cámbiala en producción.** |
| `POSTGRES_DB` | `markettracker` | Nombre de la base de datos. |
| `POSTGRES_HOST` | `db` | Host (nombre del servicio en Docker). |
| `POSTGRES_PORT` | `5432` | Puerto. |
| `DATABASE_URL` | — | URL completa alternativa. Si se define, **tiene prioridad** sobre las variables anteriores. Útil con bases de datos gestionadas. Formato: `postgresql+asyncpg://usuario:password@host:5432/basededatos`. |

### 2.2 Redis

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `REDIS_HOST` | `redis` | Host de Redis. |
| `REDIS_PORT` | `6379` | Puerto. |
| `REDIS_PASSWORD` | (vacío) | Contraseña. Vacío = sin autenticación (solo dev). |
| `REDIS_URL` | — | URL completa alternativa (`redis://:password@host:6379/0`). Tiene prioridad si se define. |

### 2.3 API y entorno

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `ENVIRONMENT` | `local` | `local`, `test`, `staging` o `production`. En `production` se activan las validaciones de seguridad. |
| `API_HOST` | `0.0.0.0` | Interfaz de escucha (usada al lanzar uvicorn). |
| `API_PORT` | `8000` | Puerto de la API. |
| `APP_REVISION` | `unknown` | Revisión/commit desplegado (se inyecta en el build). |
| `DOCS_ENABLED` | `true` | Publica `/docs`, `/redoc` y `/openapi.json`. **Ponlo a `false` en producción.** |
| `LOG_LEVEL` | `INFO` | Nivel de logging. |
| `CORS_ORIGINS` | `*` | Orígenes permitidos, separados por coma. `*` = todos (solo dev). En producción debe ser una lista https explícita. |

### 2.4 Autenticación (JWT)

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `JWT_SECRET` | `change-me-in-production` | Secreto de firma. **Debe tener ≥ 32 caracteres aleatorios en producción.** Genera uno con `openssl rand -hex 32`. |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma. |
| `JWT_EXPIRE_MINUTES` | `10080` (7 días) | Caducidad del token de acceso. |
| `ALLOW_REGISTRATION` | `true` | Permite el registro abierto de usuarios. Ponlo a `false` para cerrar el alta tras crear tu usuario. **El primer usuario siempre puede registrarse como *bootstrap*, aunque esté en `false`.** |

### 2.5 Ingestión de mercado

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `CRYPTO_WS_URL` | `wss://stream.binance.com:9443/ws` | WebSocket público de Binance para cripto. |
| `DEFAULT_CRYPTO_SYMBOLS` | `btcusdt,ethusdt` | Símbolos a seguir si todas las watchlists están vacías (minúsculas, estilo Binance). |
| `INGESTION_STALE_SECONDS` | `120` | Segundos sin recibir ticks antes de que el watchdog avise de ingestión caída. |
| `WORKER_HEARTBEAT_TTL_SECONDS` | `30` | TTL del *heartbeat* que Docker/Coolify usa para comprobar la salud del worker. |

### 2.6 Twelve Data (acciones y forex) — opcional

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `TWELVE_DATA_API_KEY` | (vacío) | Clave del plan gratuito de [twelvedata.com](https://twelvedata.com). Si se deja vacía, **solo se ingiere cripto** (Binance). |
| `TWELVE_DATA_POLL_SECONDS` | `60` | Cada cuántos segundos se consulta el precio (el plan gratuito permite ~8 req/min). |

El plan gratuito no tiene WebSocket, por eso se hace *polling* REST.

### 2.7 Tipos de cambio (Banco Central Europeo)

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `ECB_FX_DAILY_URL` | feed diario del BCE | Feed público del cambio de referencia diario a EUR. |
| `ECB_FX_HISTORY_URL` | feed 90 días del BCE | Feed histórico de 90 días. |
| `ECB_FX_CACHE_TTL_SECONDS` | `43200` (12 h) | TTL de la caché de tipos en Redis. |

Se usan para autorrellenar el cambio a EUR de las operaciones. No requieren clave.

### 2.8 Notificaciones (Telegram) — opcional

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `TELEGRAM_BOT_TOKEN` | (vacío) | Token del bot creado con [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_CHAT_ID` | (vacío) | ID del chat o grupo destino. |

Si ambos se dejan vacíos, las alertas y avisos del watchdog **solo se registran en
el log** y no se envían.

### 2.9 Paper trading (Alpaca) — opcional

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `ALPACA_ENABLED` | `false` | Activa la integración de *paper trading*. |
| `ALPACA_API_KEY` | (vacío) | Clave de API de Alpaca. |
| `ALPACA_API_SECRET` | (vacío) | Secreto de API de Alpaca. |
| `ALPACA_BASE_URL` | `https://paper-api.alpaca.markets` | **Host de paper por defecto.** Nunca uses el host de operativa real. |

Es *opt-in*: sin credenciales, queda deshabilitado. Siempre opera contra el
entorno de *paper* (sin dinero real).

## 3. Variables de despliegue (producción / Coolify)

Además de las anteriores, el stack de producción (`compose.production.yml`) usa
variables para identidad del stack, imágenes y backups. Se documentan en detalle
en la [Guía de despliegue](03-guia-de-despliegue.md); aquí un resumen:

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `STACK_NAME` | `market-tracker-production` | Prefijo de volúmenes y redes (usa otro en staging). |
| `COOLIFY_NETWORK` | `coolify` | Nombre de la red externa de Coolify. |
| `BACKEND_IMAGE` | `ghcr.io/bonairda/markettrader-backend` | Imagen del backend en GHCR. |
| `APP_IMAGE` | `ghcr.io/bonairda/markettrader-web` | Imagen de la app web en GHCR. |
| `IMAGE_TAG` | `main` o `sha-<commit>` | Tag desplegado (`main` = auto-deploy; `sha-...` para fijar/rollback). |
| `TIMESCALE_IMAGE` / `TIMESCALE_TAG` | `timescale/timescaledb` / `2.16.1-pg16` | Imagen base de la base de datos. |
| `REDIS_IMAGE` | `redis:7.4-alpine` | Imagen base de Redis. |
| `PUBLIC_API_BASE_URL` | `https://api.market.example.com` | URL pública de la API (la app la lee en runtime). |
| `BACKUP_INTERVAL_SECONDS` | `86400` | Frecuencia del backup automático. |
| `BACKUP_RETENTION_DAYS` | `30` | Días de retención de backups. |
| `BACKUP_ON_START` | `false` | Hacer un backup nada más arrancar. |
| `RCLONE_*` | — | Copia off-host opcional a S3/OCI. |

## 4. Configuración de la app Flutter

### 4.1 Web (runtime)

La imagen web es única para todos los entornos. Nginx genera `/config.json` al
arrancar a partir de estas variables:

| Variable | Descripción |
|----------|-------------|
| `PUBLIC_API_BASE_URL` | **Obligatoria.** URL absoluta de la API (p. ej. `https://api.market.example.com`). |
| `REQUIRE_HTTPS` | Si es `true`, rechaza URLs `http://` (recomendado en producción). |

El build web se compila con `--dart-define=REQUIRE_RUNTIME_CONFIG=true`, lo que
obliga a que exista `config.json` válido y evita apuntar a `localhost` por error.

### 4.2 Móvil / escritorio (compilación)

| Define | Descripción |
|--------|-------------|
| `API_BASE_URL` | URL de la API (por defecto `http://localhost:8000`). |
| `REQUIRE_RUNTIME_CONFIG` | En builds no-web se deja en `false`. |

Ejemplos:

```bash
# Emulador Android (el host de la máquina es 10.0.2.2)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# Dispositivo físico en la red local
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000
```

## 5. Recomendaciones de seguridad

El backend ejecuta `assert_safe_for_production()` al arrancar. Con
`ENVIRONMENT=production` **el arranque falla** si no se cumplen estos requisitos:

- `JWT_SECRET` con al menos **32 caracteres** y que no sea el placeholder por
  defecto ni empiece por `REPLACE_`.
- `CORS_ORIGINS` **no vacío**, sin `*` y con **todos los orígenes en HTTPS**.
- `POSTGRES_PASSWORD` y `REDIS_PASSWORD` **fuertes** (no vacíos, ni `market`, ni el
  placeholder por defecto, ni empezando por `REPLACE_`).

Buenas prácticas adicionales:

- Genera secretos con `openssl rand -hex 32` (o el generador de Coolify).
- Pon `DOCS_ENABLED=false` en producción para no exponer la documentación OpenAPI.
- Cierra el alta con `ALLOW_REGISTRATION=false` tras crear tu usuario.
- Mantén Redis con contraseña (`REDIS_PASSWORD`) y sin puerto público.
- No expongas `db`, `redis`, `worker`, `migrate` ni `backup` a internet: solo
  `app` (8080) y `api` (8000) deben tener dominio público.
- Nunca subas `.env` ni secretos reales al repositorio.

## 6. Comprobar la configuración

- **Salud básica:** `GET /health` (DB + Redis).
- **Salud integral:** `GET /health/system` (además el heartbeat del worker).
  Devuelven `200` si todo está bien y `503` si algo falla.
- **Documentación de la API** (si `DOCS_ENABLED=true`): `http://<host>:8000/docs`.

---

_Anterior: [Guía del proyecto](01-guia-del-proyecto.md) · Siguiente: [Guía de despliegue](03-guia-de-despliegue.md)_
