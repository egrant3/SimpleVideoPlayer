call .venv\Scripts\activate
pyinstaller --onefile --noconsole --name=SimpleVideoPlayer --icon=./playbutton.ico .\video_player.py