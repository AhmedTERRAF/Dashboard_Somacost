@echo off

echo ==========================================
echo     SAP SD Dashboard - Project Setup
echo ==========================================
echo.

REM Main Python files
type nul > app.py
type nul > data_loader.py
type nul > requirements.txt

REM Data folders
mkdir data 2>nul
mkdir data\real 2>nul

echo.
echo Project structure created successfully!
echo.

echo ==========================================
echo Folder structure:
echo ==========================================
echo.
echo SAP_SD_Dashboard\
echo ^|-- app.py
echo ^|-- data_loader.py
echo ^|-- requirements.txt
echo ^|
echo +-- data\
echo     +-- real\
echo         ^|-- VBRP
echo         ^|-- VBRK
echo         ^|-- VBFA
echo         ^|-- VBAK
echo         ^|-- MARA
echo         ^|-- LIKP
echo         +-- KNA1
echo.

echo ==========================================
echo Next step:
echo ==========================================
echo.
echo Put your real SAP files inside:
echo.
echo data\real\
echo.
echo You can copy them one by one.
echo Their original filenames can be kept.
echo.
pause