# Guía de despliegue — MarketTracker

> Cómo ejecutar MarketTracker en local con Docker, cómo funciona el pipeline
> CI/CD y cómo desplegar en producción con Coolify sobre Oracle Cloud, incluidos
> backups, restauración, rollback y operación diaria. Para el detalle de cada
> variable de entorno, consulta la [Guía de configuración](02-guia-de-configuracion.md).

> El runbook operativo original vive en `deploy/COOLIFY_ORACLE_RUNBOOK.md`. Esta
> guía lo resume y organiza; ante cualquier duda de producción, ese runbook es la
> fuente canónica.

## 1. Desarrollo local con Docker (recomendado)

Es la forma más rápida de tener todo el sistema funcionando.

### Requisitos

- Docker y Docker Compose.
- (Opcional) Flutter 3.35.2 si quieres ejecutar la app fuera de contenedor.

### Pasos

```bash
# 1. Copia la plantilla de variables
cp .env.example .env

# 2. Levanta todo el stack
docker compose up --build
```

El fichero `docker-compose.yml` levanta:

| Servicio | Detalle |
|----------|---------|
| `db` | TimescaleDB (PostgreSQL 16) en el puerto `5432`. |
| `redis` | Redis 7 en el puerto `6379`. |
| `migrate` | Ejecuta `alembic upgrade head` una vez y termina. |
| `api` | `uvicorn app.main:app` en el puerto `8000`. |
| `worker` | `python -m app.worker` (sin puerto público). |

`api` y `worker` esperan a que `db` y `redis` estén sanos y a que `migrate`
termine con éxito. Una vez arriba:

- API: <http://localhost:8000>
- Documentación OpenAPI: <http://localhost:8000/docs>
- Salud: <http://localhost:8000/health>

### Ejecutar la app Flutter en local

```bash
cd app
flutter create .        # genera android/ios/web/... conservando lib/ y pubspec
flutter pub get
flutter run             # apunta por defecto a http://localhost:8000
```

Para apuntar a otro host, usa `--dart-define=API_BASE_URL=...`
(ver [Guía de configuración §4.2](02-guia-de-configuracion.md#42-móvil--escritorio-compilación)).

### Comandos útiles del backend (local, dentro de `backend/`)

```bash
ruff check .          # lint (bloqueante en CI)
black .               # aplica formato (recomendado antes de commitear)
pytest -q             # tests (usan fakeredis; asyncio_mode=auto)
alembic upgrade head  # aplicar migraciones manualmente
alembic current       # ver la revisión aplicada
```

## 2. Pipeline CI/CD

El flujo es **GitOps**: GitHub valida y publica imágenes; solo si CI pasa se
dispara el despliegue en Coolify.

```
push/PR a main ──> CI (.github/workflows/ci.yml)
                     │  backend: shellcheck, render compose, pip install,
                     │           alembic upgrade, ruff, black (informativo),
                     │           pytest, build Dockerfile.production
                     │  app:     flutter analyze, test, build web, build Dockerfile.web
                     ▼
        (solo si CI OK en main)
   deploy-coolify.yml (workflow_run)
                     │  verifica SHA = punta de main
                     │  build & push multiarch (amd64+arm64) a GHCR
                     │  dispara webhook de Coolify
                     ▼
                Coolify aplica compose.production.yml  ──> smoke test
```

### `ci.yml`

- **Job backend** (con servicio Postgres/Timescale): valida scripts con
  `shellcheck`, renderiza `compose.production.yml` con `docker compose config`,
  instala dependencias, aplica migraciones, corre `ruff check` (bloqueante),
  `black --check` (informativo, no bloquea), `pytest -q` y construye
  `Dockerfile.production`.
- **Job app** (Flutter 3.35.2): `flutter create .`, `flutter pub get`,
  `flutter analyze`, `flutter test`, `flutter build web --release
  --dart-define=REQUIRE_RUNTIME_CONFIG=true` y build de `Dockerfile.web`.

### `deploy-coolify.yml`

Se dispara con `workflow_run` cuando **CI termina correctamente en `main`**.
Pasos: comprueba que el SHA sigue siendo la punta de `main`, prepara QEMU +
Buildx, verifica que TimescaleDB publica `linux/arm64`, hace login en GHCR,
construye y publica **multiarch** (`linux/amd64,linux/arm64`) las imágenes de
backend y web con los tags `main` y `sha-<commit>`, dispara el webhook de Coolify
y ejecuta `deploy/smoke.sh`.

El **smoke test** espera al release exacto (no acepta la versión anterior):
comprueba `config.json`, `/health/system`, que la revisión coincide, que el
worker está sano y que CORS responde bien; con `SMOKE_EMAIL`/`SMOKE_PASSWORD`
además valida login, `/auth/me` y `/watchlist`.

## 3. Producción: Coolify + Oracle Cloud

Arquitectura resultante (solo `app` y `api` tienen dominio público):

```
Internet ──HTTPS 443──> Coolify / Traefik (Oracle VM)
                          ├── market.<dominio>      -> app  :8080 (Flutter+Nginx)
                          └── api.market.<dominio>  -> api  :8000 (FastAPI)
                                                          │  red privada interna
                                          ┌──────────┬────┴────┬──────────┐
                                     TimescaleDB   Redis    Worker      Backup
                                                          + migrate (one-shot)
```

### 3.1 Antes de empezar necesitas

1. Cuenta de Oracle Cloud y región.
2. Clave pública SSH.
3. Un dominio con DNS editable y dos subdominios: `market.<dominio>` (app) y
   `api.market.<dominio>` (API). Recomendado `coolify.<dominio>` para la consola.
4. El repositorio GitHub del proyecto.
5. (Opcional) credenciales de Twelve Data y Telegram.
6. (Opcional, backups off-host) bucket de OCI Object Storage con Customer Secret
   Key compatible con S3.

> No compartas contraseñas, tokens, claves SSH privadas ni `JWT_SECRET` por chat
> ni por Git. Se introducen en Oracle, GitHub Secrets y Coolify.

### 3.2 Crear la VM Always Free (Oracle)

1. Crea una VCN con Internet Gateway, subnet pública y route table a Internet.
2. Crea una instancia **Ampere A1 ARM64** con Ubuntu LTS ARM64.
3. Asigna el máximo de CPU/RAM Always Free disponible (recomendado ≥ 4 GB;
   12–24 GB evita OOM en pulls/backups). Al menos 100 GB de boot volume.
4. Reserva la IP pública. Adjunta tu clave SSH.

**Reglas de firewall / Security List:**

| Puerto | Origen | Uso |
|--------|--------|-----|
| 22/TCP | Solo tu IP | SSH |
| 80/TCP | `0.0.0.0/0`, `::/0` | HTTP / certificados |
| 443/TCP | `0.0.0.0/0`, `::/0` | HTTPS |
| 8000/TCP | Solo tu IP, temporal | Alta inicial de Coolify |
| 6001–6002/TCP | Solo tu IP, temporal | Realtime/terminal de Coolify por IP |

No abras 5432 ni 6379. El proxy accede internamente.

### 3.3 Instalar Coolify

```bash
sudo -i
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

1. Abre temporalmente `http://<IP>:8000` desde tu IP y crea el usuario admin.
2. Configura `coolify.<dominio>` con HTTPS.
3. Cierra o limita el acceso a 8000/6001/6002 cuando el dominio funcione.
4. Activa MFA si está disponible.
5. Verifica el nombre de la red Docker del proxy (normalmente `coolify`); ese es
   el valor de `COOLIFY_NETWORK`.

### 3.4 DNS

Registros `A` a la IP reservada:

```
market.<dominio>       -> <IP OCI>
api.market.<dominio>   -> <IP OCI>
coolify.<dominio>      -> <IP OCI>
```

Espera propagación antes de pedir certificados. Con Cloudflare, empieza con el
proxy DNS desactivado.

### 3.5 Crear el recurso en Coolify

1. Proyecto `MarketTracker`, environment `production`.
2. Recurso **Docker Compose** desde GitHub, rama `main`, Compose
   `/compose.production.yml`.
3. **Desactiva Auto Deploy on push** (el webhook lo dispara el workflow tras CI).
4. Copia el **deploy webhook** de Coolify.
5. Asigna dominios **solo** a:
   ```
   app -> https://market.<dominio>:8080
   api -> https://api.market.<dominio>:8000
   ```
   No asignes dominio a `db`, `redis`, `migrate`, `worker` ni `backup`.

### 3.6 Variables y secretos en Coolify

Copia las claves de `.env.production.example` y sustituye todos los placeholders.
Genera secretos así:

```bash
openssl rand -hex 32   # POSTGRES_PASSWORD
openssl rand -hex 32   # REDIS_PASSWORD
openssl rand -hex 64   # JWT_SECRET
```

Valores de dominio y seguridad:

```
PUBLIC_API_BASE_URL=https://api.market.<dominio>
CORS_ORIGINS=https://market.<dominio>
ENVIRONMENT=production
DOCS_ENABLED=false
ALLOW_REGISTRATION=false
```

Marca como **secretos**: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `JWT_SECRET`,
`TWELVE_DATA_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`RCLONE_CONFIG_OCI_ACCESS_KEY_ID`, `RCLONE_CONFIG_OCI_SECRET_ACCESS_KEY`.

> Recuerda: el backend permite crear el **primer** usuario aunque
> `ALLOW_REGISTRATION=false`. Créalo de inmediato para cerrar el alta.

### 3.7 Acceso a GHCR

El workflow publica:

```
ghcr.io/<owner>/markettrader-backend:main   (+ sha-<commit>)
ghcr.io/<owner>/markettrader-web:main       (+ sha-<commit>)
```

- Opción sencilla: haz públicos ambos packages en GHCR.
- Opción privada: añade en Coolify un registry GHCR con tu usuario y un PAT con
  permiso `read:packages` (nunca en el repositorio).

### 3.8 Configurar GitHub

En `Settings > Secrets and variables > Actions`:

**Secrets:**
```
COOLIFY_DEPLOY_WEBHOOK=<webhook del recurso Compose>
SMOKE_EMAIL=<usuario de smoke, opcional>
SMOKE_PASSWORD=<password de smoke, opcional>
```

**Variables:**
```
APP_URL=https://market.<dominio>
API_URL=https://api.market.<dominio>
TIMESCALE_IMAGE=timescale/timescaledb
TIMESCALE_TAG=2.16.1-pg16
```

Crea el environment protegido `production` en GitHub (opcionalmente con
aprobación manual).

### 3.9 Primer despliegue (orden correcto)

1. Guarda primero el recurso Compose en Coolify y copia su webhook.
2. Configura variables y secrets en GitHub y en Coolify.
3. Haz push a `main` (o reejecuta el workflow `CI` de la punta actual).
4. Al pasar CI, el workflow publica las imágenes y luego llama a Coolify.
5. Coolify hace pull y levanta el Compose.

### 3.10 Verificar ARM64 de TimescaleDB

El despliegue falla antes de tocar Coolify si el tag no incluye ARM64. Comprueba
en local:

```bash
docker buildx imagetools inspect timescale/timescaledb:2.16.1-pg16
```

Debe aparecer `linux/arm64`. Si no, cambia `TIMESCALE_TAG` por uno compatible en
GitHub y en Coolify.

## 4. Verificación del primer arranque

En Coolify:

1. `db` y `redis`: **healthy**.
2. `migrate`: **exited (0)**.
3. `api`, `worker`, `app`: **healthy**.
4. `backup`: **running**.
5. Sin dominios/puertos en `db`/`redis`.

Pruebas:

```bash
curl -fsS https://market.<dominio>/healthz
curl -fsS https://api.market.<dominio>/health

# En la terminal del worker
python -m app.worker_healthcheck ; echo $?   # 0 = sano

# En la terminal de la API
alembic current
```

Registra el primer usuario propietario y confirma que `ALLOW_REGISTRATION=false`
sigue aplicado.

## 5. Backups

El servicio `backup` hace `pg_dump -Fc`, valida con `pg_restore --list`, calcula
SHA-256, conserva copias locales y, opcionalmente, sube a un destino S3
compatible (OCI Object Storage) con rclone.

Variables clave (ver también [Guía de configuración §3](02-guia-de-configuracion.md#3-variables-de-despliegue-producción--coolify)):

```
BACKUP_INTERVAL_SECONDS=86400
BACKUP_RETENTION_DAYS=30
BACKUP_ON_START=false
RCLONE_REMOTE=oci
RCLONE_DESTINATION=market-tracker-backups/production
RCLONE_CONFIG_OCI_ACCESS_KEY_ID=<access key>
RCLONE_CONFIG_OCI_SECRET_ACCESS_KEY=<secret key>
RCLONE_CONFIG_OCI_ENDPOINT=<endpoint S3 OCI>
RCLONE_CONFIG_OCI_REGION=<region>
```

Probar un backup (en la terminal del contenedor `backup`):

```bash
/opt/markettracker/backup.sh
ls -lh /backups
/opt/markettracker/verify-backup.sh /backups/<archivo>.dump
```

> Un backup no se considera válido hasta que se prueba una restauración. Descarga
> siempre `.dump`, `.dump.sha256` y `.dump.metadata`.

## 6. Restauración (ensayada)

No restaures sobre producción con API/worker escribiendo.

1. Activa mantenimiento y detén `api`/`worker`.
2. Haz un snapshot/backup adicional.
3. Elige el dump y ejecuta en la terminal `backup`:
   ```bash
   CONFIRM_RESTORE=markettracker /opt/markettracker/restore.sh /backups/<archivo>.dump
   ```
4. Ejecuta `alembic upgrade head` desde `migrate` o `api`.
5. Arranca `api`/`worker`.
6. Corre `deploy/smoke.sh` y revisa conteos/auditoría.

Si el log indica que no se pudo cerrar el modo de restauración de Timescale,
ejecuta antes de cualquier otro cambio:

```sql
SELECT timescaledb_post_restore();
```

Ensaya la restauración al menos **trimestralmente**, idealmente en un environment
`restore-test` con `STACK_NAME` distinto.

## 7. Rollback de aplicación

No uses `alembic downgrade` automático.

1. Localiza el último `sha-<commit>` sano en GitHub Packages/Actions.
2. En Coolify cambia `IMAGE_TAG=sha-<commit-completo>` y redespliega.
3. Ejecuta el smoke test.
4. Si la migración no era *backward-compatible*, restaura el backup pre-release en
   una base limpia y luego despliega el SHA anterior.

> El **worker** debe permanecer en **una sola réplica** para no duplicar ingestión
> ni alertas. `api`/`app` pueden escalar más adelante.

## 8. Operación diaria

- Revisa espacio, RAM y estado de volúmenes semanalmente.
- Actualiza Coolify y el sistema con ventana de mantenimiento y backup previo.
- No uses tags `latest`: actualiza versiones deliberadamente. Usa `main` para el
  despliegue habitual y `sha-*` para rollback.
- Revisa logs de migración, worker, watchdog y backups.
- Rota `JWT_SECRET`, contraseñas y tokens ante cualquier exposición.
- Nunca guardes secretos en Compose, Git, logs o capturas.

## 9. Limitaciones conocidas

- El JWT del WebSocket viaja en la query string (conviene un ticket efímero antes
  de una exposición amplia).
- El token web se guarda en almacenamiento accesible por JavaScript: mantén CSP y
  evita XSS.
- Telegram es global, no por usuario.
- Los informes fiscales son un borrador informativo, no asesoramiento.
- La instancia única no ofrece alta disponibilidad regional.

---

_Anterior: [Guía de configuración](02-guia-de-configuracion.md) · Siguiente: [Manual de usuario](04-manual-de-usuario.md)_
