# Revisión rápida de arquitectura — MarketTracker

Fecha: 2026-09-16. Alcance revisado: F0–F6, backend FastAPI, worker, PostgreSQL/
TimescaleDB, Redis, proveedores, notificaciones, Flutter, Docker y CI.

> Revisión estática: en este entorno no hay Python, Flutter ni Docker ejecutables.
> Las conclusiones se basan en trazado de código, contratos y diagnósticos del IDE;
> deben confirmarse con CI y la prueba de integración indicada al final.

## 1. Concordancia funcional

| Área | Fuente de verdad | Consistencia | Resultado |
| --- | --- | --- | --- |
| Usuarios y sesión | PostgreSQL + JWT | `current_user` se resuelve en cada request | Correcto |
| Watchlist | PostgreSQL por `user_id` | Worker ingiere la unión; API/WS filtran por usuario | Correcto |
| Precios en vivo | Redis | REST y WS comparten formato; ticks no se persisten | Correcto |
| Velas e indicadores | Timescale/PostgreSQL | Símbolo canónico común para cripto/stock/forex | Correcto |
| Alertas | PostgreSQL + Redis cooldown | Reglas por usuario; evaluación global eficiente | Parcial: canal Telegram aún global |
| Señales/backtest | Velas almacenadas | Misma estrategia y sin lookahead | Correcto |
| Cartera simulada | `positions` manual | Separada explícitamente del libro fiscal | Correcto, aproximado |
| Operaciones fiscales | `operations` | Decimal, transacción, lock y auditoría | Correcto |
| Informe fiscal | Motor FIFO | JSON y CSV salen del mismo resultado | Correcto con alcance declarado |
| App Flutter | API REST/WS | JWT automático y logout ante 401 | Correcto |

La separación entre datos globales (`assets`, `price_bars`, ticks) y personales
(watchlist, alertas, positions, operations y auditoría) es coherente. Cada consulta
de datos personales incluye `user_id`; las operaciones no aceptan un `userId`
del cliente.

## 2. Sistemas integrados

- **TimescaleDB/PostgreSQL**: velas, usuarios, configuración personal y ledger
  fiscal. Alembic se incluye ya en la imagen Docker y `migrate` bloquea API/worker.
- **Redis**: precios vivos, pub/sub, cooldowns y caché de dashboard. Adecuado para
  estado efímero; no se usa como fuente fiscal.
- **Binance**: cripto en vivo por WebSocket y backfill REST.
- **Twelve Data**: acciones/forex por polling; condicionado por cuota y retraso del plan.
- **Telegram**: notificaciones operativas; configuración única para toda la instancia.
- **Flutter**: web/escritorio/móvil desde una base común; polling de respaldo si cae WS.
- **GitHub Actions**: Ruff, Black informativo, migraciones y prueba concurrente
  contra Timescale/PostgreSQL, pytest, build Docker, `flutter analyze` y `flutter test`.

No existe integración de ejecución real con CaixaBank, Revolut o Trade Republic;
no ofrecen una API pública de trading apropiada para este uso. F6 registra y audita
operaciones, pero **no envía órdenes**. Alpaca paper trading queda propuesto para F7.

## 3. Seguridad y trazabilidad

Fortalezas:

- Contraseñas bcrypt con sal y JWT con caducidad.
- Ownership explícito y respuestas 404 no reveladoras ante recursos ajenos.
- Bloqueo transaccional por usuario/activo para impedir ventas concurrentes sobre
  el mismo saldo FIFO.
- `NUMERIC/Decimal`, constraints e idempotencia por operación externa.
- Auditoría inmutable de CREATE/DELETE con snapshot; el log sobrevive al borrado.
- WebSocket autenticado y filtrado por watchlist.
- La app elimina sesión al recibir 401 en tiempo de ejecución.

Antes de exposición pública:

1. HTTPS obligatorio y secretos desde un gestor (no `.env` en producción).
2. Rate limiting en login, registro, exportación y endpoints costosos.
3. Sustituir JWT largo en query WS por ticket efímero de un solo uso; las URLs
   pueden aparecer en logs de proxy.
4. Guardar token móvil en Keychain/Keystore (`flutter_secure_storage`) en lugar de
   `SharedPreferences`.
5. Cerrar `ALLOW_REGISTRATION` tras crear el propietario y resolver el bootstrap
   de primer OWNER dentro de una transacción para eliminar carreras.
6. Configurar Telegram/FCM por usuario; hoy una alerta conserva `user_id`, pero el
   destino Telegram es global.
7. Añadir política de retención/exportación del audit log y copias de seguridad.

## 4. Escalabilidad

Capacidad actual estimada: adecuada para uso personal o pocos usuarios y un universo
moderado de símbolos dentro de ~4 GB RAM.

Decisiones que escalan bien:

- Ticks en Redis y solo velas cerradas en TimescaleDB.
- Ingestión única para la unión de símbolos, no una conexión por usuario.
- Broadcaster Redis único por proceso y fan-out filtrado.
- Índices `(user_id, ...)` en datos personales y específicos para orden FIFO.
- Caché de dashboard por usuario y cálculos puros sin pandas/ML.
- Advisory lock granular: bloquea un activo de un usuario, no toda la tabla.

Límites previsibles:

- El informe FIFO reconstruye el historial en memoria. Para miles de operaciones
  por usuario es correcto; para millones conviene materializar lotes/snapshots por año.
- Cada cambio de watchlist puede reiniciar streams del proveedor; conviene debounce
  y contador de referencias por símbolo con muchos usuarios.
- Twelve Data free limita el crecimiento de acciones/forex.
- Una sola instancia API/worker y Redis sin HA. Para escalar: múltiples API stateless,
  partición de worker por proveedor/símbolo, Redis administrado y PostgreSQL con backup.
- Consultas SQL crudas son eficientes pero aumentan coste de mantenimiento; conviene
  una capa de unidad de trabajo/repositorio común antes de ampliar mucho el dominio.

## 5. Mejoras priorizadas

### P0 — antes de dinero real o Internet

1. Ampliar las pruebas PostgreSQL ya incluidas con downgrade/upgrade, fallos
   intermedios forzados y más combinaciones de constraints/idempotencia.
2. HTTPS, rate limiting, secretos administrados y ticket WS efímero.
3. Canales de notificación por usuario.
4. Backups cifrados y restauración ensayada de PostgreSQL.
5. Auditoría append-only también para login, cambios de rol e importaciones.

### P1 — calidad y exactitud

1. Fuente automática y auditable de cambio EUR (BCE/broker), conservando valor y fuente.
2. Reglas fiscales adicionales: recompra de valores homogéneos/diferimiento de pérdidas,
   splits, dividendos, traspasos, ampliaciones y clases de activo.
3. Cartera derivada del ledger y valoración multidivisa; retirar gradualmente positions manual.
4. Errores API tipados en Flutter en vez de interpretar texto.
5. `flutter test`, tests de widgets y pruebas contractuales API.
6. Black bloqueante después de formatear la base.
7. Observabilidad: Prometheus, latencias, retraso de ingestión, cuota de proveedores y
   alertas de fallo de migración/backup.

### P2 — rendimiento y experiencia

1. Intervalos 5m/1h/1d materializados, compresión y retención Timescale.
2. Paginación/carga incremental en Flutter y filtros de operaciones.
3. Descarga/compartición nativa del CSV además de copiar al portapapeles.
4. Internacionalización y accesibilidad completa.
5. Sesiones refresh/revocación y gestión de dispositivos.

## 6. Futuros desarrollos

1. **F7 importadores broker**: CSV CaixaBank/Revolut/Trade Republic, mapeo asistido,
   previsualización, conciliación y deduplicación.
2. **Alpaca paper trading**: órdenes simuladas, estado de orden, fills y reconciliación
   con el ledger; kill switch y límites de riesgo.
3. **Interactive Brokers** como alternativa avanzada, solo tras estabilizar paper trading.
4. **Fiscalidad ampliada**: reglas AEAT, dividendos/retenciones, modelo de país fiscal,
   informe de cuentas/activos extranjeros y documentos adjuntos del broker.
5. **Cartera consolidada**: posiciones derivadas, rendimiento TWR/MWR, asignación y
   exposición por moneda/sector.
6. **Notificaciones personales**: Telegram por usuario, FCM y preferencias/canales.
7. **Administración multiusuario**: invitaciones, roles reales OWNER/ANALYST/VIEWER,
   bloqueo/revocación y auditoría de administración.
8. **Analítica avanzada**: costes/slippage en backtest, walk-forward y comparación de
   estrategias; ML solo si existe volumen y una métrica clara.
9. **Operación productiva**: Terraform, despliegue gestionado, HA, SLO, backups y DR.

## 7. Comprobación de integración recomendada

```bash
# 1. Backend completo + migraciones
docker compose up --build

# 2. Tests/lint backend (dentro de backend o contenedor)
pytest -q
ruff check .
black --check .

# 3. Flutter
flutter pub get
flutter analyze
flutter test
```

Smoke test manual:

1. Registrar usuario A y B; comprobar watchlist/WS/cartera/operaciones aislados.
2. Crear dos compras y una venta parcial; comparar informe JSON y CSV.
3. Intentar venta superior al saldo (409) y borrar compra usada (409).
4. Borrar una operación válida y verificar `GET /operations/audit`.
5. Reiniciar todos los contenedores y confirmar persistencia, migración y reconexión.
6. Probar `btcusdt`, `stock:AAPL` y `fx:EUR/USD` en detalle, señales y backtest.
