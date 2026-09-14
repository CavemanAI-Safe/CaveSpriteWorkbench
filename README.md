# CaveSpriteWorkbench
A CavemanAI-branded desktop tool for generating animated UI sprite sheets for
audio plugins and game/app interfaces — rotating knobs, LED level meters,
latching buttons, toggles/switches, glowing preamp tubes, and analog VU
meters — all from one app.

Every engine renders real, exportable PNG filmstrips (one sprite sheet per
control, stacked frame-by-frame vertically), and every tab lets you scrub
through the actual rendered frame range before you export, so you can check
the animation looks right without leaving the app.

## Requirements

- Python 3.9 or newer (developed and tested on 3.12)
- The packages listed in `requirements.txt` (PySide6 + Pillow)

## Installation

```bash
pip install -r requirements.txt
```

If your system enforces PEP 668 (externally-managed Python) and `pip
install` refuses to run, use:

```bash
pip install -r requirements.txt --break-system-packages
```

or install into a virtual environment instead:

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Project Folder Setup

Keep these three items together in the same folder:

```
your-project-folder/
├── CaveSpriteWorkbench.py
├── CaveSprite.jpeg          <- the CavemanAI logo, shown at the top of the sidebar
└── requirements.txt
```

The app looks for `CaveSprite.jpeg` right next to the script. If it isn't
there, the app still runs fine — the sidebar just shows a text label instead
of the logo image.

## Running

```bash
python3 CaveSpriteWorkbench.py
```

## What's Inside

A persistent control gutter sits on the left (~20% of the window width) with
the CaveSprite logo pinned at the top; its contents swap to match whichever
tab is selected on the right. The six tabs are:

| Tab | What it generates |
|---|---|
| **Knob Engine** | Rotating knob filmstrips — continuous sweep or fixed 3–7 position "step" knobs |
| **Dial Scale Designer** | The printed tick/label ring that surrounds a knob — major/sub ticks, per-tick labels, background track, highlight zone |
| **LED Meter Engine** | Blended LED level-meter filmstrips — Vertical, Horizontal, or Arc (half-circle) layouts |
| **Button Latching Engine** | Press/latch animations for illuminated pushbuttons |
| **Switch & Toggle Builder** | Two-state or multi-frame toggle/selector switch filmstrips |
| **Preamp Tube Engine** | Glowing vacuum-tube filmstrips driven by a gain/drive curve |
| **VU Meter Engine** | Analog needle-meter filmstrips, with vector or image-overlay needles |

See **`CaveSprite_Workbench_User_Manual.md`** for full, tab-by-tab usage
instructions.

## Output

Every tab has a **Render** step (builds the sprite sheet and loads it into
the on-screen scrub preview) and a separate **Export** step (writes the PNG
to disk). Nothing is written to disk until you export. Exported files are
plain vertical PNG filmstrips: `frame_width × (frame_height × frame_count)`,
ready to slice in a game engine, JUCE plugin, or any sprite-sheet-aware
framework.

## Troubleshooting

- **Blank/black preview area**: you need to click the tab's **Render**
  button at least once before the scrub preview has anything to show.
- **Export button stays disabled**: same cause — render first.
- **Logo not showing**: confirm `CaveSprite.jpeg` is in the same folder as
  `CaveSpriteWorkbench.py`, not a subfolder.
- **VU Meter tab does nothing on Render**: load a meter *face* image first
  (Section 1 of the sidebar) — the face is required before rendering.
