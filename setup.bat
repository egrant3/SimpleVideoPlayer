@echo off

if not exist ".venv\Scripts\activate" (
    echo venv not set up correctly.
	python -m venv .venv
)

REM python -m venv .venv
echo Activating venv...
call .venv\Scripts\activate

echo Installing dependencies...

pip install numpy
pip install opencv-python
pip install screeninfo
pip install pyinstaller

echo Done