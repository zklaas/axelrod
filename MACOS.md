# Axelrod on macOS

The same code runs on macOS, Windows and Linux. Axelrod needs **Python 3.10 or newer**
(macOS's own `python3` is too old):

    brew install python@3.13        # Homebrew: https://brew.sh
    # or the installer from https://www.python.org/downloads/macos/

Then, in Terminal:

    git clone https://github.com/zklaas/axelrod.git Axelrod
    cd Axelrod
    bash install-macos.sh

That creates `.venv` (PyQt6), a `axelrod` command in `~/.local/bin`, and a
**Axelrod** app in your Applications folder (Launchpad, Spotlight, the Dock).

Bred strategy tables are kept in `~/Library/Application Support/Axelrod/bred.json`.

To remove it: delete the folder, `~/Applications/Axelrod.app` and `~/.local/bin/axelrod`.

macOS support has not yet been tested on a Mac; please report anything that does
not work.
