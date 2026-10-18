@echo off
cd /d "%~dp0"
echo Instalando dependencias...
python -m pip install --upgrade pillow pyautogui pyinstaller
echo.
echo Gerando ShadowXDesk.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --name ShadowXDesk shadowx_desk.py
echo.
if exist dist\ShadowXDesk.exe (
    copy /y dist\ShadowXDesk.exe ShadowXDesk.exe >nul
    echo Pronto! O arquivo ShadowXDesk.exe esta nesta pasta.
    echo Coloque a pasta "platform-tools" ao lado dele para o modo USB.
) else (
    echo Falhou. Veja as mensagens acima.
)
pause
