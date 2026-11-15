# Axelrod on Windows

The same code runs on Windows, macOS and Linux. Axelrod needs **Python 3.10 or newer**:

    winget install --id Python.Python.3.13 -e --scope user

Then install with PowerShell:

    git clone https://github.com/zklaas/axelrod.git Axelrod
    cd Axelrod
    powershell -ExecutionPolicy Bypass -File install.ps1

That creates `.venv` (PyQt6), a `axelrod` command on your PATH (open a
new terminal first), and a **Axelrod** Start-menu entry.

Bred strategy tables are kept in `%APPDATA%\Axelrod\bred.json`.

To remove it: delete the folder, the Start-menu entry (Axelrod) and
`%LOCALAPPDATA%\Programs\Axelrod`.

Windows support has not yet been tested on a Windows machine; please report anything
that does not work.
