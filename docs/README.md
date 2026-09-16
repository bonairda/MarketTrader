# Documentación de MarketTracker

Bienvenido a la documentación completa de **MarketTracker**, una herramienta de
seguimiento y análisis de mercados financieros (cripto, forex y acciones) formada
por un backend Python/FastAPI y una app Flutter multiplataforma.

Esta carpeta reúne todas las guías y manuales del proyecto. Cada documento está
escrito en Markdown y puede consultarse online (GitHub Pages) o exportarse a PDF.

> **Sitio web (un único punto de acceso):**
> <https://bonairda.github.io/MarketTrader/>
> Reúne las cuatro guías navegables, un documento "todo en uno" y las descargas en
> PDF. Se actualiza solo en cada cambio de `docs/` (ver [Publicar el sitio](#publicar-el-sitio-github-pages)).

## Índice de documentos

| # | Documento | Para quién | Contenido |
|---|-----------|------------|-----------|
| 01 | [Guía del proyecto](01-guia-del-proyecto.md) | Desarrolladores, arquitectos | Qué es, arquitectura, componentes, flujo de datos, módulos, modelo de datos |
| 02 | [Guía de configuración](02-guia-de-configuracion.md) | Desarrolladores, operadores | Todas las variables de entorno, secretos, seguridad, integraciones opcionales |
| 03 | [Guía de despliegue](03-guia-de-despliegue.md) | DevOps, operadores | Local con Docker, CI/CD, Coolify + Oracle Cloud, backups, operación y rollback |
| 04 | [Manual de usuario](04-manual-de-usuario.md) | Usuario final | Cómo usar cada pantalla y función de la aplicación |
| 05 | [Trading con dinero real](05-trading-real.md) | Desarrolladores, operadores | Hoja de ruta para pasar de paper a dinero real: fases, seguridad, límites y conciliación |

> Consejo: si es la primera vez que tocas el proyecto, lee los documentos en orden
> (01 → 02 → 03). Si solo vas a **usar** la aplicación, ve directo al
> [Manual de usuario](04-manual-de-usuario.md).

## Mapa rápido del repositorio

```
market-tracker/
├── app/            # App Flutter (web / escritorio / móvil)
├── backend/        # API FastAPI + worker de ingestión + migraciones Alembic
├── deploy/         # Scripts de despliegue, backups y runbook de Coolify/Oracle
├── docs/           # ESTA carpeta: guías y manuales
├── docker-compose.yml         # Stack de desarrollo local
├── compose.production.yml     # Stack de producción (Coolify)
├── .env.example               # Plantilla de variables para desarrollo
└── .env.production.example    # Plantilla de variables para producción
```

## Generar los PDF

Los documentos se escriben en Markdown para que sean fáciles de mantener y de
versionar con Git. Para obtener los PDF hay tres vías, sin instalar nada:

### Opción A — Ya está listo (la más rápida)

En `docs/pdf/` encontrarás un documento **ya generado** con las cuatro guías:

1. Abre `docs/pdf/MarketTracker-Documentacion.html` en tu navegador (doble clic),
   o abre `docs/pdf/index.html` como portada.
2. Pulsa el botón **"Imprimir / Guardar como PDF"** (o `Ctrl+P` / `Cmd+P`) y
   elige **Guardar como PDF**, tamaño A4.

Es un fichero autocontenido: no necesita internet ni ninguna herramienta. Los
estilos ya están preparados para impresión (saltos de página, márgenes y tipografía).

### Opción B — Regenerar los HTML por documento

Si editas los `.md` y quieres regenerar HTML imprimibles individuales:

- **Windows:** haz doble clic en `docs/build-pdf.bat`.
- **Linux/macOS:** `bash docs/build-pdf.sh`

El script transforma cada Markdown en un HTML con estilos dentro de `docs/pdf/`.
No requiere Python, Node ni pandoc; tu navegador hace la exportación a PDF.

### Opción C — Con herramientas de línea de comandos

Si dispones de [Pandoc](https://pandoc.org/) y un motor LaTeX o
[wkhtmltopdf](https://wkhtmltopdf.org/), puedes convertir directamente:

```bash
# Con pandoc + wkhtmltopdf
pandoc docs/01-guia-del-proyecto.md -o docs/pdf/01-guia-del-proyecto.pdf

# O todos a la vez (bash)
for f in docs/0*.md; do pandoc "$f" -o "docs/pdf/$(basename "${f%.md}").pdf"; done
```

## Publicar el sitio (GitHub Pages)

La documentación se publica como un sitio web con un único punto de acceso, que
reúne las guías navegables, el documento completo y los PDF.

### Activarlo (solo la primera vez)

1. En GitHub, ve a **Settings → Pages**.
2. En **Build and deployment → Source**, elige **GitHub Actions**.
3. Listo. A partir de ahí, cada push a `main` que toque `docs/` regenera y
   despliega el sitio automáticamente.

También puedes lanzarlo a mano desde **Actions → "Docs (GitHub Pages)" → Run
workflow**.

### Cómo funciona

- El workflow [`.github/workflows/docs-pages.yml`](../.github/workflows/docs-pages.yml)
  instala `pandoc` y `wkhtmltopdf`, ejecuta [`docs/build-site.sh`](build-site.sh)
  y publica el resultado en Pages.
- `build-site.sh` genera, a partir de los `.md`:
  - una página HTML por guía (`01..04.html`) con barra de navegación común,
  - un documento combinado `completo.html`,
  - los PDF en `pdf/` (por guía y uno completo),
  - y copia la portada `index.html`.
- La URL del sitio es `https://<owner>.github.io/<repo>/`; para este repositorio:
  **<https://bonairda.github.io/MarketTrader/>**.

### Construir el sitio en local (opcional)

Con `pandoc` y `wkhtmltopdf` instalados:

```bash
bash docs/build-site.sh _site
# Abre _site/index.html en el navegador
```

Sin esas herramientas, sigue estando disponible el visor offline
`docs/pdf/MarketTracker-Documentacion.html` (Opción A de arriba).

---

_Documentación generada para el proyecto MarketTracker. Última revisión: septiembre de 2026._
