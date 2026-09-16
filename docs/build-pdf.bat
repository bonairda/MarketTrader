@echo off
REM Genera HTML imprimibles (listos para "Guardar como PDF") a partir de los .md de docs/.
REM No requiere instalar nada: usa PowerShell, presente en Windows.
setlocal
set "SCRIPT_DIR=%~dp0"
echo Generando HTML imprimibles desde los documentos Markdown...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%md-to-html.ps1"
if errorlevel 1 (
  echo.
  echo Hubo un error al generar los documentos.
  pause
  exit /b 1
)
echo.
echo Abriendo el indice en el navegador...
start "" "%SCRIPT_DIR%pdf\index.html"
echo.
echo Sugerencia: en el navegador pulsa Ctrl+P y elige "Guardar como PDF".
endlocal
