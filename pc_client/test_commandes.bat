@echo off
chcp 65001 > nul
cls
echo ==============================================================
echo    MENU DE TEST DU PROJET - STM32 / FreeRTOS (Membre 1 & 2)
echo ==============================================================
echo.
echo 1. Lancer la Console de Telemetrie (serial_alert_bridge.py)
echo 2. Lancer le Dashboard Graphique avec la Courbe (gui_dashboard.py)
echo 3. Tester la connexion E-mail SMTP (--test-email)
echo 4. Lancer la Simulation Console sans carte (--simulate)
echo 5. Quitter
echo.
set /p choix="Entrez votre choix (1, 2, 3, 4 ou 5) : "

if "%choix%"=="1" (
    echo.
    echo Lancement du moniteur serie...
    python serial_alert_bridge.py
)
if "%choix%"=="2" (
    echo.
    echo Lancement du Dashboard graphique...
    python gui_dashboard.py
)
if "%choix%"=="3" (
    echo.
    echo Test de la liaison email...
    python serial_alert_bridge.py --test-email
)
if "%choix%"=="4" (
    echo.
    echo Lancement de la simulation...
    python serial_alert_bridge.py --simulate
)

pause
