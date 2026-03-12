# CLAUDE.md — Survey Cross-Section Drawing Tool (횡단면도)

## Project Overview

A **Kivy-based Python application** for creating civil engineering survey cross-section diagrams, packaged as an Android APK via Buildozer. All UI text is in Korean.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10 |
| UI Framework | Kivy 2.3.0 |
| Build System | Buildozer (not Gradle) |
| Rendering | Matplotlib (Agg backend) |
| Numerical | NumPy |
| Image Processing | Pillow |
| Networking | Requests |
| CI/CD | GitHub Actions |

## Repository Structure

```
android-app/
├── main.py              # Entire application source (~1050 lines)
├── buildozer.spec       # Android build configuration
├── README.md
├── CLAUDE.md            # This file
└── .github/
    └── workflows/
        └── build.apk.yml   # CI pipeline: build APK on push to main/master
```

This is a **monolithic single-file architecture** — all application code lives in `main.py`.

## Architecture

### Global State — `AppData` class

A mutable singleton holding all application state:
- `table_data` — list of survey points `[name, ΔL, ΔH, notes]`
- `sections` — array of 10 sections, each with `image`, `photos`, `photo_idx`
- `current_no` — index of the section being edited
- `opt_labels`, `opt_dims`, `opt_grid`, `opt_hatch` — rendering toggles
- `unit` — measurement unit (`mm` or `m`)
- `title_text` — drawing title

State is mutated directly and screens call `self._refresh()` to rebuild UI.

### Screen Navigation — `ScreenManager` (4 screens)

1. **InputScreen** — Data table CRUD, survey point editing, preset shortcuts
2. **DrawScreen** — Matplotlib-rendered cross-section diagram, toggle options, save PNG
3. **PhotoScreen** — Photo attachment via file chooser, gallery view, memo notes
4. **ExportScreen** — Save PNG/PDF/CSV, import CSV

Navigation is tab-based with buttons at the bottom of the screen.

### Code Layout in `main.py`

| Lines | Section |
|-------|---------|
| 1–36 | Imports and environment setup |
| 38–68 | Korean font configuration (cross-platform) |
| 70–108 | Constants, default data, color scheme |
| 111–211 | Utility functions (`mk_btn`, `mk_lbl`, `popup_msg`, `get_points`, etc.) |
| 213–337 | Drawing engine (`render_figure`, `place_labels`, `draw_dims`) |
| 339–994 | Screen classes (InputScreen, DrawScreen, PhotoScreen, ExportScreen) |
| 996–1052 | Main App class and entry point |

## Build & Run

### Local Development

```bash
# Install dependencies
pip install kivy==2.3.0 pillow matplotlib numpy requests

# Run locally (desktop)
python main.py
```

### Build Android APK

```bash
pip install buildozer cython==0.29.37
buildozer android debug
# Output: bin/*.apk
```

### Android Build Configuration (from `buildozer.spec`)

- **Package**: `org.survey.surveycrosssection`
- **Target API**: 35 (Android 15)
- **Min API**: 24 (Android 7.0)
- **Architecture**: arm64-v8a only
- **Orientation**: landscape
- **NDK**: 25b
- **Permissions**: READ_MEDIA_IMAGES, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO, WRITE_EXTERNAL_STORAGE

## CI/CD

GitHub Actions workflow (`.github/workflows/build.apk.yml`):
- **Triggers**: push to `main`/`master`, manual dispatch
- **Runner**: ubuntu-22.04
- **Steps**: checkout → Python 3.10 → Java 17 → system deps → Cython → Buildozer → build APK → upload artifact
- **Artifact**: `횡단면도-APK` (retained 30 days)

## Key Conventions

- **No tests exist** — there is no test suite or test framework configured
- **No linter configured** — no pylint, flake8, or pre-commit hooks
- **Korean UI** — all user-facing strings are in Korean; CJK font setup is required
- **Matplotlib Agg backend** — headless rendering for Android compatibility (set via env vars `MPLCONFIGDIR=/tmp`, `MPLBACKEND=Agg`)
- **No persistence layer** — data lives in memory only; CSV import/export is the save mechanism
- **Single-threaded** — Kivy event loop; use `Clock.schedule_once` to defer heavy work

## Common Patterns

### Creating UI widgets
Use factory helpers: `mk_btn(text, callback)`, `mk_lbl(text)`, `mk_input(text, hint)`

### Drawing cross-sections
`render_figure(target, ...)` renders to either a Kivy texture (for display) or a file (PNG/PDF)

### File save paths
`get_save_dir()` resolves the appropriate download directory across platforms (Windows, macOS, Android)

### Popups / Dialogs
`popup_msg(title, msg)` for alerts, `popup_confirm(title, msg, callback)` for confirmations

## Things to Watch Out For

- All code is in one file — changes to one screen can affect others through `AppData`
- No input validation beyond basic type checking on numeric fields
- Matplotlib rendering blocks the UI thread briefly
- Fixed 10-section limit (pre-allocated array, not dynamic)
- No error handling around file I/O or rendering
