# Despliegue MarketTracker — Oracle Cloud Always Free + Coolify

Este runbook prepara un entorno GitOps: GitHub valida y publica imágenes ARM64 en
GHCR; solo si CI termina correctamente se llama al webhook de Coolify, que aplica
`compose.production.yml` en Oracle Cloud.

## 1. Arquitectura resultante

```text
Internet
   |
   | HTTPS 443
   v
Coolify / Traefik (Oracle VM)
   |---------------------------|
   |                           |
market.example.com       api.market.example.com
   | :8080                     | :8000
Flutter + Nginx               FastAPI
                                  |
                        red privada interna
                    /        |        |        \
             TimescaleDB   Redis    Worker    Backup
                                  + migrate one-shot
```

Solo `app` y `api` tienen dominio. PostgreSQL, Redis, worker, migraciones y
backups no publican puertos al host.

## 2. Información que necesitas proporcionar

Antes del primer despliegue hacen falta:

1. Cuenta Oracle Cloud y región elegida.
2. Clave pública SSH para crear la VM.
3. Dominio propio y capacidad para editar DNS.
4. Dos subdominios públicos:
   - `market.<tu-dominio>` para Flutter.
   - `api.market.<tu-dominio>` para FastAPI.
5. Recomendado: `coolify.<tu-dominio>` para la consola, restringido a tu IP/VPN.
6. Confirmar que usarás el repositorio GitHub `bonairda/MarketTrader`.
7. Credenciales opcionales ya existentes:
   - Twelve Data.
   - Telegram.
8. Para backups externos: bucket OCI Object Storage, namespace/región y una
   Customer Secret Key compatible con S3.

No compartas passwords, tokens, claves SSH privadas ni `JWT_SECRET` por chat o
Git. Se introducen directamente en Oracle, GitHub Secrets y Coolify.

## 3. Crear la VM Always Free

En Oracle Cloud:

1. Crea una VCN con Internet Gateway, subnet pública y route table a Internet.
2. Crea una instancia **Ampere A1 ARM64** con Ubuntu LTS ARM64.
3. Asigna el máximo de CPU/RAM que tu tenancy marque como Always Free y tenga
   disponible. Para este stack se recomiendan al menos 4 GB; 12–24 GB evita OOM
   durante pulls, backups y operación de Coolify.
4. Usa al menos 100 GB de boot volume si entra en tu cuota gratuita.
5. Reserva la IP pública para que no cambie al reiniciar.
6. Adjunta tu clave pública SSH.

Las instancias A1 son ARM; la documentación oficial de OCI describe esta familia
como Arm-based compute: [OCI Arm Compute](https://docs.oracle.com/iaas/Content/Compute/References/arm.htm).

### Reglas NSG/Security List

| Puerto | Origen | Uso |
| --- | --- | --- |
| 22/TCP | Solo tu IP pública | SSH |
| 80/TCP | `0.0.0.0/0`, `::/0` | HTTP / certificados |
| 443/TCP | `0.0.0.0/0`, `::/0` | HTTPS |
| 8000/TCP | Solo tu IP, temporal | Alta inicial Coolify |
| 6001–6002/TCP | Solo tu IP, temporal | Realtime/terminal Coolify por IP |

No abras 5432, 6379 ni el 8000 de FastAPI. El proxy accede internamente. Coolify
indica que 80/443 son necesarios para dominios y que 8000/6001/6002 se usan al
acceder directamente por IP: [Coolify firewall](https://coolify.io/docs/knowledge-base/server/firewall).

## 4. Instalar Coolify

Conecta por SSH como usuario con sudo y ejecuta el instalador oficial:

```bash
sudo -i
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Coolify recomienda una máquina Linux fresca y soporta `arm64`; sus mínimos son
2 CPU, 2 GB RAM y 10 GB: [instalación self-hosted](https://coolify.io/docs/get-started/installation/).

1. Abre temporalmente `http://<IP>:8000` desde tu IP.
2. Crea inmediatamente el usuario administrador.
3. Configura `coolify.<tu-dominio>` y HTTPS.
4. Cuando el dominio funcione, cierra el acceso público a 8000/6001/6002 o
   mantenlo limitado a tu IP.
5. Activa MFA si tu versión de Coolify lo permite.
6. Comprueba que la red Docker del proxy se llama `coolify`; si usa otro nombre,
   ese será el valor de `COOLIFY_NETWORK`.

Coolify crea las rutas de Traefik y certificados TLS al asignar dominios:
[proxy y TLS](https://coolify.io/docs/core/networking/proxy/traefik/overview).

## 5. Configurar DNS

Crea registros `A` hacia la IP reservada:

```text
market.<tu-dominio>       -> <IP OCI>
api.market.<tu-dominio>   -> <IP OCI>
coolify.<tu-dominio>      -> <IP OCI>
```

Espera la propagación antes de pedir certificados. Si usas Cloudflare, empieza
con proxy DNS desactivado hasta verificar Coolify/Let's Encrypt.

## 6. Preparar el proyecto en Coolify

1. Crea proyecto `MarketTracker` y environment `production`.
2. Añade un recurso **Docker Compose** desde GitHub.
3. Conecta el repositorio `bonairda/MarketTrader` y rama `main`.
4. Indica el Compose: `/compose.production.yml`.
5. Guarda el recurso, pero no es necesario que el primer deploy funcione aún:
   GHCR todavía puede no contener imágenes.
6. Desactiva **Auto Deploy on push**. El workflow GitHub llamará al webhook solo
   después de que CI pase; así un push roto nunca llega al servidor.
7. Copia el deploy webhook de Coolify. GitHub Actions puede publicar imágenes y
   disparar Coolify después de validar: [Coolify + GitHub Actions](https://coolify.io/docs/applications/sources/github/actions).

### Dominios por servicio

En la configuración del Compose asigna únicamente:

```text
app -> https://market.<tu-dominio>:8080
api -> https://api.market.<tu-dominio>:8000
```

El sufijo indica el puerto interno de destino; externamente se usa HTTPS 443.
Coolify documenta que para servicios que no escuchan en 80 debe indicarse el
puerto en el dominio: [Docker Compose domains](https://coolify.io/docs/knowledge-base/docker/compose/).

No asignes dominios a `db`, `redis`, `migrate`, `worker` ni `backup`.

## 7. Variables y secretos de Coolify

Copia las claves de `.env.production.example` en Environment Variables. Sustituye
todos los placeholders. Genera secretos en tu equipo, por ejemplo:

```bash
openssl rand -hex 32   # password DB
openssl rand -hex 32   # password Redis
openssl rand -hex 64   # JWT_SECRET
```

Valores de dominio:

```text
PUBLIC_API_BASE_URL=https://api.market.<tu-dominio>
CORS_ORIGINS=https://market.<tu-dominio>
ENVIRONMENT=production
DOCS_ENABLED=false
```

Marca como secretos:

```text
POSTGRES_PASSWORD
REDIS_PASSWORD
JWT_SECRET
TWELVE_DATA_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
RCLONE_CONFIG_OCI_ACCESS_KEY_ID
RCLONE_CONFIG_OCI_SECRET_ACCESS_KEY
```

Mantén desde el primer arranque:

```text
ALLOW_REGISTRATION=false
```

El backend permite crear el primer usuario aunque el registro general esté
cerrado; después bloquea nuevas altas. Crea el propietario inmediatamente. En
una evolución posterior conviene sustituir este bootstrap público por un token
de un solo uso.

### Acceso a GHCR

El workflow publica:

```text
ghcr.io/bonairda/markettrader-backend:main
ghcr.io/bonairda/markettrader-web:main
```

y versiones inmutables `sha-<commit-completo>`.

- Opción sencilla: configura ambos packages GHCR como públicos.
- Opción privada: añade en Coolify un registry GHCR con usuario GitHub y PAT con
  permiso `read:packages`; nunca guardes el PAT en el repositorio.

## 8. Configurar GitHub

En `Settings > Secrets and variables > Actions`:

### Secrets

```text
COOLIFY_DEPLOY_WEBHOOK=<webhook del recurso Compose>
SMOKE_EMAIL=<usuario de smoke opcional>
SMOKE_PASSWORD=<password del usuario smoke opcional>
```

### Variables

```text
APP_URL=https://market.<tu-dominio>
API_URL=https://api.market.<tu-dominio>
TIMESCALE_IMAGE=timescale/timescaledb
TIMESCALE_TAG=2.16.1-pg16
```

El workflow `.github/workflows/deploy-coolify.yml`:

1. Solo continúa si `CI` termina bien en el SHA que sigue siendo la punta de `main`.
2. Usa el environment protegido `production` de GitHub.
3. Verifica que TimescaleDB anuncia plataforma `linux/arm64`.
4. Publica backend y web multiarch (`amd64`, `arm64`) en GHCR.
5. Etiqueta `main` y `sha-<commit>` e incrusta la revisión en ambas imágenes.
6. Dispara el webhook de Coolify.
7. Espera hasta cinco minutos y exige que app/API/worker publiquen ese SHA exacto.

Crea en GitHub el environment `production`; opcionalmente exige aprobación manual.

### Primer despliegue, sin ciclo imposible

1. Guarda primero el recurso Compose en Coolify y copia su webhook.
2. Configura variables/secrets en GitHub y Coolify.
3. Haz push de este commit a `main` (o reejecuta el workflow `CI` de la punta actual).
4. Al completar CI, el workflow publica las imágenes antes de llamar a Coolify.
5. Coolify ya puede hacer pull y levantar el Compose.

## 9. Comprobar ARM64 de TimescaleDB

El despliegue fallará antes de tocar Coolify si el tag elegido no incluye ARM64.
También puedes verificarlo localmente:

```bash
docker buildx imagetools inspect timescale/timescaledb:2.16.1-pg16
```

Debe aparecer `linux/arm64`. No uses la imagen `timescaledb-ha` sin confirmar
arquitectura. Si el tag no tiene ARM64, cambia `TIMESCALE_TAG` por uno compatible
y actualiza la variable tanto en GitHub como Coolify.

## 10. Verificación del primer arranque

En Coolify comprueba:

1. `db` y `redis`: healthy.
2. `migrate`: exited con código 0.
3. `api`, `worker`, `app`: healthy.
4. `backup`: running.
5. Ningún dominio/puerto en DB/Redis.

Pruebas:

```bash
curl -fsS https://market.<tu-dominio>/healthz
curl -fsS https://api.market.<tu-dominio>/health
```

En terminal del worker:

```bash
python -m app.worker_healthcheck
echo $?   # debe ser 0
```

En terminal API:

```bash
alembic current
```

Finalmente registra el primer OWNER y verifica que `ALLOW_REGISTRATION=false`
sigue aplicado.

## 11. Backups off-host en OCI Object Storage

El servicio `backup` hace `pg_dump -Fc`, valida con `pg_restore --list`, calcula
SHA-256, conserva copias locales y opcionalmente sube a un destino S3 compatible.

En OCI:

1. Crea bucket privado, por ejemplo `market-tracker-backups`.
2. Configura lifecycle de retención.
3. Genera Customer Secret Key para un usuario limitado al bucket.
4. Obtén endpoint S3 compatible y región.
5. Configura en Coolify:

```text
RCLONE_REMOTE=oci
RCLONE_DESTINATION=market-tracker-backups/production
RCLONE_CONFIG_OCI_ACCESS_KEY_ID=<access key>
RCLONE_CONFIG_OCI_SECRET_ACCESS_KEY=<secret key>
RCLONE_CONFIG_OCI_ENDPOINT=<endpoint S3 OCI>
RCLONE_CONFIG_OCI_REGION=<region>
```

Coolify también admite backups programados a S3 para bases soportadas:
[database backups](https://coolify.io/docs/databases/backups). En este stack el
servicio propio se mantiene porque usa TimescaleDB en Compose y deja backup,
checksum y restore versionados con el proyecto.

### Probar backup

En terminal del contenedor `backup`:

```bash
/opt/markettracker/backup.sh
ls -lh /backups
/opt/markettracker/verify-backup.sh /backups/<archivo>.dump
```

Configura una alerta externa si no aparece una copia reciente. Un backup no se
considera válido hasta probar una restauración.

Para recuperar una copia de OCI antes del ensayo:

```bash
rclone copy oci:market-tracker-backups/production/<base> /backups/<base>
/opt/markettracker/verify-backup.sh /backups/<base>/<archivo>.dump
```

Descarga siempre `.dump`, `.dump.sha256` y `.dump.metadata`; el checksum es
obligatorio.

## 12. Restauración ensayada

No restaures sobre producción con API/worker escribiendo.

1. Activa mantenimiento y detén API/worker.
2. Haz snapshot/backup adicional.
3. Selecciona el dump.
4. En terminal `backup`:

```bash
CONFIRM_RESTORE=markettracker \
  /opt/markettracker/restore.sh /backups/<archivo>.dump
```

5. Ejecuta `alembic upgrade head` desde `migrate` o API.
6. Arranca API/worker.
7. Ejecuta `deploy/smoke.sh` y comprueba conteos/auditoría.

`restore.sh` intenta siempre ejecutar `timescaledb_post_restore()` aunque falle
`pg_restore`. Si el log indica que tampoco pudo cerrar ese modo, ejecuta antes
de cualquier otro cambio:

```sql
SELECT timescaledb_post_restore();
```

Para un ensayo sin riesgo, crea environment `restore-test` con `STACK_NAME`
distinto y restaura allí. Hazlo al menos trimestralmente.

## 13. Rollback de aplicación

No uses `alembic downgrade` automático.

1. Localiza el último SHA sano en GitHub Packages/Actions.
2. Cambia en Coolify:

```text
IMAGE_TAG=sha-<commit-completo>
```

3. Redespliega.
4. Ejecuta smoke test.
5. Si la migración no era backward-compatible, restaura el backup pre-release
   en una DB limpia y después despliega el SHA anterior.

El worker debe permanecer en una única réplica para no duplicar ingestión y
alertas. API/app sí pueden escalar más adelante.

## 14. Operación diaria

- Revisa espacio, RAM y estado de volúmenes semanalmente.
- Actualiza Coolify y el sistema con ventana de mantenimiento y backup previo.
- No uses tags `latest`; actualiza versiones deliberadamente.
- Conserva `main` para despliegue habitual y tags `sha-*` para rollback.
- Revisa logs de migración, worker, watchdog y backups.
- Rota JWT, passwords y tokens ante cualquier exposición.
- No guardes secretos en Compose, Git, logs o capturas.

## 15. Limitaciones conocidas antes de producción comercial

- JWT del WebSocket aún viaja en query string; usar ticket efímero antes de
  exposición amplia.
- Token web está en almacenamiento accesible a JavaScript; mantener CSP y evitar XSS.
- Telegram sigue siendo global, no por usuario.
- Fiscalidad es borrador informativo, no asesoramiento.
- La instancia única no ofrece alta disponibilidad regional.

Contenido de fuentes externas reformulado por cumplimiento de licencias.
