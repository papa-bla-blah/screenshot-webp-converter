#!/usr/bin/env python3
"""
WebP Screenshot Util
Converts screenshots and AirDrop images to WebP format automatically.

Watches two directories simultaneously:
  - Screenshots : ~/Desktop  (macOS default, Mojave 10.14+)
  - AirDrop     : ~/Downloads (macOS hardcoded, not user-configurable in UI)

Output: ~/Pictures/WebP_ss/

Supported input: PNG, JPG, JPEG, HEIC
Output format:   WebP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIGURING FOR YOUR SETUP
Edit the CONFIGURATION block below. All user-adjustable settings
are grouped there with comments explaining each option.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

macOS screenshot save location history:
  OS X 10.0-10.7   (Cheetah-Lion)              ~/Desktop   "Screen Shot"
  OS X 10.8-10.13  (Mountain Lion-High Sierra)  ~/Desktop   "Screen Shot"
  macOS 10.14      (Mojave)                     ~/Desktop   "Screenshot"
  macOS 10.15      (Catalina)                   ~/Desktop   "Screenshot"
  macOS 11         (Big Sur)                    ~/Desktop   "Screenshot"
  macOS 12         (Monterey)                   ~/Desktop   "Screenshot"
  macOS 13         (Ventura)                    ~/Desktop   "Screenshot"
  macOS 14         (Sonoma)                     ~/Desktop   "Screenshot"
  macOS 15         (Sequoia)                    ~/Desktop   "Screenshot"

  Mojave introduced the Screenshot app (cmd+shift+5). The "Screenshot" prefix
  is the new default but users can reset it with:
    defaults write com.apple.screencapture name "Screen Shot"
  This script handles both known prefixes and degrades gracefully for any
  custom prefix.

  Sonoma/Sequoia bug: custom save locations may silently revert to
  ~/Desktop after OS updates. Defaulting to ~/Desktop is safest.

macOS AirDrop receive location history:
  OS X 10.7   (Lion)      AirDrop introduced. Received to ~/Downloads
  OS X 10.8+              ~/Downloads  (hardcoded, no UI to change)
  macOS 14.4  (Sonoma)    Known bug: files land in /private/tmp when
                          ~/Downloads is redirected to iCloud or Dropbox.
                          This script watches BOTH ~/Downloads and
                          /private/tmp as a fallback for that bug.

Usage:
  python3 webp_converter.py             # silent (errors only)
  python3 webp_converter.py --verbose   # full logging
"""

import os
import time
import argparse
import platform
from pathlib import Path
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# HEIC support (optional)
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION — edit these to match your setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Where macOS saves screenshots.
# Default: ~/Desktop  (macOS default for all supported versions)
# Change if you've pointed screenshots elsewhere via cmd+shift+5 -> Options.
# Example: Path.home() / "Desktop" / "Screenshots"
SCREENSHOTS_DIR = Path.home() / "Desktop"

# If SCREENSHOTS_DIR is ~/Desktop, only files matching SCREENSHOT_PREFIXES
# will be converted (avoids converting every PNG on your Desktop).
# Set to False if SCREENSHOTS_DIR is a dedicated folder (converts everything).
FILTER_DESKTOP_BY_PREFIX = True

# Where AirDrop files land.
# macOS hardcodes this to ~/Downloads. Only change if you use an
# Automator folder action to redirect AirDrop to a custom location.
AIRDROP_DIR = Path.home() / "Downloads"

# Sonoma 14.4+ bug fallback: AirDrop sometimes lands in /private/tmp
# instead of ~/Downloads when Downloads is iCloud/Dropbox-backed.
# Safe to leave enabled on all versions.
WATCH_PRIVATE_TMP = True
PRIVATE_TMP_DIR = Path("/private/tmp")

# Where converted WebP files are written. Created automatically if missing.
OUTPUT_DIR = Path.home() / "Pictures" / "WebP_ss"

# WebP quality: 1 (smallest) - 100 (largest/best).
# 95 = high quality lossy compression, typically 40-60% smaller than PNG.
WEBP_QUALITY = 95

# Formats to watch. Add or remove extensions as needed (lowercase only).
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.heic'}

# Known macOS screenshot filename prefixes.
# "Screenshot" = Mojave 10.14+   "Screen Shot" = pre-Mojave or custom reset
# Add your custom prefix here if you changed it via defaults write.
SCREENSHOT_PREFIXES = ("Screenshot ", "Screen Shot ")

# Logging: off by default. Run with --verbose / -v to enable.
VERBOSE = False

# Auto-delete original screenshot after confirmed successful conversion.
# OFF by default — set to True to enable.
# Only deletes if the WebP output file exists and is non-zero bytes after save.
# Two modes (set DELETE_MODE to one of these strings):
#   "on_convert"  — delete only when a new conversion is performed
#   "on_exists"   — delete if output already existed too (file was already done)
# Screenshots only. AirDrop originals are never deleted (Downloads folder is
# shared with browser downloads etc — too risky). Advanced users can extend
# this to AirDrop by calling delete_original() in the AirDrop handler.
DELETE_SCREENSHOT_ORIGINAL = False
DELETE_MODE = "on_convert"  # "on_convert" or "on_exists"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# END CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def log(msg: str, force: bool = False):
    if VERBOSE or force:
        print(msg, flush=True)


def get_output_filename(image_filename: str, is_screenshot: bool = True) -> str:
    stem = Path(image_filename).stem
    if is_screenshot:
        for prefix in SCREENSHOT_PREFIXES:
            if stem.startswith(prefix):
                stem = "SS_" + stem[len(prefix):]
                break
    stem = stem.replace(" ", "_")
    return f"{stem}_WebP.webp"


def is_screenshot_file(path: Path) -> bool:
    if not FILTER_DESKTOP_BY_PREFIX:
        return True
    return any(path.name.startswith(p) for p in SCREENSHOT_PREFIXES)


def wait_for_file_stable(filepath: Path, timeout: float = 2.0) -> bool:
    last_size = -1
    stable_count = 0
    start = time.time()
    while time.time() - start < timeout:
        try:
            size = os.path.getsize(filepath)
            if size == last_size:
                stable_count += 1
                if stable_count >= 3:
                    return True
            else:
                stable_count = 0
            last_size = size
        except (FileNotFoundError, PermissionError):
            pass
        time.sleep(0.1)
    return True


def delete_original(image_path: Path):
    """Delete the original source file. Logs result either way."""
    try:
        image_path.unlink()
        log(f"Deleted original: {image_path.name}")
    except Exception as e:
        log(f"Could not delete original {image_path.name}: {e}", force=True)


def convert_image_to_webp(image_path: Path, is_screenshot: bool = True):
    try:
        wait_for_file_stable(image_path)
        output_filename = get_output_filename(image_path.name, is_screenshot=is_screenshot)
        output_path = OUTPUT_DIR / output_filename

        if output_path.exists():
            log(f"Skip (exists): {output_filename}")
            # Delete original even if already converted, if mode allows
            if is_screenshot and DELETE_SCREENSHOT_ORIGINAL and DELETE_MODE == "on_exists":
                delete_original(image_path)
            return

        original_size = os.path.getsize(image_path)
        with Image.open(image_path) as img:
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, "WebP", quality=WEBP_QUALITY)

        # Confirm output is real before deleting anything
        if output_path.exists() and output_path.stat().st_size > 0:
            new_size = output_path.stat().st_size
            log(f"Converted: {output_filename} ({original_size/1024:.0f}KB -> {new_size/1024:.0f}KB)")
            if is_screenshot and DELETE_SCREENSHOT_ORIGINAL:
                delete_original(image_path)
        else:
            log(f"Warning: output missing or empty after save — original kept: {image_path.name}", force=True)

    except PermissionError as e:
        log(f"Permission error - {image_path.name}: {e}", force=True)
    except Exception as e:
        log(f"Error - {image_path.name}: {e}", force=True)


def backfill_existing_images(source_dir: Path, is_screenshot: bool = True):
    if not source_dir.exists():
        log(f"Directory not found: {source_dir}", force=True)
        return
    image_files = []
    for ext in IMAGE_EXTENSIONS:
        image_files.extend(source_dir.glob(f"*{ext}"))
        image_files.extend(source_dir.glob(f"*{ext.upper()}"))
    if is_screenshot:
        image_files = [f for f in image_files if is_screenshot_file(f)]
    if image_files:
        log(f"Backfilling {len(image_files)} file(s) from {source_dir.name}...")
        for f in sorted(image_files):
            convert_image_to_webp(f, is_screenshot=is_screenshot)
    else:
        log(f"Nothing to backfill in {source_dir.name}")


class ImageHandler(FileSystemEventHandler):
    def __init__(self, is_screenshot: bool = True):
        self.processed: set = set()
        self.is_screenshot = is_screenshot

    def _handle(self, path: Path):
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            return
        if path in self.processed:
            return
        if self.is_screenshot and not is_screenshot_file(path):
            return
        self.processed.add(path)
        time.sleep(0.2)
        convert_image_to_webp(path, is_screenshot=self.is_screenshot)

    def on_created(self, event):
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._handle(Path(event.dest_path))


def main():
    global VERBOSE
    parser = argparse.ArgumentParser(
        description="WebP Screenshot Util - auto-convert screenshots and AirDrop images to WebP"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging (default: off)")
    args = parser.parse_args()
    VERBOSE = args.verbose

    mac_ver = platform.mac_ver()[0]

    if not HEIC_SUPPORTED:
        log("Warning: pillow-heif not installed - HEIC files will not convert.", force=True)
        log("  Install with: pip install pillow-heif", force=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log("-" * 60)
    log(f"WebP Screenshot Util  |  macOS {mac_ver}")
    log(f"  Screenshots : {SCREENSHOTS_DIR}")
    log(f"  AirDrop     : {AIRDROP_DIR}")
    if WATCH_PRIVATE_TMP:
        log(f"  /private/tmp: watched (Sonoma AirDrop bug fallback)")
    log(f"  Output      : {OUTPUT_DIR}")
    log(f"  Quality     : {WEBP_QUALITY}")
    log(f"  Formats     : {', '.join(sorted(IMAGE_EXTENSIONS))}")
    log("-" * 60)

    backfill_existing_images(SCREENSHOTS_DIR, is_screenshot=True)
    backfill_existing_images(AIRDROP_DIR, is_screenshot=False)
    if WATCH_PRIVATE_TMP and PRIVATE_TMP_DIR.exists():
        backfill_existing_images(PRIVATE_TMP_DIR, is_screenshot=False)

    log("-" * 60)
    log("Watching for new images... (Ctrl+C to stop)")

    observer = Observer()
    observer.schedule(ImageHandler(is_screenshot=True), str(SCREENSHOTS_DIR), recursive=False)
    observer.schedule(ImageHandler(is_screenshot=False), str(AIRDROP_DIR), recursive=False)
    if WATCH_PRIVATE_TMP and PRIVATE_TMP_DIR.exists():
        observer.schedule(ImageHandler(is_screenshot=False), str(PRIVATE_TMP_DIR), recursive=False)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("\nStopping.", force=True)
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
