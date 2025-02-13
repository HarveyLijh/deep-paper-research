import sys
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from src.ui.app import main

if __name__ == "__main__":
    main()
