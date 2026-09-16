# Guía de trading con dinero real — MarketTracker

> **Aviso importante.** Este documento es una **hoja de ruta técnica y de
> seguridad**, no una implementación ni asesoramiento financiero, legal o fiscal.
> Hoy el sistema opera **solo en modo simulado** (*paper trading* con Alpaca).
> Pasar a dinero real es un cambio de gran alcance: no lo actives hasta completar
> las fases 1 a 4 de esta guía. Consulta a un profesional legal/fiscal antes.

## 1. Punto de partida

El proyecto ya integra *paper trading* con Alpaca (ver
[Guía de configuración §2.10](02-guia-de-configuracion.md)):

- `ALPACA_ENABLED=false` por defecto (opt-in).
- `ALPACA_BASE_URL=https://paper-api.alpaca.markets` — **host de práctica**.
- El código usa siempre el host de *paper* para no operar real por accidente, y
  las órdenes ya requieren un `confirm` explícito.

Técnicamente, el cambio mínimo hacia real sería apuntar `ALPACA_BASE_URL` al host
de operativa (`https://api.alpaca.markets`) con credenciales *live*. **Hacer solo
eso sería un error grave**: alrededor de esa línea hay que construir barreras de
seguridad, límites y trazabilidad. Este documento las detalla.

## 2. Decisiones previas (alcance)

Antes de nada, define:

- **¿Para ti o multiusuario?** Operar solo tu propia cuenta es manejable. Operar
  con dinero de terceros entra en **terreno regulado** (custodia, licencias,
  responsabilidad) y normalmente exige asesoramiento legal y una estructura
  adecuada. Esta guía asume, por defecto, **uso personal de una sola cuenta**.
- **¿Qué activos?** Empieza con un universo mínimo y conocido.
- **¿Qué límites de riesgo aceptas?** Importe por orden, exposición total, número
  de órdenes por día.

## 3. Ruta por fases

### Fase 0 — Legal y de cuenta (bloqueante)

- Abrir cuenta **real** en el bróker y pasar su KYC/verificación.
- Revisar implicaciones **legales y fiscales** de operar de forma automatizada en
  tu país. Esto no es asesoramiento; consúltalo con un profesional.
- Registrar quién es el **responsable** de la operativa.

### Fase 1 — Endurecer la seguridad (bloqueante)

Deudas ya identificadas (ver [Guía de despliegue §9](03-guia-de-despliegue.md#9-limitaciones-conocidas))
que se vuelven **críticas** con dinero real:

- **JWT del WebSocket en query string** → sustituir por un *ticket* efímero.
- **Token web accesible por JavaScript** → CSP estricta y revisión de XSS.
- **Rotación de secretos**, MFA en Coolify y acceso restringido por IP/VPN.
- **Credenciales del bróker**: solo como secretos en Coolify, nunca en el
  repositorio ni en logs.

### Fase 2 — Barreras en la operativa (el corazón)

Esto separa un juguete de algo que mueve dinero. Debe implementarse **antes** de
habilitar el modo real:

- **Confirmación reforzada** de cada orden real (doble confirmación y/o
  re-autenticación), más estricta que el `confirm` actual del *paper*.
- **Límites duros en servidor** (no solo en la app): importe máximo por orden,
  exposición máxima, nº de órdenes por día, lista de activos permitidos. Con un
  **tope absoluto** que la app no pueda sobrepasar.
- **Kill switch**: interruptor para detener toda la operativa al instante.
- **Idempotencia**: cada orden con un `client_order_id` único para que un
  reintento no duplique la orden.
- **Modo real explícito y separado de las credenciales**: p. ej.
  `ALPACA_LIVE_TRADING=true`. El arranque debe **avisar en el log** de que está en
  real y, en producción, exigir credenciales *live* válidas.
- **Autorización por rol**: solo `OWNER`/`SUPERADMIN` pueden lanzar órdenes
  reales; nunca `VIEWER`.

### Fase 3 — Trazabilidad y conciliación

- **Auditoría inmutable** de cada orden real (quién, cuándo, qué, resultado).
  Ampliar el `operation_audit_log` existente.
- **Conciliación** periódica: contrastar posiciones, saldos y órdenes del bróker
  con la base de datos, y **alertar** ante cualquier descuadre.
- **Alertas al administrador** por rechazos, errores o límites alcanzados.

### Fase 4 — Pruebas y despliegue gradual

- Probar en **paper** con los mismos límites y flujos que en real.
- **Backtesting realista**: modelar comisiones y *slippage* (hoy el backtest es
  sin comisiones ni *slippage*).
- Empezar en real con **cantidades mínimas** y un solo activo, vigilando.
- Ampliar el universo/importes solo cuando la **conciliación cuadre** durante un
  periodo sostenido.

## 4. El "interruptor" a alto nivel (conceptual)

> Las variables `ALPACA_LIVE_TRADING`, `ALPACA_MAX_ORDER_EUR` y
> `ALPACA_MAX_DAILY_ORDERS` **no existen todavía**: son las que habría que
> implementar en la Fase 2. Se muestran aquí solo para ilustrar el diseño.

```
# Paper (hoy, por defecto y seguro)
ALPACA_ENABLED=true
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_LIVE_TRADING=false

# Real (solo tras completar las fases 1-4)
ALPACA_ENABLED=true
ALPACA_BASE_URL=https://api.alpaca.markets
ALPACA_LIVE_TRADING=true
ALPACA_MAX_ORDER_EUR=100        # tope duro por orden
ALPACA_MAX_DAILY_ORDERS=10      # límite diario
```

Poner `ALPACA_LIVE_TRADING=true` **no es seguro** mientras no estén implementados
los límites, la confirmación reforzada, el kill switch, la idempotencia y la
conciliación.

## 5. Recomendación

- **Uso personal:** viable si completas las fases 1–4 con cuidado y empiezas con
  importes mínimos.
- **Multiusuario / dinero de terceros:** no lo hagas sin asesoramiento legal y,
  probablemente, una entidad/estructura adecuada.
- Explota el *paper trading* como banco de pruebas hasta que el flujo con límites
  esté sólido y la conciliación cuadre.

---

_Anterior: [Manual de usuario](04-manual-de-usuario.md) · Volver al [índice](README.md)_
