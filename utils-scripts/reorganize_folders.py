import os
import shutil
from pathlib import Path
from typing import Iterable
from movies_catalog import CATEGORIES

# ======================================
# CONFIGURATION
# ======================================
BASE_DIR = Path("/srv/media")
TEMP_SOURCE = BASE_DIR / "temp_movies"
TEMP_RENAMED = TEMP_SOURCE / "renamed"

# Only used for awareness/documentation; we move whole title folders
MOVIE_EXTS = (".mp4", ".mkv", ".avi", ".mov")
AUX_EXTS   = (".srt", ".ssa", ".ass", ".sub", ".idx", ".nfo", ".jpg", ".png", ".webp")

# ======================================
# INTERACTIVE PROMPTS
# ======================================
def prompt_yes_no(msg: str) -> bool:
    while True:
        ans = input(f"{msg} [y/N]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("Please answer y or n.")

# ======================================
# HELPERS
# ======================================
def is_subpath(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def safe_move(src: Path, dest: Path, log: list, dry_run: bool):
    """Move a file or folder safely (no overwrites, no self-moves)."""
    if not src.exists():
        log.append(f"⚠️  Missing: {src}")
        return
    if dest.exists():
        log.append(f"⚠️  Exists, skipped: {dest}")
        return
    if is_subpath(dest, src):
        log.append(f"🚫 Self-move blocked: {src} → {dest}")
        return
    log.append(f"➡️  Move: {src} → {dest}")
    if not dry_run:
        ensure_dir(dest.parent)
        shutil.move(str(src), str(dest))

def safe_merge_folder(src_folder: Path, dest_folder: Path, log: list, dry_run: bool):
    """Merge src_folder contents into dest_folder without overwriting existing files."""
    ensure_dir(dest_folder)
    for item in src_folder.iterdir():
        dest_item = dest_folder / item.name
        if dest_item.exists():
            log.append(f"⚠️  Exists, skipped: {dest_item}")
            continue
        log.append(f"➡️  Move: {item} → {dest_item}")
        if not dry_run:
            shutil.move(str(item), str(dest_item))
    if not any(src_folder.iterdir()):
        log.append(f"🧹  Cleaned empty folder: {src_folder}")
        if not dry_run:
            src_folder.rmdir()

def build_title_index(categories: dict):
    """Map movie title → category path."""
    idx = {}
    for category_path, titles in categories.items():
        for title in titles:
            idx[title] = category_path
    return idx

# ======================================
# PHASE A — RENAME & STAGE
# ======================================
def phase_a_rename(rename_map: dict, temp_source: Path, staging_dir: Path, dry_run: bool = True):
    """
    Find each old_name recursively in temp_source, rename and move to staging_dir/<title>/<new_name>.
    """
    log = []
    moved = 0
    if not dry_run:
        ensure_dir(staging_dir)

    for old_name, new_name in rename_map.items():
        found = list(temp_source.rglob(old_name))
        if not found:
            log.append(f"❌ Not found: {old_name}")
            continue
        if len(found) > 1:
            log.append(f"❗ Multiple matches for {old_name}, skipped")
            continue

        src = found[0]
        movie_title = os.path.splitext(new_name)[0]
        dst_folder = staging_dir / movie_title
        dst_path = dst_folder / new_name

        if dst_path.exists():
            log.append(f"⚠️  Already exists: {dst_path}")
            continue

        log.append(f"➡️  Stage & Rename: {src} → {dst_path}")
        moved += 1
        if not dry_run:
            ensure_dir(dst_folder)
            shutil.move(str(src), str(dst_path))

    log.append(f"\n📊 Phase A complete. Files staged: {moved}\n")
    return log

# ======================================
# PHASE B — MOVE STAGED → LIBRARY
# ======================================
def phase_b_move(staging_dir: Path, base_dir: Path, categories: dict, dry_run: bool = True):
    log = []
    index = build_title_index(categories)
    uncategorized = base_dir / "_Uncategorized"
    if not dry_run:
        ensure_dir(uncategorized)

    if not staging_dir.exists():
        log.append(f"ℹ️  Staging folder not found: {staging_dir}")
        return log

    for movie_folder in sorted(p for p in staging_dir.iterdir() if p.is_dir()):
        title = movie_folder.name
        category = index.get(title)
        dest_dir = base_dir / category / title if category else uncategorized / title

        if not category:
            log.append(f"📦 Unknown → _Uncategorized: {title}")

        if dest_dir.exists():
            safe_merge_folder(movie_folder, dest_dir, log, dry_run)
        else:
            safe_move(movie_folder, dest_dir, log, dry_run)

    log.append("\n📦 Phase B complete.\n")
    return log

# ======================================
# PHASE C — VALIDATE LIBRARY STRUCTURE (fixed)
# ======================================
def _is_within_any(path: Path, bases: Iterable[Path]) -> bool:
    pr = path.resolve()
    for b in bases:
        try:
            pr.relative_to(b.resolve())
            return True
        except ValueError:
            continue
    return False

def phase_c_validate(base_dir: Path, categories: dict):
    """
    Validate that:
      1) Every expected title folder exists.
      2) Unexpected directories not part of the catalog are reported,
         while allowing:
         - top-level category roots (e.g., 'Horror', 'Adventure & Fantasy', ...)
         - category paths (e.g., 'Adventure & Fantasy/Back to the Future')
         - everything under a title folder (including .trickplay, artwork, etc.)
         - known utility/staging folders (temp_movies, scripts, _Uncategorized, etc.)
    """
    log = []
    missing, unexpected = [], []

    # Build expected directories
    expected_title_dirs = set()
    expected_category_dirs = set()
    expected_root_categories = set()

    for category_path, titles in categories.items():
        cat_dir = base_dir / category_path
        expected_category_dirs.add(cat_dir)
        root = category_path.split("/", 1)[0]  # e.g., "Adventure & Fantasy"
        expected_root_categories.add(base_dir / root)

        for title in titles:
            expected_title_dirs.add(cat_dir / title)

    # Known allowed misc (staging, scripts, etc.)
    allowed_misc = {
        base_dir / "_Uncategorized",
        base_dir / "temp_movies",
        base_dir / "temp_movies" / "renamed",
        base_dir / "scripts",
    }

    # ---------- 1) Missing expected title folders ----------
    for tdir in sorted(expected_title_dirs):
        if not tdir.exists():
            missing.append(str(tdir))
            log.append(f"❌ Missing title folder: {tdir}")

    # ---------- 2) Unexpected directory scan ----------
    for root, dirnames, _filenames in os.walk(base_dir):
        cur = Path(root)
        if cur.resolve() == base_dir.resolve():
            continue

        name = cur.name
        if name == "__pycache__" or name.startswith("."):
            continue

        if (
            _is_within_any(cur, expected_title_dirs)
            or _is_within_any(cur, expected_category_dirs)
            or _is_within_any(cur, expected_root_categories)
            or _is_within_any(cur, allowed_misc)
        ):
            continue

        unexpected.append(str(cur))
        log.append(f"⚠️ Unexpected: {cur}")

    # ---------- Summary ----------
    log.append("\n📊 Phase C Summary")
    log.append(f"   Missing titles: {len(missing)}")
    log.append(f"   Unexpected dirs: {len(unexpected)}")

    if missing:
        log.append("\n❌ Missing list:")
        for m in missing:
            log.append(f"   - {m}")

    if unexpected:
        log.append("\n⚠️ Unexpected list:")
        for u in unexpected:
            log.append(f"   - {u}")

    return log

# ======================================
# MAIN (Interactive A → B → C)
# ======================================
if __name__ == "__main__":
    # === Example rename map for your real case ===
    RENAME_MAP = {
        "Wrong name Movie.mp4": "Correct Name Movie 1 (2020).mp4",
        "Another Wrong Name.mkv": "Another Correct Name (2019).mkv",
    }

    # ---- Phase A (always dry-run first) ----
    print("=== PHASE A: RENAME & STAGE (Dry Run) ===")
    a_log = phase_a_rename(RENAME_MAP, TEMP_SOURCE, TEMP_RENAMED, dry_run=True)
    print("\n".join(a_log))

    if prompt_yes_no("Execute Phase A for real?"):
        print("\n=== Running PHASE A (Real Move) ===")
        a_log = phase_a_rename(RENAME_MAP, TEMP_SOURCE, TEMP_RENAMED, dry_run=False)
        print("\n".join(a_log))
    else:
        print("⏭️  Skipped actual Phase A execution.\n")

    # ---- Phase B (dry-run then optional real) ----
    print("\n=== PHASE B: MOVE STAGED → LIBRARY (Dry Run) ===")
    b_log = phase_b_move(TEMP_RENAMED, BASE_DIR, CATEGORIES, dry_run=True)
    print("\n".join(b_log))

    if prompt_yes_no("Execute Phase B for real?"):
        print("\n=== Running PHASE B (Real Move) ===")
        b_log = phase_b_move(TEMP_RENAMED, BASE_DIR, CATEGORIES, dry_run=False)
        print("\n".join(b_log))
    else:
        print("⏭️  Skipped actual Phase B execution.\n")

    # ---- Phase C (validation; read-only) ----
    print("\n=== PHASE C: VALIDATE LIBRARY ===")
    c_log = phase_c_validate(BASE_DIR, CATEGORIES)
    print("\n".join(c_log))

    print("\n✅ All phases complete (interactive mode).")
