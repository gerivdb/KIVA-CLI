@echo off
REM ============================================================
REM  KIVA — nexus sync weekly
REM  Task Scheduler : lundi 06:00
REM  Créé : 2026-05-23 | ENV1 | CONFORME_NEXUS
REM  Repo  : gerivdb/KIVA-CLI (SCRIPTS/)
REM ============================================================

SETLOCAL

SET KIVA_CLI=D:\DO\WEB\TOOLS\L0-CANON\KIVA-CLI
SET NEXUS_ROOT=D:\DO\WEB\TOOLS\L0-CANON\NEXUS
SET LOG_DIR=%NEXUS_ROOT%\logs
SET LOG_FILE=%LOG_DIR%\nexus-sync-weekly.log

REM -- Créer le dossier logs si absent
IF NOT EXIST "%LOG_DIR%" MKDIR "%LOG_DIR%"

REM -- Timestamp de début
ECHO. >> "%LOG_FILE%"
ECHO ======================================================== >> "%LOG_FILE%"
ECHO [%DATE% %TIME%] kiva nexus sync -- START >> "%LOG_FILE%"
ECHO ======================================================== >> "%LOG_FILE%"

REM -- Exécution
cd /d "%KIVA_CLI%"
python -m kiva nexus sync --repo "%NEXUS_ROOT%" >> "%LOG_FILE%" 2>&1
SET EXIT_CODE=%ERRORLEVEL%

REM -- Timestamp de fin + exit code
ECHO [%DATE% %TIME%] kiva nexus sync -- END (exit=%EXIT_CODE%) >> "%LOG_FILE%"

ENDLOCAL
EXIT /B %EXIT_CODE%
