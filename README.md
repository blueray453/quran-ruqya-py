.Run
python -m ruqya_quran

pipx install --force .
pipx install --force --editable .
./install-desktop.sh

the extras folder should be placed inside your user configuration directory for the app, specifically at: ~/.config/ruqya-quran/extras/

pip freeze > requirements.txt

python -m venv .venv

pip install -e .

The command pip install -e . installs a local Python project in editable (or development) mode.

pip install -r requirements.txt