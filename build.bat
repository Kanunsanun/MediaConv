@echo off
chcp 65001 > nul
title MediaConv ビルド
cd /d "%~dp0"
echo ============================================
echo  [1/2] PyInstaller でアプリを固めています...
echo ============================================
".venv\Scripts\pyinstaller.exe" mediaconv.spec --noconfirm
if errorlevel 1 (
  echo PyInstaller ビルドに失敗しました。
  pause
  exit /b 1
)
echo.
echo  -> dist\MediaConv\ を生成しました。
echo.
echo ============================================
echo  [2/2] setup.exe を作成します
echo ============================================
echo  bin\ffmpeg.exe を配置済みか確認してください。
echo  続いて Inno Setup を実行します（インストール済みの場合）。
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" (
  "%ISCC%" installer.iss
  echo  -> Output\ に setup.exe を生成しました。
) else (
  echo  [スキップ] Inno Setup が見つかりません。
  echo  導入後に installer.iss を右クリック→Compile してください。
)
echo.
pause
