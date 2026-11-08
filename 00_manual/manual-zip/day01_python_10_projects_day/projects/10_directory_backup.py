"""Back up a directory to ZIP without overwriting and clamp unsupported timestamps."""
import os
import sys
import zipfile
from pathlib import Path


def raise_walk_error(error):
    """Propagate directory traversal failures to the caller."""
    raise error


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 10_directory_backup.py <source_directory> <output_zip>")
        return 2

    try:
        source = Path(sys.argv[1]).expanduser()
        destination = Path(sys.argv[2]).expanduser()
        if source.is_symlink() or not source.is_dir():
            print("Error: Specify an existing regular directory.")
            return 1
        if destination.is_symlink():
            print("Error: Output path must not be a symbolic link.")
            return 1

        source = source.resolve()
        destination = destination.resolve(strict=False)
        if destination == source or source in destination.parents:
            print("Error: Output path must not be inside the source directory.")
            return 2
        if destination.exists():
            print(f"Error: Destination already exists: {destination}")
            return 1
        if not destination.parent.is_dir():
            print(f"Error: Destination directory does not exist: {destination.parent}")
            return 1

        file_count = 0
        directory_count = 0
        skipped_links = 0
        with zipfile.ZipFile(
            destination, "x", compression=zipfile.ZIP_DEFLATED,
            strict_timestamps=False,
        ) as archive:
            for current, directories, files in os.walk(
                source, onerror=raise_walk_error, followlinks=False,
            ):
                directories.sort()
                for name in sorted(directories + files):
                    item = Path(current) / name
                    if item.is_symlink():
                        skipped_links += 1
                        continue
                    relative_name = item.relative_to(source)
                    if item.is_dir():
                        archive.write(item, arcname=f"{relative_name.as_posix()}/")
                        directory_count += 1
                    elif item.is_file():
                        archive.write(item, arcname=relative_name.as_posix())
                        file_count += 1
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"Error: Cannot create ZIP: {error}")
        print("Warning: A partial ZIP file may remain; inspect it manually.")
        return 1

    print(f"Saved: {destination}")
    print(f"Files: {file_count} / Directories: {directory_count}")
    print(f"Skipped symlinks: {skipped_links}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
