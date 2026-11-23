"""Delete old files from storage/temporary.

Usage: python scripts/maintenance/purge_temporary.py [--days 7] [--dir storage/temporary] [--dry-run]
Only regular files inside the chosen folder are removed, and .gitkeep is always kept. Uploads and reports are never touched.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def purge(folder: Path, days: float, dry_run: bool) -> list[Path]:
    cutoff = time.time() - days * 86400
    removed = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.name == ".gitkeep":
            continue
        if path.stat().st_mtime < cutoff:
            removed.append(path)
            if not dry_run:
                path.unlink()
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--dir", type=Path, default=ROOT / "storage" / "temporary")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    folder = args.dir.resolve()
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return 1
    removed = purge(folder, args.days, args.dry_run)
    verb = "Would remove" if args.dry_run else "Removed"
    print(f"{verb} {len(removed)} file(s) older than {args.days:g} day(s) from {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
