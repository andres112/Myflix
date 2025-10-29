
import os
import shutil

def organize_files(source_path: str, rename_map: dict, target_path: str):
    """
    Rename and organize files based on a mapping from old to new names.

    Args:
        source_path (str): Directory containing the unorganized files.
        rename_map (dict): Mapping of old file names to new standardized names.
        target_path (str): Destination root folder for organized files.
    """
    print(f"\n🎬 Organizing files from: {source_path}")
    print(f"📦 Target destination: {target_path}\n")

    if not os.path.isdir(source_path):
        print(f"❌ Error: Source path not found → {source_path}")
        return
    os.makedirs(target_path, exist_ok=True)

    moved, skipped, missing = 0, 0, 0

    for old_name, new_name in rename_map.items():
        old_path = os.path.join(source_path, old_name)
        if not os.path.exists(old_path):
            print(f"❌ Missing: {old_name}")
            missing += 1
            continue

        # Create file folder name based on new file's title (before extension)
        file_title = os.path.splitext(new_name)[0]
        file_folder = os.path.join(target_path, file_title)
        os.makedirs(file_folder, exist_ok=True)

        new_path = os.path.join(file_folder, new_name)

        # Rename and move
        if not os.path.exists(new_path):
            shutil.move(old_path, new_path)
            print(f"✅ {old_name} → {file_folder}/{new_name}")
            moved += 1
        else:
            print(f"⚠️ Skipped (already exists): {new_name}")
            skipped += 1

    print("\n📊 Summary:")
    print(f"  ✅ Moved/Renamed: {moved}")
    print(f"  ⚠️ Skipped: {skipped}")
    print(f"  ❌ Missing: {missing}")
    print("\n✨ Done organizing your collection!\n")


# === Example usage ===
if __name__ == "__main__":
    # Example: you can customize these easily for any collection
    SOURCE_PATH = "/srv/media/"
    TARGET_PATH = "/srv/media/"  # Can be same as source or a different path

    RENAME_MAP = {
        "WrongFileName.mkv": "CorrectFileName (YYYY).mkv",
    }

    organize_files(SOURCE_PATH, RENAME_MAP, TARGET_PATH)
