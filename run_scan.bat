@echo off
rem Cave Mapper SCAN tab on the desktop, live VL53L5CX on COM12.
cd /d "%~dp0"
py cavemap.py --desktop --serial COM12 %*
if errorlevel 1 pause
