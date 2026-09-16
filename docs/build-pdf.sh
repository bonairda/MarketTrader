#!/usr/bin/env bash
# Genera los PDF de la documentacion en docs/pdf/.
#
# Estrategia por orden de preferencia:
#   1. pandoc + wkhtmltopdf  -> PDF directo (mejor calidad)
#   2. pandoc (con motor por defecto) -> PDF directo
#   3. Fallback -> HTML imprimibles (abrir y "Guardar como PDF" desde el navegador)
#
# Uso: bash docs/build-pdf.sh
set -Eeuo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$DOCS_DIR/pdf"
mkdir -p "$OUT_DIR"

shopt -s nullglob
md_files=("$DOCS_DIR"/*.md)

if command -v pandoc >/dev/null 2>&1; then
  echo "pandoc detectado; generando PDF..."
  engine_args=()
  if command -v wkhtmltopdf >/dev/null 2>&1; then
    engine_args=(--pdf-engine=wkhtmltopdf)
  fi
  for f in "${md_files[@]}"; do
    base="$(basename "${f%.md}")"
    echo "  -> pdf/$base.pdf"
    pandoc "$f" "${engine_args[@]}" \
      -V geometry:margin=2.2cm -V mainfont="DejaVu Sans" \
      --toc -o "$OUT_DIR/$base.pdf" || {
        echo "     (pandoc fallo en $base; se generara HTML)"; pandoc "$f" -s -o "$OUT_DIR/$base.html";
      }
  done
  echo "Listo. PDF en $OUT_DIR"
  exit 0
fi

echo "pandoc no esta instalado; generando HTML imprimibles como alternativa."
echo "Abre docs/pdf/index.html en tu navegador y usa 'Guardar como PDF' (Ctrl+P)."

# Generador HTML minimo autocontenido (sin dependencias).
css='<style>body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;line-height:1.55;max-width:820px;margin:0 auto;padding:32px 28px;color:#1f2933}h1{border-bottom:3px solid #2563eb;padding-bottom:.25em}h2{border-bottom:1px solid #d0d7de;padding-bottom:.2em}code{background:#f1f5f9;padding:.12em .35em;border-radius:4px;font-family:Consolas,monospace}pre{background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:8px;overflow-x:auto}pre code{background:transparent;color:inherit}table{border-collapse:collapse;width:100%;margin:1em 0}th,td{border:1px solid #d0d7de;padding:7px 10px;text-align:left;vertical-align:top}th{background:#eff6ff}blockquote{border-left:4px solid #2563eb;background:#f0f7ff;margin:1em 0;padding:.5em 1em;border-radius:0 6px 6px 0}a{color:#2563eb}@media print{body{max-width:none;padding:0}pre{white-space:pre-wrap}}</style>'

html_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

index_items=""
for f in "${md_files[@]}"; do
  base="$(basename "${f%.md}")"
  out="$OUT_DIR/$base.html"
  title="$(grep -m1 '^# ' "$f" | sed 's/^# //' || echo "$base")"
  {
    printf '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>%s</title>%s</head><body>\n' "$title" "$css"
    # Conversion minima: parrafos, encabezados y bloques de codigo. Para una
    # conversion completa instala pandoc; este fallback es legible e imprimible.
    awk '
      BEGIN{code=0}
      /^```/{ if(code==0){print "<pre><code>";code=1}else{print "</code></pre>";code=0}; next }
      { if(code==1){ gsub(/&/,"\\&amp;"); gsub(/</,"\\&lt;"); gsub(/>/,"\\&gt;"); print; next } }
      /^# /{ sub(/^# /,""); print "<h1>"$0"</h1>"; next }
      /^## /{ sub(/^## /,""); print "<h2>"$0"</h2>"; next }
      /^### /{ sub(/^### /,""); print "<h3>"$0"</h3>"; next }
      /^$/{ print ""; next }
      { print "<p>"$0"</p>" }
    ' "$f"
    printf '</body></html>\n'
  } > "$out"
  echo "  -> pdf/$base.html"
  index_items+="<li><a href=\"$base.html\">$title</a></li>"
done

printf '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Documentacion MarketTracker</title>%s</head><body><h1>Documentacion de MarketTracker</h1><p>Abre cada documento y usa Ctrl+P -> Guardar como PDF.</p><ul>%s</ul></body></html>\n' "$css" "$index_items" > "$OUT_DIR/index.html"

echo "Listo. HTML en $OUT_DIR (abre index.html)."
