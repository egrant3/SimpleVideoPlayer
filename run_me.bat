@echo off
call .venv\Scripts\activate
START /B cmd /c "python .\video_player.py"
exit