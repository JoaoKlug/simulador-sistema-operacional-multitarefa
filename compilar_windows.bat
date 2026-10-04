@echo off
echo Compilando Simulador de Sistema Operacional Multitarefa...
pyinstaller --onefile --windowed src/principal.py
echo Compilacao concluida!
pause
