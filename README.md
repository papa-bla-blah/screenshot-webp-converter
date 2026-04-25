# WebP Screenshot Util

A lightweight macOS utility (10.14 Mojave+) that auto-converts screenshots and AirDrop images to WebP format.

Free and open source (MIT). Use at your own risk. Tested on macOS with Python 3.14.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/liam_turnover86)

---

## What It Does

Watches two directories simultaneously:

| Source | Default Path | Trigger |
|---|---|---|
| Screenshots | `~/Desktop` | Mac screenshot capture |
| AirDrop | `~/Downloads` | AirDrop file landing |

Converts incoming images to WebP and writes them to `~/Pictures/WebP_ss/`.

On startup it also backfills — converting any existing unconverted images already present.

---

## macOS Compatibility

| macOS Version | Name | Default Save Location | Screenshot Prefix |
|---|---|---|---|
| 10.0-10.13 | Cheetah - High Sierra | ~/Desktop | "Screen Shot" |
| 10.14 | Mojave | ~/Desktop | "Screenshot" |
| 10.15 | Catalina | ~/Desktop | "Screenshot" |
| 11 | Big Sur | ~/Desktop | "Screenshot" |
| 12 | Monterey | ~/Desktop | "Screenshot" |
| 13 | Ventura | ~/Desktop | "Screenshot" |
| 14 | Sonoma | ~/Desktop | "Screenshot" |
| 15 | Sequoia | ~/Desktop | "Screenshot" |

Both "Screenshot" and "Screen Shot" prefixes are handled automatically.
Custom prefixes (set via `defaults write com.apple.screencapture name`) are supported with graceful fallback.

Sonoma 14.4+ note: AirDrop files may land in `/private/tmp` instead of `~/Downloads` if Downloads is iCloud or Dropbox-backed. This script watches both locations automatically.

---

## Supported Input Formats

| Format | Notes |
|---|---|
| `.png` | macOS default screenshot format |
| `.jpg` / `.jpeg` | Common photo format |
| `.heic` | iPhone/AirDrop default (requires pillow-heif) |

Additional formats can be added by editing `IMAGE_EXTENSIONS` in the script.

---

## Output Naming Convention

Spaces replaced with `_` for shell-safe names.

Screenshots:
```
Screenshot 2026-02-24 at 3.17.07 PM.png   ->  SS_2026-02-24_at_3.17.07_PM_WebP.webp
Screen Shot 2019-06-15 at 9.30.00 AM.png  ->  SS_2019-06-15_at_9.30.00_AM_WebP.webp
```

AirDrop / other:
```
IMG_3847.HEIC          ->  IMG_3847_WebP.webp
Photo 2026-02-24.jpg   ->  Photo_2026-02-24_WebP.webp
```

---

## Dependencies

All free and open source. Install with one command.

| Package | Purpose | Required |
|---|---|---|
| Pillow | Image reading and WebP conversion | Yes |
| watchdog | Folder watching for new files | Yes |
| pillow-heif | HEIC format support | Optional |

---

## Requirements

- macOS 10.14 Mojave or later
- Python 3.9+

---

## Installation

```bash
git clone https://github.com/papa-bla-blah/screenshot_webp_converter.git
cd screenshot_webp_converter
pip install -r requirements.txt
```

For HEIC support:
```bash
pip install pillow-heif
```

---

## Usage

```bash
# Run silently (errors only)
python3 webp_converter.py

# Run with verbose output
python3 webp_converter.py --verbose
```

Verbose output example:
```
------------------------------------------------------------
WebP Screenshot Util  |  macOS 15.3.1
  Screenshots : /Users/you/Desktop
  AirDrop     : /Users/you/Downloads
  /private/tmp: watched (Sonoma AirDrop bug fallback)
  Output      : /Users/you/Pictures/WebP_ss
  Quality     : 95
  Formats     : .heic, .jpeg, .jpg, .png
------------------------------------------------------------
Backfilling 3 file(s) from Desktop...
Converted: SS_2026-02-24_at_3.17.07_PM_WebP.webp (412KB -> 187KB)
Watching for new images... (Ctrl+C to stop)
```

---

## Configuration

Edit the variables at the top of `webp_converter.py`:
VariableDefaultDescription`SCREENSHOTS_DIR~/Desktop`Screenshot source (macOS default)`FILTER_DESKTOP_BY_PREFIXTrue`Only convert screenshot-prefixed files on Desktop`AIRDROP_DIR~/Downloads`AirDrop source`WATCH_PRIVATE_TMPTrue`Also watch /private/tmp (Sonoma bug fallback)`OUTPUT_DIR~/Pictures/WebP_ss`WebP output directory`WEBP_QUALITY95`Quality 1-100 (95 = high quality lossy)`IMAGE_EXTENSIONS.png .jpg .jpeg .heic`Formats to watch`SCREENSHOT_PREFIXES("Screenshot ", "Screen Shot ")`Recognized prefixes`DELETE_SCREENSHOT_ORIGINALFalse`Delete original screenshot after conversion (opt-in)`DELETE_MODE"on_convert""on_convert"` = only new conversions; `"on_exists"` = also when output already existed

If you moved your screenshot folder via cmd+shift+5 -&gt; Options, update `SCREENSHOTS_DIR` and set `FILTER_DESKTOP_BY_PREFIX = False`.

---

## Run on Login (Optional)

```bash
cp launchd/com.example.webp-converter.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.webp-converter.plist
```

---

## Known Limitations

- Transparency (RGBA/PNG) is flattened to white background on conversion
- Watches directories non-recursively
- AirDrop detection relies on watchdog on_moved event; direct writes use on_created

---

## Support This Project

This is free software. If it saves you time, a tip is appreciated but never expected.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/liam_turnover86)

GitHub Sponsors also available via the Sponsor button at the top of this repo.

---

## License

MIT - free to use, modify, and distribute.
