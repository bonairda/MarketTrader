<#
.SYNOPSIS
    Convierte los documentos Markdown de docs/ en HTML autocontenido e imprimible
    (listo para "Guardar como PDF" desde el navegador). No requiere dependencias
    externas: usa solo PowerShell.

.DESCRIPTION
    Recorre los ficheros .md de la carpeta docs/, los transforma a HTML con estilos
    preparados para impresion (margenes, saltos de pagina, tipografia) y genera un
    indice docs/pdf/index.html. Abre index.html en el navegador y usa Ctrl+P para
    exportar a PDF.

.NOTES
    Uso: powershell -ExecutionPolicy Bypass -File docs\md-to-html.ps1
    O simplemente ejecuta docs\build-pdf.bat
#>

[CmdletBinding()]
param(
    [string]$DocsDir = $PSScriptRoot,
    [string]$OutDir  = (Join-Path $PSScriptRoot 'pdf')
)

$ErrorActionPreference = 'Stop'

function ConvertTo-HtmlText {
    param([string]$Text)
    $Text = $Text -replace '&', '&amp;'
    $Text = $Text -replace '<', '&lt;'
    $Text = $Text -replace '>', '&gt;'
    return $Text
}

function Convert-Inline {
    param([string]$Text)
    # Escapar HTML primero, luego reintroducir el formato inline seguro.
    $t = ConvertTo-HtmlText $Text
    # Codigo inline `...`
    $t = [regex]::Replace($t, '`([^`]+)`', '<code>$1</code>')
    # Negrita **...**
    $t = [regex]::Replace($t, '\*\*([^*]+)\*\*', '<strong>$1</strong>')
    # Enlaces [texto](url) -> los .md internos apuntan al .html generado
    $t = [regex]::Replace($t, '\[([^\]]+)\]\(([^)]+)\)', {
        param($m)
        $label = $m.Groups[1].Value
        $url = $m.Groups[2].Value
        if ($url -match '^(0\d|README)[\w-]*\.md$') {
            $url = ($url -replace '\.md$', '.html')
        }
        "<a href=`"$url`">$label</a>"
    })
    # Cursiva _..._ (evita colisionar con snake_case; solo con espacios/limites)
    $t = [regex]::Replace($t, '(?<=\s|^)_([^_]+)_(?=\s|$|[.,;:)])', '<em>$1</em>')
    return $t
}

function Convert-Markdown {
    param([string[]]$Lines)

    $sb = [System.Text.StringBuilder]::new()
    $inCode = $false
    $inTable = $false
    $tableHeaderDone = $false
    $listType = $null   # 'ul' | 'ol' | $null

    function Close-List {
        if ($script:listType) {
            [void]$sb.AppendLine("</$script:listType>")
            $script:listType = $null
        }
    }
    function Close-Table {
        if ($script:inTable) {
            [void]$sb.AppendLine('</tbody></table>')
            $script:inTable = $false
            $script:tableHeaderDone = $false
        }
    }

    foreach ($raw in $Lines) {
        $line = $raw.TrimEnd()

        # Bloques de codigo ```
        if ($line -match '^```') {
            if (-not $inCode) {
                Close-List; Close-Table
                [void]$sb.AppendLine('<pre><code>')
                $inCode = $true
            } else {
                [void]$sb.AppendLine('</code></pre>')
                $inCode = $false
            }
            continue
        }
        if ($inCode) {
            [void]$sb.AppendLine((ConvertTo-HtmlText $raw))
            continue
        }

        # Linea en blanco
        if ($line -eq '') {
            Close-List; Close-Table
            continue
        }

        # Tablas (| ... | ... |)
        if ($line -match '^\s*\|.*\|\s*$') {
            # Separador de cabecera |---|---|
            if ($line -match '^\s*\|[\s:\-|]+\|\s*$') {
                $tableHeaderDone = $true
                continue
            }
            $cells = $line.Trim().Trim('|').Split('|')
            if (-not $inTable) {
                Close-List
                [void]$sb.AppendLine('<table><thead><tr>')
                foreach ($c in $cells) {
                    [void]$sb.AppendLine("<th>$([string](Convert-Inline $c.Trim()))</th>")
                }
                [void]$sb.AppendLine('</tr></thead><tbody>')
                $inTable = $true
                continue
            } else {
                [void]$sb.AppendLine('<tr>')
                foreach ($c in $cells) {
                    [void]$sb.AppendLine("<td>$([string](Convert-Inline $c.Trim()))</td>")
                }
                [void]$sb.AppendLine('</tr>')
                continue
            }
        } else {
            Close-Table
        }

        # Encabezados
        if ($line -match '^(#{1,6})\s+(.*)$') {
            Close-List
            $level = $Matches[1].Length
            $text = Convert-Inline $Matches[2]
            [void]$sb.AppendLine("<h$level>$text</h$level>")
            continue
        }

        # Cita >
        if ($line -match '^>\s?(.*)$') {
            Close-List
            $text = Convert-Inline $Matches[1]
            [void]$sb.AppendLine("<blockquote>$text</blockquote>")
            continue
        }

        # Regla horizontal
        if ($line -match '^(-{3,}|\*{3,}|_{3,})$') {
            Close-List; Close-Table
            [void]$sb.AppendLine('<hr />')
            continue
        }

        # Lista ordenada
        if ($line -match '^\s*\d+\.\s+(.*)$') {
            if ($listType -ne 'ol') { Close-List; [void]$sb.AppendLine('<ol>'); $listType = 'ol' }
            [void]$sb.AppendLine("<li>$([string](Convert-Inline $Matches[1]))</li>")
            continue
        }
        # Lista no ordenada
        if ($line -match '^\s*[-*+]\s+(.*)$') {
            if ($listType -ne 'ul') { Close-List; [void]$sb.AppendLine('<ul>'); $listType = 'ul' }
            [void]$sb.AppendLine("<li>$([string](Convert-Inline $Matches[1]))</li>")
            continue
        }

        # Parrafo normal
        Close-List
        [void]$sb.AppendLine("<p>$([string](Convert-Inline $line))</p>")
    }

    Close-List; Close-Table
    if ($inCode) { [void]$sb.AppendLine('</code></pre>') }
    return $sb.ToString()
}

$css = @'
<style>
  :root { color-scheme: light; }
  body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.55; color: #1f2933; max-width: 820px; margin: 0 auto;
    padding: 32px 28px; font-size: 15px;
  }
  h1, h2, h3, h4 { color: #10243e; line-height: 1.25; margin-top: 1.6em; }
  h1 { font-size: 1.9em; border-bottom: 3px solid #2563eb; padding-bottom: .25em; }
  h2 { font-size: 1.45em; border-bottom: 1px solid #d0d7de; padding-bottom: .2em; }
  h3 { font-size: 1.2em; }
  code {
    background: #f1f5f9; padding: .12em .35em; border-radius: 4px;
    font-family: "Cascadia Code", Consolas, "Courier New", monospace; font-size: .88em;
  }
  pre {
    background: #0f172a; color: #e2e8f0; padding: 14px 16px; border-radius: 8px;
    overflow-x: auto; font-size: .84em; line-height: 1.45;
  }
  pre code { background: transparent; color: inherit; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: .92em; }
  th, td { border: 1px solid #d0d7de; padding: 7px 10px; text-align: left; vertical-align: top; }
  th { background: #eff6ff; }
  tr:nth-child(even) td { background: #f8fafc; }
  blockquote {
    margin: 1em 0; padding: .5em 1em; border-left: 4px solid #2563eb;
    background: #f0f7ff; color: #334155; border-radius: 0 6px 6px 0;
  }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  hr { border: none; border-top: 1px solid #d0d7de; margin: 2em 0; }
  ul, ol { padding-left: 1.4em; }
  @media print {
    body { max-width: none; padding: 0; font-size: 11pt; }
    a { color: #1f2933; }
    pre { white-space: pre-wrap; word-wrap: break-word; }
    h1, h2, h3 { page-break-after: avoid; }
    table, pre, blockquote { page-break-inside: avoid; }
    thead { display: table-header-group; }
  }
</style>
'@

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$mdFiles = Get-ChildItem -Path $DocsDir -Filter '*.md' | Sort-Object Name
$generated = @()

foreach ($file in $mdFiles) {
    $lines = Get-Content -LiteralPath $file.FullName -Encoding UTF8
    $bodyHtml = Convert-Markdown -Lines $lines
    $title = ($lines | Where-Object { $_ -match '^#\s+' } | Select-Object -First 1) -replace '^#\s+', ''
    if (-not $title) { $title = $file.BaseName }

    $htmlName = ($file.BaseName + '.html')
    $htmlPath = Join-Path $OutDir $htmlName

    $doc = @"
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>$([string](ConvertTo-HtmlText $title)) — MarketTracker</title>
$css
</head>
<body>
$bodyHtml
</body>
</html>
"@

    Set-Content -LiteralPath $htmlPath -Value $doc -Encoding UTF8
    $generated += [pscustomobject]@{ Title = $title; File = $htmlName }
    Write-Host "  generado: pdf/$htmlName"
}

# Indice
$items = ($generated | ForEach-Object {
    "<li><a href=`"$($_.File)`">$([string](ConvertTo-HtmlText $_.Title))</a></li>"
}) -join "`n"

$index = @"
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>Documentacion MarketTracker</title>
$css
</head>
<body>
<h1>Documentacion de MarketTracker</h1>
<p>Abre cada documento y usa <strong>Imprimir &rarr; Guardar como PDF</strong> (Ctrl+P) para exportarlo.</p>
<ul>
$items
</ul>
</body>
</html>
"@
Set-Content -LiteralPath (Join-Path $OutDir 'index.html') -Value $index -Encoding UTF8

Write-Host ''
Write-Host "Listo. HTML imprimibles en: $OutDir"
Write-Host "Abre index.html y pulsa Ctrl+P -> Guardar como PDF."
