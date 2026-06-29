@echo off
chcp 65001 > nul
title MediaConv
cd /d "%~dp0"
".venv\Scripts\pythonw.exe" "%~dp0app.py"
