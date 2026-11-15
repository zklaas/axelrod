# Installing Axelrod

## Linux

```
git clone https://github.com/zklaas/axelrod.git
cd axelrod
python3 -m pip install --user PyQt6   # or your distribution's packages
./install.sh
```

## Windows (untested)

```
git clone https://github.com/zklaas/axelrod.git
cd axelrod
py -m pip install PyQt6
powershell -ExecutionPolicy Bypass -File install.ps1
```

## macOS (untested)

```
git clone https://github.com/zklaas/axelrod.git
cd axelrod
python3 -m pip install --user PyQt6
python3 axelrod_app.py
```
