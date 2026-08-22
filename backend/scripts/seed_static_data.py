import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import PROJECT_ROOT
from app.data.generate import write_seed_files


def main() -> None:
    write_seed_files(PROJECT_ROOT / "data")


if __name__ == "__main__":
    main()
