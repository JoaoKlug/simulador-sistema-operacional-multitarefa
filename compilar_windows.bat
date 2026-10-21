@echo off
chcp 65001 >nul
echo ============================================================================
echo   Compilando Simulador de Sistema Operacional Multitarefa (SimuladorSO.exe)
echo ============================================================================

echo [1/3] Limpando caches de builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/3] Gerando recursos visuais (icone da aplicacao)...
python gerar_recursos_build.py
if errorlevel 1 (
    echo [ERRO] Falha ao gerar icone da aplicacao.
    pause
    exit /b 1
)

echo [3/3] Executando PyInstaller com metadados de versao e sem compressao UPX...
pyinstaller --clean --noconfirm principal.spec
if errorlevel 1 (
    echo [ERRO] A compilacao falhou. Verifique as mensagens acima.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   Compilacao concluida com sucesso!
echo   Executavel gerado em: dist\SimuladorSO.exe
echo ============================================================================
pause
