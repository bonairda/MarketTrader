# MarketTracker — Documento de diseño y construcción

> Aplicación personal de seguimiento y análisis de mercados financieros, centrada en acciones y forex, con criptomonedas integradas en el mismo modelo. Disponible en móvil, escritorio y web mediante Flutter, con backend siempre activo, alertas push y señales explicables de recomendación y riesgo.
>
> **Filosofía de ejecución:** proyecto personal, un solo desarrollador, recursos limitados (~4 GB RAM). Se prioriza *tenerlo funcionando pronto y barato* sobre la exhaustividad. Cada decisión de diseño está sesgada hacia bajo coste operativo y bajo mantenimiento.

## 0. Advertencia legal y de datos

MarketTracker es una herramienta personal de análisis. No es un asesor financiero regulado, ni un robo-advisor, ni una garantía de resultados. Las recomendaciones son señales cuantitativas que muestran su fundamento, confianza, horizonte y riesgo, y las interpreta el usuario bajo su responsabilidad.

El mayor coste externo no es la infraestructura, sino el acceso legal a datos bursátiles en tiempo real. Cripto suele ofrecer streaming gratuito; acciones y forex en tiempo real real suelen ser de pago. **En el MVP se asume retraso (~15 min) en acciones/forex** y solo cripto en vivo.

---

## 1. Decisiones de producto cerradas

| Área | Decisión |
|---|---|
| Mercados principales | Acciones y forex |
| Mercados adicionales | Criptomonedas, ETFs e índices bajo el mismo modelo |
| Actualización | Cripto en tiempo real; acciones/forex con retraso (~15 min) en el MVP, sin cambiar arquitectura |
| Cliente | Flutter (Android, iOS, web, escritorio) |
| Notificaciones | Push (FCM) + respaldo Telegram |
| Backend | Python + FastAPI, monolito modular, siempre activo |
| Tareas asíncronas | ARQ o BackgroundTasks de FastAPI (NO Celery en fase inicial) |
| Persistencia de precios | Solo velas cerradas (PriceBar). **Los ticks NO se persisten**, viven en Redis |
| Datos | PostgreSQL + TimescaleDB (solo velas) · Redis (precio en vivo, caché, colas) |
| Hosting | VPS gestionada pequeña (~4 GB RAM) con límites de memoria por contenedor |
| Universo de datos | Controlado: solo se suscribe a los activos de la watchlist activa |

---

## 2. Riesgos críticos asumidos y cómo se mitigan

Estos riesgos son la razón de varias decisiones de diseño. Se documentan para no "olvidarlos" al implementar.

### 2.1 Mantenimiento de WebSockets (el mayor sumidero de tiempo)
Mantener conexiones WS estables con varios proveedores es costoso: desconexiones por inactividad, backpressure en alta volatilidad, cambios de formato sin aviso.

**Mitigación:**
- **Suscripción selectiva**: el worker solo se conecta a los activos de tu watchlist, nunca a "todo el mercado".
- **Aislar cada proveedor** tras un adaptador con contrato común; si uno cambia el formato, se toca un solo archivo.
- **Heartbeat + reconexión con backoff + jitter** y detección de conexión zombie.
- **Backfill por REST** al reconectar para tapar huecos.
- **Empezar solo con cripto** (Binance/Coinbase WS) para validar toda la tubería antes de añadir proveedores más frágiles.

### 2.2 Coste oculto del almacenamiento
Persistir cada tick dispara disco/memoria y arruina cualquier plan barato.

**Mitigación (decisión firme):** **no se persisten ticks.** Los ticks entran en Redis para (a) precio en vivo y (b) construir la vela en curso. A TimescaleDB solo se escriben **velas cerradas** (1m/5m). Esto reduce el almacenamiento ~90%.

### 2.3 Scope creep del dashboard
El dashboard completo es un proyecto en sí mismo; construirlo entero en F1 retrasa meses ver algo funcionando.

**Mitigación:** el dashboard rico se difiere a F2/F3. **F1 = watchlist en vivo + detalle de activo con gráfico.** Nada más.

### 2.4 Presupuesto de memoria (~4 GB RAM)
**Mitigación:** límites de memoria por contenedor en `docker-compose` (ver §12), tareas asíncronas ligeras (ARQ/BackgroundTasks, no Celery), y universo controlado.

---

## 3. Fases de construcción

| Fase | Alcance | Resultado |
|---|---|---|
| **F0 — Cimientos** | Repos, Docker Compose con límites de RAM, CI, modelo base, healthcheck | Entorno desplegable |
| **F1 — MVP mínimo** | Cripto en vivo (1 proveedor WS) + watchlist + detalle de activo con velas + 1 alerta de precio push | App usable en el móvil cuanto antes |
| **F2 — Datos y dashboard** | Añadir acciones/forex (con retraso), indicadores básicos, dashboard de inicio, más tipos de alerta | Herramienta de seguimiento real |
| **F3 — Señales y descubrimiento** | Señales por reglas explicables, riesgo, detección de "mercados llamativos" con push | El "asistente analítico" |
| **F4 — Validación** | Backtesting simple, evaluación de señales, cartera/simulación | Medir si las señales sirven |
| **F5 — Producto** | Multiusuario, roles, planes; foco comercial en descubrimiento + explicabilidad | Apertura a terceros |

> Regla de oro: **F1 debe caber en semanas, no meses.** Si una función no es imprescindible para "ver precios de mi watchlist en vivo en el móvil y recibir una alerta", va a F2 o más allá.

---

## 4. Arquitectura

### 4.1 Enfoque
Monolito modular (API + lógica) + **workers persistentes** para ingestión/análisis. Simple, barato y depurable por una sola persona. Los límites internos por módulo permiten extraer servicios más adelante si hiciera falta.

### 4.2 Vista general

```text
Proveedores
  ├─ Cripto (WebSocket, tiempo real, gratis)      → F1
  ├─ Acciones/Forex (REST/WS económico, ~15m)     → F2
  └─ Noticias/macro (REST/RSS)                     → F3
          │  (solo activos de la watchlist activa)
          ▼
Worker de ingestión (async, ARQ/BackgroundTasks)
  ├─ Adaptador por proveedor (contrato común)
  ├─ Normalización + control de calidad
  ├─ Reconexión (backoff+jitter), heartbeat, backfill
  └─ Publica ticks → Redis
          │
          ▼
Redis  (RAM acotada)
  ├─ Último precio por activo (vivo)
  ├─ Vela en construcción (se agrega en memoria)
  ├─ Pub/Sub → Gateway WebSocket → App
  └─ Cola de tareas / caché de dashboard
          │  (SOLO al cerrar vela)
          ▼
TimescaleDB / PostgreSQL
  ├─ PriceBar (velas cerradas 1m/5m/…)   ← única serie temporal persistida
  ├─ Usuarios, watchlists, alertas
  └─ Señales, riesgo (F3+)
          │
          ▼
API REST + WebSocket gateway  →  App Flutter (Android/iOS/web/escritorio)
          │
          ▼
Notificaciones: FCM (push) + Telegram
```

### 4.3 Punto clave del flujo de datos
- **Tick recibido** → normalizar → actualizar "último precio" en Redis → publicar a Pub/Sub (para la app) → **actualizar la vela en curso en Redis**.
- **Al cerrar la vela** (fin de minuto/5 min) → **escribir 1 fila `PriceBar` en TimescaleDB** y (F3+) recalcular indicadores.
- El tick individual **nunca toca disco**.

### 4.4 Módulos del backend
`auth`, `users`, `assets` (catálogo unificado), `providers` (adaptadores), `ingestion`, `market_data` (velas + snapshot en Redis), `indicators` (F2+), `signals` (F3+), `risk` (F3+), `discovery` (F3+), `watchlists`, `alerts`, `notifications`, `dashboard` (F2+), `admin` (salud de fuentes).

---

## 5. Stack tecnológico

### 5.1 Backend
- **Python 3.12+ / FastAPI** (REST + WebSocket async nativo).
- **Tareas async: ARQ** (ligero, sobre Redis) o **BackgroundTasks** de FastAPI para lo simple. **No Celery** en fase inicial (consumo de RAM por worker demasiado alto para 4 GB).
- **asyncio** para las conexiones de mercado.
- **pandas / NumPy** (y pandas-ta o TA-Lib) para indicadores, en F2+.
- SQLAlchemy + Alembic.

### 5.2 Datos e infraestructura
- **TimescaleDB (PostgreSQL)**: hypertable **solo para `PriceBar`**. Compresión de velas antiguas.
- **Redis**: precio en vivo, vela en curso, Pub/Sub, cola ARQ, caché dashboard. **Límite de memoria configurado** (ver §12).
- **Docker** con límites de memoria por servicio.

### 5.3 Cliente
- **Flutter** (una base de código). Riverpod para estado. Dio para REST. Cliente WS con reconexión. Drift/Hive para caché offline. `firebase_messaging` para push. Librería de velas encapsulada tras interfaz propia.

### 5.4 Notificaciones
- **FCM** (push, gratis, multiplataforma) + **Telegram bot** (respaldo/instantáneo) + email opcional (F3+) para resúmenes.

---

## 6. Modelo de datos

### 6.1 Asset (unificado)

```text
Asset
  id, symbol, name, type(STOCK|ETF|INDEX|FX|CRYPTO),
  exchange?, providerSymbols(jsonb), baseCurrency?, quoteCurrency,
  sector?, timezone, priceDecimals, isActive
```
- Acción: `AAPL` / quote USD. FX: `EUR/USD` (base+quote). Cripto: `BTC/USDT`.

### 6.2 Datos de mercado

```text
# EN REDIS (no en disco):
LivePrice (Redis hash)   -> assetId -> { price, bid, ask, ts, status }
BuildingBar (Redis)      -> vela en curso por asset+interval

# EN TIMESCALEDB (hypertable, único dato temporal persistido):
PriceBar
  assetId, interval(1m|5m|1h|1d), openTime, open, high, low, close, volume?

# EN TIMESCALEDB (F3+):
IndicatorValue
  assetId, interval, timestamp, indicator, parametersHash, value
```

> Nota de diseño: no existe tabla `PriceTick`. Fue eliminada a propósito. Si en el futuro se quisiera HFT (fuera de alcance), se reevaluaría.

### 6.3 Usuario, seguimiento, alertas, señales

```text
User(id, email, passwordHash, displayName, role, timezone, settings)
Device(id, userId, platform, fcmToken, lastSeenAt, isActive)
Watchlist(id, userId, name, isDefault)
WatchlistItem(watchlistId, assetId, addedAt, notes)   ← define el universo suscrito
Portfolio(id, userId, name, baseCurrency)              ← F4, manual/simulado
Position(id, portfolioId, assetId, quantity, averagePrice, source)

Signal(id, assetId, createdAt, horizon, action, score, confidence,
       riskScore, strategyVersion, rationale, expiresAt, status)     ← F3+
RiskSnapshot(assetId, timestamp, horizon, volatility, drawdown,
             liquidityRisk, eventRisk, totalScore, explanation)      ← F3+
HotMarket(id, assetId, detectedAt, score, reason, expiresAt, notified) ← F3+

AlertRule(id, userId, assetId?, type(PRICE_MOVE|NEW_HOT_MARKET|SIGNAL|CUSTOM),
          condition(jsonb), channels, cooldownSeconds, enabled, lastTriggeredAt)
AlertEvent(id, ruleId, assetId, triggeredAt, payload, deliveryStatus)
```

---

## 7. Ingestión (barata y controlada)

### 7.1 Estrategia por fases
- **F1 — Cripto en vivo**: WebSocket de Binance/Coinbase (gratis). Valida toda la tubería streaming → vela → Redis → app → push.
- **F2 — Acciones/Forex económicos**: Twelve Data o Polygon.io (planes gratuitos/baratos). **Se acepta retraso ~15 min**; para análisis horario/diario personal no arruina la estrategia. La arquitectura no cambia (el adaptador entrega ticks o barras; el resto es igual).

### 7.2 Suscripción selectiva (regla firme)
El worker **solo se suscribe a los activos presentes en la watchlist activa**. Nada de suscribirse a todo el mercado. Al añadir/quitar de la watchlist, se actualizan las suscripciones y se hace backfill del histórico necesario.

### 7.3 Contrato de adaptador
```text
MarketDataProvider:
  connect() / disconnect()
  subscribe(symbols) / unsubscribe(symbols)
  streamTicks()                     # o polling REST en proveedores con retraso
  fetchHistoricalBars(asset, interval, from, to)
  fetchAssetMetadata(query)
  health()
```

### 7.4 Resiliencia
Reconexión exponencial con jitter, heartbeat, detección de zombie, backfill de huecos por REST, idempotencia por `(assetId, interval, openTime)` en velas, estado de frescura `LIVE|DELAYED|STALE|UNAVAILABLE` visible en la UI, circuit breaker por proveedor, backpressure controlado.

---

## 8. Análisis, señales y descubrimiento (F2–F3)

### 8.1 Indicadores (F2)
SMA/EMA (20/50/200), MACD, RSI, ATR, Bollinger, volumen relativo, retornos (1h/1d/1w/YTD), máx/mín 52s; en FX: fuerza relativa de divisa, correlación de pares, spread. Se calculan sobre **velas** (que es lo que se persiste), no sobre ticks.

### 8.2 Mercados llamativos (F3) — la fortaleza diferencial
Escanea el universo buscando anomalías (volumen ×N sobre su media, movimiento de N desviaciones, ruptura de máximos/mínimos, aceleración de momento, correlación inusual). Genera un `HotMarket` y **notifica por push/Telegram**, incluso de activos que no sigues. Cada hallazgo explica: qué pasó, en qué ventana, cuánto se desvía de lo normal, y su riesgo.

### 8.3 Señales explicables (F3)
`action` (BUY/SELL/HOLD/WATCH), `score`, `confidence` (distinta del score), `riskScore`, `expiresAt`, `strategyVersion`, y **explicación humana**. Ejemplo del tipo de push que aporta valor comercial futuro:

```text
WATCH — Apple (AAPL) — horizonte intradía
Score 78 · Confianza 66 · Riesgo BAJO
- Volumen relativo ×3 en los últimos 15 min
- Ruptura de resistencia histórica
- Volatilidad macro baja → riesgo contenido
```

### 8.4 ML (F4+)
Solo cuando haya histórico etiquetado y backtesting con validación temporal (sin data leakage). Primeros modelos simples y comparables con una regla base.

---

## 9. Cliente Flutter y UX

### 9.1 F1 (mínimo)
- **Watchlist en vivo**: lista de activos con precio, cambio y estado de frescura.
- **Detalle de activo**: gráfico de velas + selección de intervalo.
- **1 tipo de alerta**: cruce de precio, con push.

### 9.2 Dashboard rico (F2/F3 — diferido a propósito)
Estado global del mercado, "dónde está el dinero" (mapa de calor), top movers, mercados llamativos, señales activas, insights automáticos, alertas recientes. Todo precomputado en backend y cacheado en Redis; en vivo por WebSocket.

### 9.3 Transversal
Diseño adaptativo (móvil/tablet/escritorio), accesibilidad AA, offline (último estado conocido), y **frescura del dato siempre visible** (LIVE/DELAYED/STALE).

---

## 10. API (contrato inicial)

```text
Auth:      POST /auth/login · POST /auth/refresh
Live:      WS   /ws/stream            # precios + (F3) señales/hot-markets
Assets:    GET  /assets?query=&type=  · GET /assets/{id}
           GET  /assets/{id}/bars?interval=1m&from=&to=
Watchlist: GET/POST /watchlists · POST/DELETE /watchlists/{id}/items[/{assetId}]
Alerts:    GET/POST/PUT/DELETE /alerts
Devices:   POST /devices/register     # token FCM
Dashboard: GET  /dashboard            # F2+
Signals:   GET  /signals · GET /signals/{id}     # F3+
HotMarkets:GET  /hot-markets?since=              # F3+
```

---

## 11. Perfiles y seguridad (diseñado, activado en F5)
- Roles: **OWNER** (tú), **ANALYST**, **VIEWER**.
- JWT (access+refresh), autorización por rol en endpoints, aislamiento de datos por usuario, secretos (API keys de proveedores) en variables de entorno/gestor de secretos, HTTPS, rate limiting.
- En F1 basta login simple, pero `User.role` y el middleware ya se dejan puestos.

---

## 12. Hosting y presupuesto de ~4 GB RAM

Backend siempre activo con conexiones WS persistentes → **contenedor 24/7**, no serverless puro. VPS gestionada pequeña y económica (p. ej. Hetzner/Fly.io/Railway/Render según coste).

### 12.1 Reparto de memoria orientativo (4 GB)
| Servicio | Límite RAM | Nota |
|---|---|---|
| PostgreSQL/TimescaleDB | 1–1.5 GB | Solo velas; `shared_buffers` ajustado |
| Redis | ≤ 512 MB | `maxmemory 512mb` + `maxmemory-policy allkeys-lru` |
| API FastAPI | ~512 MB | 1–2 workers uvicorn |
| Worker ingestión | ~512 MB | async, universo controlado |
| Sistema / margen | resto | monitorización, picos |

### 12.2 `docker-compose` (pautas)
- `mem_limit`/`deploy.resources.limits.memory` por servicio.
- Redis: `--maxmemory 512mb --maxmemory-policy allkeys-lru`.
- Postgres: `shared_buffers`, `work_mem` y `max_connections` moderados.
- Sin Celery: ARQ comparte el Redis existente; los `BackgroundTasks` de FastAPI para lo trivial.
- Reinicio automático (`restart: unless-stopped`) + healthchecks.

### 12.3 Resiliencia operativa
Watchdog que avisa a Telegram si la ingestión deja de recibir datos, backups diarios de Postgres, compresión de velas antiguas, degradación elegante si un proveedor cae.

---

## 13. Camino a producto (F5) — dónde está el valor comercial
No competir con TradingView en gráficos. La ventaja es el **sistema de descubrimiento + explicabilidad**: alertas push estructuradas y accionables ("volumen ×3 en 15 min + ruptura de resistencia + riesgo bajo"). El producto se vende como **asistente analítico personalizable**, no como otro visor de gráficos.

---

## 14. Resumen ejecutivo
- **Monolito modular Python/FastAPI + workers async**, TimescaleDB **solo para velas**, Redis para vivo/caché/colas, Flutter multiplataforma, push FCM/Telegram.
- **Decisiones anti-coste/anti-mantenimiento (firmes):** no persistir ticks; cripto en vivo y acciones/forex con retraso en el MVP; suscripción selectiva a la watchlist; ARQ/BackgroundTasks en vez de Celery; límites de RAM por contenedor para caber en 4 GB.
- **Anti scope creep:** F1 = watchlist en vivo + detalle de activo + 1 alerta. El dashboard rico y las señales se difieren.
- **Diferencial futuro:** descubrimiento de "mercados llamativos" + explicabilidad, entregado por push.
```
