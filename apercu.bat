@echo off
rem Apercu local du site : double-cliquez sur ce fichier, le site s'ouvre dans le navigateur.
rem Les albums proteges ne fonctionnent pas en ouvrant directement un fichier .html.
cd /d "%~dp0"
start "" http://localhost:8765/index.html
echo Apercu du site sur http://localhost:8765  -  fermez cette fenetre pour l'arreter.
python -m http.server 8765 --bind 127.0.0.1
pause
