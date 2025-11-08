import shutil
from pathlib import Path
from movies_catalog import CATEGORIES  # 👈 imported here

# === CONFIGURATION ===
BASE_DIR = Path("/srv/media")
DRY_RUN = True  # Set False to execute moves


def candidate_paths_for(title: str, base: Path):
    """Yield directories matching 'title' within BASE_DIR at depth ≤2."""
    for pattern in [title, f"*/{title}", f"*/*/{title}"]:
        for p in base.glob(pattern):
            if p.is_dir():
                yield p


def move_movies():
    log = []
    for category, movies in CATEGORIES.items():
        target_dir = BASE_DIR / category
        target_dir.mkdir(parents=True, exist_ok=True)

        for title in movies:
            dest = target_dir / title
            if dest.exists():
                log.append(f"✅ Already placed: {dest}")
                continue

            found = False
            for src in candidate_paths_for(title, BASE_DIR):
                if src.resolve() == dest.resolve():
                    continue
                if src.parent.resolve() == target_dir.resolve():
                    continue

                found = True
                log.append(f"➡️  Move: {src} → {dest}")
                if not DRY_RUN:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dest))
                break

            if not found:
                log.append(f"🔎 Not found (skipped): {title}")

    return log


if __name__ == "__main__":
    moves = move_movies()
    print("\n".join(moves))
    print("\n✅ Dry run complete." if DRY_RUN else "\n✅ Move operation complete.")
