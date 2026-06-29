このフォルダに、同梱する外部ツールを配置してください。
（setup.exe ビルド時に {app}\bin へインストールされ、アプリが自動検出します）

配置するもの
============

ffmpeg（音声変換用）
   bin\ffmpeg.exe
   ※ 静的ビルド版の ffmpeg.exe を 1 つ置くだけで OK
     （gyan.dev の essentials / full ビルド、または BtbN ビルド等）

最終的なレイアウト
==================
bin\
  ffmpeg.exe

メモ
====
GitHub Actions で自動ビルドする場合、ffmpeg は CI が自動ダウンロードして
配置するため、このフォルダを手動で埋める必要はありません
（ローカルで build.bat を使うときのみ配置が必要）。
