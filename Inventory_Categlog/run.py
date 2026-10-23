import importlib.util
import sys


def ensure_dependencies():
    missing = [name for name in ("flask",) if importlib.util.find_spec(name) is None]
    if missing:
        packages = ", ".join(missing)
        print(f"Missing Python dependencies: {packages}")
        print("Run setup.ps1 in PowerShell, or install them with:")
        print(f'  "{sys.executable}" -m pip install -r requirements.txt')
        raise SystemExit(1)


ensure_dependencies()

from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
