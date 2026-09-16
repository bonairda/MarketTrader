# Manual de usuario — MarketTracker

> Guía para usar la aplicación MarketTracker paso a paso. No requiere
> conocimientos técnicos. Si buscas instalar o configurar el sistema, consulta la
> [Guía de despliegue](03-guia-de-despliegue.md).

## 1. ¿Qué puedes hacer con MarketTracker?

MarketTracker te permite:

- Seguir precios en vivo de **criptomonedas, acciones y forex**.
- Ver **gráficos de velas** con indicadores técnicos.
- Recibir **alertas** cuando el precio o un indicador cruza un umbral.
- Consultar **señales** de compra/venta orientativas.
- Probar estrategias con **backtesting**.
- Llevar tu **cartera** y un **libro de operaciones** con informe fiscal (FIFO, en euros).
- Registrar **dividendos y splits**.
- Practicar con **paper trading** (órdenes simuladas, sin dinero real).

> Aviso importante: las señales, backtests e informes fiscales son **orientativos
> e informativos**. No constituyen asesoramiento financiero ni fiscal.

## 2. Acceder a la aplicación

Abre la URL de la aplicación en tu navegador (o la app instalada). Verás la
pantalla de **acceso** con el logo de MarketTracker.

### Crear una cuenta

1. Pulsa **"¿No tienes cuenta? Regístrate"**.
2. Introduce tu **email** y una **contraseña de al menos 8 caracteres**.
3. Pulsa **Registrarme**.

Mensajes posibles:

- *"Ese email ya está registrado"* — usa otro email o inicia sesión.
- *"La contraseña debe tener al menos 8 caracteres"* — elige una más larga.
- *"El registro está deshabilitado"* — el administrador ha cerrado las altas
  nuevas. Pide que te den de alta.

### Iniciar sesión

1. Introduce tu email y contraseña.
2. Pulsa **Entrar**.

Si las credenciales no son correctas verás *"Credenciales incorrectas"*. La sesión
se mantiene guardada; si caduca, la app te devolverá automáticamente a esta
pantalla.

## 3. La pantalla principal

Tras iniciar sesión verás una barra de navegación inferior con cuatro secciones:

| Sección | Icono | Para qué sirve |
|---------|-------|----------------|
| **Mercado** | Panel | Resumen del mercado que sigues (dashboard). |
| **Watchlist** | Estrella | Tus activos con precio en vivo. |
| **Cartera** | Cartera | Posiciones y ganancias/pérdidas. |
| **Operaciones** | Flechas | Libro de compras/ventas e informes fiscales. |

El botón de **cerrar sesión** está arriba a la derecha en la sección Mercado.

## 4. Mercado (Dashboard)

Es la pantalla de inicio. Muestra un resumen de los activos que sigues y se
refresca solo cada pocos segundos.

- **Resumen** (arriba): número de activos **Seguidos**, cuántos **Suben** y
  cuántos **Bajan**.
- **Mayores subidas**: los activos con mayor variación positiva.
- **Mayores bajadas**: los de mayor variación negativa.
- **Más volátiles**: los activos con mayor variación de precio (σ).

Cada fila muestra el símbolo, el precio y el porcentaje de cambio (verde si sube,
rojo si baja). **Pulsa cualquier fila** para abrir el detalle del activo.

Desliza hacia abajo para forzar una actualización manual.

## 5. Watchlist (tus activos)

La watchlist es la lista de activos que quieres seguir en vivo. Los precios se
actualizan por WebSocket y, como respaldo, por consultas periódicas.

### Añadir un activo

1. Pulsa el botón **+** (abajo a la derecha).
2. Escribe el símbolo según su tipo:
   - **Cripto:** `btcusdt`, `ethusdt`, …
   - **Acciones:** `stock:AAPL`, `stock:MSFT`, …
   - **Forex:** `fx:EUR/USD`, `fx:GBP/USD`, …
3. Pulsa **Añadir**.

Verás un aviso de confirmación y el activo aparecerá en la lista en cuanto llegue
su primer precio.

> Para que lleguen precios de **acciones o forex**, el administrador debe haber
> configurado la clave de Twelve Data. Sin ella solo funcionan las criptomonedas.

### Quitar un activo

Desliza la fila del activo **hacia la izquierda** y suéltala. Verás un aviso de
confirmación.

### Refrescar

Usa el icono de recarga (arriba a la derecha) o desliza la lista hacia abajo.

### Pulsar un activo

Al tocar un activo se abre su pantalla de **detalle** (siguiente sección).

## 6. Detalle de un activo

Muestra el gráfico, los indicadores y la señal del activo seleccionado.

### Gráfico de velas

- Selecciona el **intervalo** con el desplegable: `1m`, `5m`, `1h` o `1d`.
- Usa el icono de recarga para actualizar.

### Panel de señal

Cuando hay datos suficientes, arriba aparece una tarjeta con la señal:

- **Acción:** COMPRAR, VENDER, VIGILAR o MANTENER.
- **Fuerza** y **Confianza** de la señal.
- **Nivel de riesgo** (bajo/medio/alto) con su puntuación.
- **Motivos** que justifican la señal (lista de razones).

> La señal es cuantitativa y orientativa; **no es asesoramiento financiero**.

### Panel de indicadores

Muestra el valor actual de los principales indicadores técnicos: RSI (14),
SMA 20/50, EMA 20, MACD y su señal, ATR (14) y las bandas de Bollinger. Bajo el
RSI verás una pista de estado: **Sobrecompra**, **Sobreventa** o **Neutral**.

### Crear una alerta (icono de campana)

1. Pulsa el icono de **campana** (arriba a la derecha).
2. Elige el **tipo de alerta**:
   - **Cruce de precio** — avisa cuando el precio cruza un valor.
   - **Variación %** — avisa ante un cambio porcentual (admite negativos).
   - **Cruce de indicador** — avisa cuando un indicador (RSI, SMA 20 o EMA 20)
     cruza un valor.
3. Elige la **dirección**: *Por encima* o *Por debajo*.
4. Introduce el **valor umbral**.
5. Pulsa **Crear**.

Las alertas se evalúan en el servidor de forma continua. Si el administrador
configuró Telegram, además recibirás la notificación por ahí; si no, quedan
registradas.

### Ejecutar un backtest (icono de análisis)

1. Pulsa el icono de **análisis** (gráfica).
2. Espera unos segundos mientras se calcula.
3. Verás un resumen: número de operaciones, % de aciertos, retorno total, retorno
   medio por operación, máximo *drawdown* y velas analizadas.

> El backtest es una simulación histórica **sin comisiones ni slippage**. No
> garantiza rendimientos futuros ni es asesoramiento.

## 7. Cartera

Muestra tus posiciones valoradas y el resultado (P&L). Tiene dos vistas:

- **Cartera derivada** (por defecto): se calcula automáticamente a partir de tu
  libro de operaciones aplicando **FIFO en euros**.
- **Cartera manual**: posiciones que añades a mano.

Puedes cambiar entre ambas vistas y, en la vista manual, **añadir** o **eliminar**
posiciones. Cada posición se valora con el precio en vivo del activo.

## 8. Operaciones (libro fiscal)

El libro de operaciones registra tus **compras y ventas** para tener trazabilidad
y poder calcular la fiscalidad por FIFO. Es independiente de la cartera manual: su
objetivo es el registro y el cálculo, no ejecutar órdenes reales.

Funciones principales:

- **Ver operaciones** con paginación (se cargan más al llegar al final de la lista).
- **Añadir** una operación (compra/venta) con su fecha, cantidad, precio y divisa.
- **Importar / exportar** operaciones (CSV genérico e importadores por *broker*).
- **Eliminar** operaciones.

Desde esta sección también accedes a:

- **Informe fiscal** (ver §9).
- **Eventos corporativos** (ver §10).
- **Paper trading** (ver §11).

El cambio a euros de operaciones en otras divisas se autorrellena con los tipos de
cambio del Banco Central Europeo.

## 9. Informe fiscal anual

Calcula, por año, el resultado fiscal aplicando FIFO.

1. Selecciona el **año**.
2. Consulta el resumen del ejercicio.
3. Pulsa para **copiar el CSV al portapapeles** y pégalo donde lo necesites
   (hoja de cálculo, gestor, etc.).

> El informe es un **borrador informativo**, no asesoramiento fiscal. Contrasta
> siempre con un profesional.

## 10. Eventos corporativos

Registra hechos que afectan a tus posiciones:

- **Dividendos**, con su **retención**.
- **Splits** (desdoblamientos).

Pulsa **añadir** para registrar un evento y elimínalos cuando quieras. Los
importes en otras divisas se convierten a euros con los tipos del BCE.

## 11. Paper trading (simulado)

Permite practicar con órdenes **simuladas** a través de Alpaca, **sin dinero
real**.

- Solo está operativo si el administrador ha configurado las credenciales de
  *paper* de Alpaca. Si no, la pantalla lo indicará como deshabilitado.
- Cuando está activo, puedes ver el **estado**, la **cuenta**, las **posiciones**
  y las **órdenes**, y **crear nuevas órdenes** simuladas.

> El paper trading siempre opera contra el entorno de práctica de Alpaca. Nunca se
> ejecutan órdenes con dinero real.

## 12. Notificaciones (Telegram)

Puedes vincular **tu propio chat de Telegram** para recibir **solo tus** alertas.
Cada usuario tiene su propio chat; no compartes notificaciones con nadie.

**Vincular tu chat:**

1. Entra en **Operaciones → menú (⋮) → Notificaciones**.
2. Pulsa **Generar código**.
3. Abre el **bot de Telegram** del proyecto y envía el comando `/start` con tu
   código (puedes copiarlo con "Copiar comando").
4. El bot te confirmará con un ✅ y volverás a la app; tu chat quedará vinculado.

Desde esa pantalla puedes **pausar** el envío sin desvincular (interruptor) o
**desvincular** el chat cuando quieras.

Qué recibirás en tu chat:

- Los avisos de **tus alertas** de precio e indicadores cuando se cumplen.

Notas:

- Si el administrador no ha configurado el bot, la vinculación no estará
  disponible y la pantalla lo indicará.
- Los avisos de **estado del sistema** (watchdog) van a un canal del
  administrador, no a tu chat personal.
- Si no vinculas Telegram, tus alertas se siguen evaluando y quedan registradas
  en el servidor, pero no recibirás mensajes.

## 13. Administración (solo superadministrador)

Si tu cuenta tiene el rol **SUPERADMIN**, verás un icono de **administración**
(engranaje con escudo) en la parte superior de la pantalla Mercado. Desde ese
panel puedes:

- **Ver** todos los usuarios, con su rol y si están activos.
- **Crear** un usuario nuevo (email, contraseña y rol).
- **Cambiar el rol** de un usuario: `SUPERADMIN`, `OWNER` o `VIEWER`.
- **Activar o desactivar** una cuenta (un usuario inactivo no puede entrar).
- **Borrar** un usuario.

Por seguridad, no puedes quitarte a ti mismo el rol de superadmin, ni
desactivarte ni borrarte a ti mismo (para no dejar el sistema sin administrador).

El superadministrador inicial se define en la configuración del servidor
(`SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`) y se crea automáticamente al arrancar.

## 14. Preguntas frecuentes

**No veo precios de una acción que he añadido.**
Las acciones y el forex requieren que el administrador haya configurado la clave
de Twelve Data. Sin ella, solo funcionan las criptomonedas.

**Me ha echado a la pantalla de login sin hacer nada.**
Tu sesión ha caducado. Vuelve a iniciar sesión; es normal tras varios días.

**El gráfico dice "Sin datos todavía".**
Aún no hay velas suficientes para ese activo e intervalo. Espera a que se acumulen
datos o prueba con un intervalo mayor (por ejemplo `1h`).

**¿Puedo cerrar la app y no perder mis alertas?**
Sí. Las alertas, la watchlist, las operaciones y la cartera se guardan en el
servidor asociadas a tu cuenta.

**¿Las señales me dicen qué comprar?**
No. Son indicadores cuantitativos orientativos. Las decisiones de inversión son
tuyas y deberías contrastarlas.

---

_Anterior: [Guía de despliegue](03-guia-de-despliegue.md) · Volver al [índice](README.md)_
