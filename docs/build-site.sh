#!/usr/bin/env bash
# Construye el sitio de documentacion (HTML + PDF) en el directorio de salida.
#
# Uso: bash docs/build-site.sh [directorio_salida]   (por defecto: _site)
#
# Requisitos: pandoc y wkhtmltopdf (los instala el workflow docs-pages.yml).
# Si faltan, el sitio HTML se genera igualmente; solo se omiten los PDF.
set -Eeuo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-_site}"
PDF_DIR="$OUT_DIR/pdf"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "$PDF_DIR"

# Marca para que GitHub Pages no procese el sitio con Jekyll.
touch "$OUT_DIR/.nojekyll"

# Orden y titulos de las guias.
DOCS=(
  "01-guia-del-proyecto:Guía del proyecto"
  "02-guia-de-configuracion:Guía de configuración"
  "03-guia-de-despliegue:Guía de despliegue"
  "04-manual-de-usuario:Manual de usuario"
  "05-trading-real:Trading con dinero real"
)

# ---- CSS comun del sitio (claro, legible, imprimible) ----
CSS_FILE="$OUT_DIR/style.css"
cat > "$CSS_FILE" <<'CSS'
:root { --accent:#2563eb; --accent-2:#1d4ed8; --border:#d0d7de; --muted:#52606d; }
* { box-sizing: border-box; }
body { font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; line-height:1.6; color:#1f2933; margin:0; }
.topnav { background:#10243e; color:#fff; padding:0 20px; position:sticky; top:0; z-index:20; display:flex; flex-wrap:wrap; align-items:center; gap:4px; }
.topnav a { color:#cdd9ec; text-decoration:none; padding:14px 12px; font-size:.92rem; }
.topnav a.brand { font-weight:700; color:#fff; padding-left:0; }
.topnav a:hover { color:#fff; }
.topnav a.active { color:#fff; border-bottom:3px solid var(--accent); }
.container { max-width:900px; margin:0 auto; padding:28px 24px 72px; }
h1,h2,h3,h4 { color:#10243e; line-height:1.25; margin-top:1.6em; }
h1 { font-size:2rem; border-bottom:3px solid var(--accent); padding-bottom:.25em; }
h2 { font-size:1.45rem; border-bottom:1px solid var(--border); padding-bottom:.2em; }
h3 { font-size:1.2rem; }
a { color:var(--accent); }
code { background:#f1f5f9; padding:.12em .35em; border-radius:4px; font-family:"Cascadia Code",Consolas,monospace; font-size:.88em; }
pre { background:#0f172a; color:#e2e8f0; padding:14px 16px; border-radius:8px; overflow-x:auto; font-size:.84em; line-height:1.45; }
pre code { background:transparent; color:inherit; padding:0; }
table { border-collapse:collapse; width:100%; margin:1em 0; font-size:.92em; }
th,td { border:1px solid var(--border); padding:7px 10px; text-align:left; vertical-align:top; }
th { background:#eff6ff; }
tr:nth-child(even) td { background:#f8fafc; }
blockquote { margin:1em 0; padding:.5em 1em; border-left:4px solid var(--accent); background:#f0f7ff; color:#334155; border-radius:0 6px 6px 0; }
hr { border:none; border-top:1px solid var(--border); margin:2em 0; }
#TOC { background:#f8fafc; border:1px solid var(--border); border-radius:10px; padding:14px 18px; margin:1.5em 0; }
#TOC ul { margin:.2em 0; }
.pdf-link { display:inline-block; margin:8px 0 0; background:var(--accent); color:#fff; padding:8px 16px; border-radius:8px; text-decoration:none; font-weight:600; font-size:.9rem; }
.pdf-link:hover { background:var(--accent-2); }
.doc-sep { page-break-after:always; }
@media print {
  .topnav { display:none; }
  .container { max-width:none; padding:0; }
  a { color:#1f2933; }
  pre { white-space:pre-wrap; word-wrap:break-word; }
  h1,h2,h3 { page-break-after:avoid; }
  table,pre,blockquote { page-break-inside:avoid; }
  thead { display:table-header-group; }
}
CSS

# ---- Barra de navegacion comun (acceso a todo desde cualquier pagina) ----
nav_html() {
  local active="$1"
  local html='<nav class="topnav"><a class="brand" href="index.html">MarketTracker Docs</a>'
  html+="<a href=\"completo.html\"$([ "$active" = "completo" ] && echo ' class=\"active\"')>Todo en uno</a>"
  local n=1
  for entry in "${DOCS[@]}"; do
    local slug="${entry%%:*}"
    local title="${entry##*:}"
    local label
    label="$(printf '%02d' "$n")"
    html+="<a href=\"$slug.html\"$([ "$active" = "$slug" ] && echo ' class=\"active\"')>$label · $title</a>"
    n=$((n+1))
  done
  html+='</nav>'
  printf '%s' "$html"
}

have_pandoc=0
if command -v pandoc >/dev/null 2>&1; then have_pandoc=1; fi
have_pdf=0
if command -v wkhtmltopdf >/dev/null 2>&1; then have_pdf=1; fi

render_page() {
  # render_page <slug> <title> <active> <src.md>
  local slug="$1" title="$2" active="$3" src="$4"
  local before after
  before="$(nav_html "$active")"
  if [ "$have_pandoc" = "1" ]; then
    pandoc "$src" \
      --standalone --toc --toc-depth=3 \
      --metadata title="$title — MarketTracker" \
      --css style.css \
      --include-before-body=<(printf '%s<div class="container">' "$before") \
      --include-after-body=<(printf '</div>') \
      -o "$OUT_DIR/$slug.html"
  else
    # Fallback minimal sin pandoc.
    {
      printf '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>%s</title><link rel="stylesheet" href="style.css"></head><body>' "$title"
      printf '%s<div class="container"><pre>' "$before"
      sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' "$src"
      printf '</pre></div></body></html>'
    } > "$OUT_DIR/$slug.html"
  fi
}

echo "== Generando paginas HTML por documento =="
for entry in "${DOCS[@]}"; do
  slug="${entry%%:*}"; title="${entry##*:}"
  render_page "$slug" "$title" "$slug" "$DOCS_DIR/$slug.md"
  echo "  -> $slug.html"
done

echo "== Generando documento combinado (completo.html) =="
COMBINED_MD="$(mktemp)"
for entry in "${DOCS[@]}"; do
  slug="${entry%%:*}"
  cat "$DOCS_DIR/$slug.md" >> "$COMBINED_MD"
  printf '\n\n<div class="doc-sep"></div>\n\n' >> "$COMBINED_MD"
done
render_page "completo" "Documentación completa" "completo" "$COMBINED_MD"
echo "  -> completo.html"

echo "== Copiando la landing (index.html) =="
cp "$DOCS_DIR/index.html" "$OUT_DIR/index.html"

echo "== Generando 404.html =="
cat > "$OUT_DIR/404.html" <<'HTML'
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Página no encontrada — MarketTracker</title>
<style>
  body { font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:#0b1220; color:#e6edf7; margin:0; min-height:100vh;
    display:flex; align-items:center; justify-content:center; text-align:center; padding:24px; }
  .box { max-width:520px; }
  h1 { font-size:2.4rem; margin:.2em 0; }
  p { color:#9fb0c9; }
  a { display:inline-block; margin-top:16px; background:#2563eb; color:#fff;
    padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:600; }
  a:hover { background:#3b82f6; }
  ul { list-style:none; padding:0; margin-top:20px; }
  li { margin:6px 0; }
  li a { background:transparent; color:#60a5fa; padding:0; font-weight:400; margin:0; }
</style>
</head>
<body>
<div class="box">
  <h1>404</h1>
  <p>No encontramos esa página. Puede que el sitio se esté actualizando; inténtalo
     de nuevo en un momento o vuelve al inicio.</p>
  <a href="./">Ir al inicio de la documentación</a>
  <ul>
    <li><a href="01-guia-del-proyecto.html">Guía del proyecto</a></li>
    <li><a href="02-guia-de-configuracion.html">Guía de configuración</a></li>
    <li><a href="03-guia-de-despliegue.html">Guía de despliegue</a></li>
    <li><a href="04-manual-de-usuario.html">Manual de usuario</a></li>
    <li><a href="05-trading-real.html">Trading con dinero real</a></li>
  </ul>
</div>
</body>
</html>
HTML

if [ "$have_pandoc" = "1" ] && [ "$have_pdf" = "1" ]; then
  echo "== Generando PDF con pandoc + wkhtmltopdf =="
  PDF_OPTS=(--pdf-engine=wkhtmltopdf -V margin-top=18mm -V margin-bottom=18mm -V margin-left=16mm -V margin-right=16mm --toc --toc-depth=3 --css "$CSS_FILE")
  for entry in "${DOCS[@]}"; do
    slug="${entry%%:*}"; title="${entry##*:}"
    pandoc "$DOCS_DIR/$slug.md" "${PDF_OPTS[@]}" --metadata title="$title — MarketTracker" -o "$PDF_DIR/$slug.pdf" \
      && echo "  -> pdf/$slug.pdf" || echo "  (aviso: fallo el PDF de $slug)"
  done
  pandoc "$COMBINED_MD" "${PDF_OPTS[@]}" --metadata title="Documentación de MarketTracker" -o "$PDF_DIR/MarketTracker-Documentacion.pdf" \
    && echo "  -> pdf/MarketTracker-Documentacion.pdf" || echo "  (aviso: fallo el PDF combinado)"
else
  echo "== pandoc/wkhtmltopdf no disponibles: se omiten los PDF =="
  # Copia el visor offline como respaldo para el PDF completo.
  if [ -f "$DOCS_DIR/pdf/MarketTracker-Documentacion.html" ]; then
    cp "$DOCS_DIR/pdf/MarketTracker-Documentacion.html" "$PDF_DIR/MarketTracker-Documentacion.html"
  fi
fi

rm -f "$COMBINED_MD"
echo "== Sitio construido en: $OUT_DIR =="
