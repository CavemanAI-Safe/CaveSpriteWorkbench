# CaveSprite Workbench — User's Manual

A CavemanAI tool for generating animated sprite-sheet filmstrips for audio
plugin UI controls and app interfaces: knobs, LED meters, latching buttons,
switches, preamp tubes, and VU meters.

---

## 1. Getting Around

### 1.1 The Layout

The window is split into two areas:

- **Left — Control Gutter (~20% of the window width).** The CaveSprite logo
  is pinned at the top. Everything below it is that tab's controls — the
  content swaps automatically when you click a different tab on the right.
- **Right — Workspace.** Six tabs, one per engine. Each tab's workspace has
  the same two-part shape:
  1. A **live interactive canvas** at the top — a quick, abstract "feel
     test" you can drag/click to preview behavior, before you've rendered
     anything.
  2. A **Sprite Range Preview** at the bottom — once you render, this shows
     the *actual* generated filmstrip. Drag its slider to scrub through
     every frame, exactly as it will appear exported.

### 1.2 The Render → Export Pattern

Every tab follows the same two-step flow:

1. **Render** (button text varies by tab, e.g. *"Render Knob Filmstrip"*) —
   builds the sprite sheet in memory and loads it into the Sprite Range
   Preview at the bottom of the workspace. Nothing is written to disk yet.
2. **Export** (e.g. *"Export Sprite Sheet (.png)"*) — opens a save dialog and
   writes the rendered sheet to a PNG file. This button stays disabled until
   you've rendered at least once.

**Always scrub the Sprite Range Preview before exporting.** It's showing you
the literal frames that will be written to disk.

### 1.3 Output Format

Every export is a single vertical PNG **filmstrip**: one column, with each
animation frame stacked directly below the previous one —
`sheet_height = frame_height × frame_count`. This is the standard layout
most game engines and JUCE-based plugin frameworks expect for
frame-by-frame sprite animation.

---

## 2. Knob Engine

Generates a rotating-knob filmstrip from a single knob image (or a whole
folder of them at once).

### Sidebar Controls

**1. Knob Source**
- **Select Single File** — pick one knob PNG/JPG to animate.
- **Select Batch Folder** — pick a folder; every image inside will be
  processed with the same settings when you export (see 2.1 below).

**2. Rotation Sweep**
- **Min Angle / Max Angle** — the rotation range in degrees, e.g. `-135` to
  `135` for a classic 270° knob sweep.
- **Sprite Style** — choose:
  - *Continuous Sweep* — uses the **Frame Count** field below for a smooth
    animation.
  - *3 / 4 / 5 / 6 / 7-Position Step Knob* — locks Frame Count to that exact
    number and renders one frame per detent position, evenly spaced from Min
    to Max Angle. Use this for selector-style knobs that click into fixed
    positions rather than sweeping continuously.
- **Frame Count** — only editable in Continuous Sweep mode.
- **Source Indicator Already Drawn at Min Angle** (checked by default) —
  turn this **on** if your source PNG's indicator/pointer graphic is already
  drawn at the Min Angle position (very common for knob art). Frame 0 will
  then be an exact, unrotated copy of your source image, rotating forward
  from there. Turn it **off** only if your source art's indicator points
  straight up (North) at rest.

**3. Interactive Feel Test** — drag the slider to preview the rotation on an
abstract knob graphic (doesn't require rendering first).

**Render Knob Filmstrip** / **Export Sprite Sheet (.png)**

### 2.1 Batch Mode Notes

When a batch folder is selected, **Render** previews just the first image
found (so you can sanity-check your settings), but **Export** processes
*every* image in that folder and writes the results into a new
`sprite_exports` subfolder inside it, each named `<original filename>_sprite.png`.

---

## 3. Dial Scale Designer

Builds the printed tick/label ring that sits **around** a knob — the value
scale, major/minor tick marks, and (optionally) a colored background track
or highlight zone. This is a **static image**, not an animated filmstrip: it
exports as a single transparent-background PNG meant to sit as its own
layer behind or around your separately-animated Knob Engine sprite.

### Sidebar Controls

**1. Reference Knob (Preview Only)**
- **Load Reference Knob Image (Optional)** — load your actual knob art so
  the live preview shows exactly how the scale will look around your real
  knob, instead of a generic placeholder disc.
- **Knob Diameter (px)** — the pixel diameter of the knob this scale
  surrounds. This is a real geometry input, not just cosmetic — it's what
  the tick ring's inner radius is calculated from.
- **Include Reference Knob Graphic in Export** — off by default, so the
  exported PNG's center stays transparent (the normal case: your animated
  knob sprite sits on top of it at runtime). Turn on only if you specifically
  want the reference knob baked into the same PNG.

**2. Sweep & Value Range**
- **Min Angle / Max Angle** — the rotation range the scale spans, matching
  your knob's own rotation range from the Knob Engine tab.
- **Min Value / Max Value** — the numeric range the scale represents.
- **Value Scale** — *Linear* or *Logarithmic*. Either way, major ticks stay
  **physically evenly spaced** around the sweep (how real printed gear is
  made) — Logarithmic just changes what *values* get labeled at those even
  positions, progressing by ratio instead of by difference (e.g. a
  frequency dial's 100 / 200 / 500 / 1k / 2k / 5k / 10k / 20k). Logarithmic
  requires Min Value greater than 0.

**3. Major Ticks**
- **Number of Major Ticks** — 2 to 21.
- **Tick Length (px) / Tick Width (px) / Major Tick Color**
- **Gap from Knob Edge (px)** — space between the knob's edge and where
  ticks begin.

**4. Major Tick Labels**
- **Decimal Places** and **Label Suffix** (e.g. `dB`, `Hz`, `%`) control how
  auto-generated label text is formatted.
- **Auto-Fill Labels From Range** — (re)computes every label from Min
  Value/Max Value/Value Scale using the current Decimal Places and Suffix.
- **Font Size (px) / Label Color / Label Gap (px)** (gap = space between the
  tick end and the label text).
- **Per-Tick Label Text** — one editable text box per major tick, so you can
  override any individual label to custom text (e.g. `∞`, `MIN`, `Unity`,
  `+3`) instead of the auto-computed value. This list automatically rebuilds
  when you change Number of Major Ticks, preserving whatever you've already
  typed wherever possible.

**5. Sub-Ticks**
- **Sub-Ticks Between Majors** — 0 to 10 unlabeled minor ticks placed evenly
  between each pair of major ticks.
- **Sub-Tick Length (px) / Width (px) / Color**

**6. Arc Track & Highlight Zone**
- **Show Background Track** — a colored arc band following the full sweep,
  just outside the knob edge (the ring visible in most of the screenshots
  above).
- **Track Color / Track Width (px) / Track Gap from Knob Edge (px)**
- **Show Highlight Zone** — an additional colored band over just a portion
  of the sweep, defined by **Start Value** / **End Value** — useful for
  marking a "danger zone," a boost range, or a sweet spot.
- **Highlight Color**

**7. Canvas**
- **Canvas Padding (px)** — extra transparent margin around the outermost
  label text in the exported image.

**Render Dial Scale** / **Export Scale Image (.png)**

### Workspace

- **Live Dial Scale Preview** updates in real time as you change *any*
  setting — no Render click needed — and shows your loaded reference knob
  (or the placeholder disc) composited in the center so you can judge
  spacing and proportions immediately.
- **Exported Scale Image Preview** (the same Sprite Range Preview pattern
  used elsewhere) only updates when you click **Render**, and shows exactly
  what will be written to disk — including the transparent center, unless
  you've checked *Include Reference Knob Graphic in Export*.

---

## 4. LED Meter Engine

Generates a **true blended level-meter** filmstrip: frame 0 is fully dark,
the last frame is fully lit, and every frame in between lights up
progressively more segments — the standard format for an animated VU/level
indicator built from discrete LEDs.

### Sidebar Controls

**1. Array Configuration**
- **LED Shape** — Rectangle, Circle, or Triangle.
- **LED Count** — number of individual LED segments (the export will have
  `LED Count + 1` frames: one for each fill level from 0 up to full).
- **Orientation**:
  - *Vertical* — LEDs stacked bottom-to-top, first segment at the bottom.
  - *Horizontal* — LEDs in a row, left-to-right.
  - *Arc (Half-Circle)* — LEDs fanned across a 180° dome from a pivot at the
    bottom-center, first segment at the left horizon, sweeping up and over
    to the last segment at the right horizon — a classic "rainbow" VU arc.
- **LED Width / LED Height (px)** — size of each individual segment.
- **Spacing (px)** — gap between segments.
- **Inner Bevel** — adds a subtle glossy highlight/shadow to each segment.
- **Soft Glow on Lit Segments** — adds a soft blur/glow around lit segments.

**2. Color Gradient Preset** — choose a built-in color ramp (*Classic VU
(Green-Yellow-Red)*, *Caveman (Teal-Purple)*, *Neon Blue-Magenta*, *Amber
Mono*), or select **Custom Gradient** to unlock the **Start Color** / **End
Color** pickers and define your own two-color ramp.

**3. Interactive Level Test** — drag to preview a generic level-meter feel
(this abstract preview always shows as a simple bar regardless of your
chosen Shape/Orientation — scrub the actual Sprite Range Preview below for a
true look at your specific settings).

**Render LED Meter Filmstrip** / **Export Sprite Sheet (.png)**

---

## 5. Button Latching Engine

Generates a press-and-latch animation for an illuminated pushbutton, from a
single "cap" graphic.

### Sidebar Controls

**1. Cap Graphic**
- **Select Cap Image...** — load your own button cap art. A default
  CavemanAI-styled cap is used until you do.

**2. Visual Overlays**
- **Overlay Metallic Bevel** — adds a brushed-metal-look rim highlight.
- **Overlay Center LED Indicator** — adds a center LED dot that brightens as
  the button presses in.
- **LED Color** — the color of that center indicator (swatch shows current
  color).

**3. Motion Parameters**
- **Frame Size (px)** — output frame width/height (square).
- **Total Frames** — number of animation frames from released to pressed.
- **Press Travel (px)** — how far the cap visually moves downward at full
  press.
- **Shadow Alpha** — intensity of the drop shadow under the cap.

**Export Button Sprite Sheet (.png)**

### Workspace

- **Interactive Feeling Test** — click the button graphic itself to toggle
  between released and latched; it plays the actual rendered frames as a
  quick press animation, so you can feel the timing.
- **Sprite Range Preview** below it scrubs the same real filmstrip
  frame-by-frame.

The button re-renders automatically whenever you change a setting — there's
no separate Render button on this tab.

---

## 6. Switch & Toggle Builder

Builds a two-state (or multi-frame) toggle/selector switch filmstrip, either
from two separate state images or by slicing an existing filmstrip.

### Sidebar Controls

**Generation Mode** — choose one:
- **Dual Source (Up/Down Images → Filmstrip)** — combine two separate
  images (an "off/down/left" state and an "on/up/right" state) into a
  2-frame filmstrip.
- **Sprite Slice & Rotate (Left/Right → Up/Down)** — take an existing
  multi-frame filmstrip and re-slice/rotate it (useful for converting a
  horizontally-animated asset into a vertical filmstrip, or vice versa).

**Dual Image Inputs** *(Dual Source mode)*
- **Load State 0 (Off / Down / Left)**
- **Load State 1 (On / Up / Right)**

**Sprite Sheet Input** *(Sprite Slice mode)*
- **Load Existing Filmstrip**
- **Frame Count** — how many frames the loaded filmstrip already contains.

**Processing Options**
- **Rotation Filter** — No Rotation, Rotate 90° CW, Rotate 90° CCW, or
  Rotate 180° — applied to every frame during processing.

**Interactive Test** — drag the Lever Position slider to preview toggle
motion on an abstract lever graphic.

**Generate Switch Filmstrip** / **Export Sprite File (.png)**

---

## 7. Preamp Tube Engine

Generates a glowing vacuum-tube filmstrip whose filament/plate glow responds
to a chosen drive curve — for an animated "tube is working harder" indicator.

### Sidebar Controls

**1. Tube Asset & Dimensions**
- **Load Custom Tube Image (Optional)** — if skipped, a synthesized 12AX7-style
  glass shell is drawn procedurally.
- **W / H** — output frame width/height.

**2. Gain & Filament Glow**
- **Frame Count**
- **Drive Curve** — Linear Gain, Logarithmic (Audio), or Overdrive
  (Exponential) — controls how glow intensity ramps across the frame range.
- **Idle Glow** — baseline glow at frame 0 (a real tube is never fully dark
  at idle).
- **Glow Spread** — how far the glow radius extends outward.
- **Set Filament Glow Color**
- **Render Internal Glass Reflections** — adds a soft diagonal specular
  highlight across the glass.

**3. Interactive Drive Test** — drag to preview glow intensity live.

**Render Preamp Tube Filmstrip** / **Export Sprite Sheet (.png)**

---

## 8. VU Meter Engine

Generates an analog VU-style needle-meter filmstrip, sweeping a needle
across a meter face image from a calibrated pivot point.

### Sidebar Controls

**1. Meter Assets**
- **Load VU Meter Face** — **required before rendering.**
- **Use Overlay Needle Image** — off by default, which draws a clean vector
  needle. Turn on to use your own needle graphic instead.
- **Load Needle Asset** — only enabled when Overlay is on.
- **Set Vector Needle Color** — only relevant when Overlay is off.

**2. Pivot & Needle Calibration**
- **Pivot X / Pivot Y (% Width/Height)** — where the needle's rotation point
  sits on the face image, as a percentage of the image's width/height.
- **Needle Length** — 20%–300%. Scales the needle's length only (not its
  thickness) — 100% is natural length.
- **Needle Orientation** — where the needle rests at its zero position:
  - *Vertical (Rests Pointing Up)* — standard meter, sweeps left-right.
  - *Horizontal (Rests Pointing Right)* / *Horizontal (Rests Pointing Left)*
    — for meters mounted sideways, sweeps up-down.
  - *Vertical (Rests Pointing Down)*
  Your Min/Max Angle values (below) are always measured relative to this
  rest position, so the same sweep values work in any orientation.

**3. Sweep & Frame Parameters**
- **Frame Count**
- **Min Angle (-20 VU) / Max Angle (+3 VU)** — the needle's rotation range
  relative to the rest orientation above.

**4. Interactive Test Signal** — drag to preview needle position live on the
calibration canvas.

**5. Live Canvas Zoom** — zoom the calibration canvas above (100%–400%) for
fine pivot alignment. Two ways to control it:
- The slider (or the **Reset** button to snap back to 100%).
- Scroll your mouse wheel directly over the canvas.
Zooming is always anchored on the pivot point, so the needle stays in view
as you zoom in rather than drifting off-screen. This only affects the
on-screen preview — the exported sprite always renders at full native
resolution regardless of zoom level.

**Render VU Meter Filmstrip** / **Export Sprite Sheet (.png)**

> **Tip:** if Render does nothing, make sure you've loaded a meter face
> image in Section 1 first — it's required.

---

## 9. General Tips

- **Nothing is exported until you click Export.** Rendering only updates
  the on-screen preview.
- **Drag-and-drop:** dropping an image file onto the window while the Knob
  Engine tab is active will load it as that tab's single-file source.
- **Scrub before you export.** The Sprite Range Preview on every tab shows
  the literal frames that will be written to disk — it's the fastest way to
  catch a bad frame, a misaligned needle, or an off-by-one before exporting.
- **Frame counts:** for the LED Meter Engine specifically, the exported
  frame count is always `LED Count + 1` (one frame per fill level, including
  the fully-dark starting frame) — it isn't set directly.
