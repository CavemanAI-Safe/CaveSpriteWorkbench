"""
CaveSprite Workbench — CavemanAI UI Asset Generator
=====================================================
Unified build combining:
  - CaveSpriteWB1: Button Latching engine + LED engine (rebuilt as a true
    blended level-meter filmstrip instead of an on/off 2-frame strip)
  - CaveSpriteWB3: Preamp Tube engine + Switch/Toggle engine, and the base
    VU Meter rendering math (pivot calibration, vector/overlay needle)
  - CaveSpriteWB6: CavemanAI brand stylesheet + the "live range preview
    before export" UX from its VU tab, generalized to every engine tab

Layout: a persistent 20%-width control gutter on the left (logo pinned at
the top, controls swapped per selected tab) and a tabbed workspace on the
right containing a live parametric feel-test canvas plus a scrub preview
that lets you inspect the *actual* rendered sprite across its full frame
range before exporting.
"""

import sys
import os
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

from PySide6.QtCore import Qt, QRect, QRectF, QPointF, QTimeLine, Signal
from PySide6.QtGui import (
    QColor, QImage, QPainter, QPixmap, QPen, QBrush, QFont,
    QRadialGradient, QLinearGradient, QTransform,
    QDragEnterEvent, QDropEvent
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStackedWidget, QLabel, QPushButton, QSlider, QSpinBox,
    QDoubleSpinBox, QCheckBox, QFileDialog, QGroupBox, QSplitter,
    QScrollArea, QComboBox, QColorDialog, QFormLayout, QFrame,
    QMessageBox, QStyle, QSizePolicy, QLineEdit
)

# =============================================================================
# CAVEMANAI BRAND PALETTE & STYLESHEET
# =============================================================================
COLOR_CAVE_TEAL = "#25EFCB"       # Core / Action / Accent
COLOR_GALAXY_PURPLE = "#160D32"   # Background / Surface
COLOR_STAR_LAVENDER = "#A4A1ED"   # Text / Secondary Elements
COLOR_BORDER_INDIGO = "#331A76"   # Containment / Borders

CAVEMAN_STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {COLOR_GALAXY_PURPLE};
        color: {COLOR_STAR_LAVENDER};
        font-family: 'Cave Sans Rounded', 'SF Pro Rounded', 'Segoe UI Rounded', sans-serif;
        font-size: 13px;
    }}
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER_INDIGO};
        background: {COLOR_GALAXY_PURPLE};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background: #1e1345;
        color: {COLOR_STAR_LAVENDER};
        border: 1px solid {COLOR_BORDER_INDIGO};
        padding: 8px 14px;
        font-weight: bold;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {COLOR_BORDER_INDIGO};
        color: {COLOR_CAVE_TEAL};
        border-bottom: 3px solid {COLOR_CAVE_TEAL};
    }}
    QGroupBox {{
        border: 1px solid {COLOR_BORDER_INDIGO};
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 10px;
        font-weight: bold;
        color: {COLOR_CAVE_TEAL};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
    }}
    QPushButton {{
        background-color: {COLOR_CAVE_TEAL};
        color: {COLOR_GALAXY_PURPLE};
        border: none;
        border-radius: 5px;
        padding: 7px 12px;
        font-weight: bold;
    }}
    QPushButton:hover {{ background-color: #51ffe0; }}
    QPushButton:pressed {{ background-color: #1cccae; }}
    QPushButton:disabled {{
        background-color: {COLOR_BORDER_INDIGO};
        color: #6c62a0;
    }}
    QLabel {{ color: {COLOR_STAR_LAVENDER}; }}
    QSlider::groove:horizontal {{
        border: 1px solid {COLOR_BORDER_INDIGO};
        height: 6px;
        background: #110926;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {COLOR_CAVE_TEAL};
        width: 14px; height: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }}
    QSpinBox, QDoubleSpinBox, QComboBox {{
        background: #1a0f3d;
        border: 1px solid {COLOR_BORDER_INDIGO};
        color: {COLOR_CAVE_TEAL};
        padding: 4px 6px;
        border-radius: 4px;
        font-weight: bold;
    }}
    QCheckBox {{ color: {COLOR_STAR_LAVENDER}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {COLOR_BORDER_INDIGO};
        background: #1a0f3d;
        border-radius: 4px;
    }}
    QCheckBox::indicator:checked {{ background: {COLOR_CAVE_TEAL}; }}
    QScrollArea {{ border: none; background: {COLOR_GALAXY_PURPLE}; }}
    QSplitter::handle {{ background-color: {COLOR_BORDER_INDIGO}; }}
"""

SCRUB_PREVIEW_STYLE = (
    f"border: 1px dashed {COLOR_BORDER_INDIGO}; background: #0d0620; "
    "border-radius: 6px;"
)

# Location of the CaveSprite logo — lives next to this script in the project folder.
SCRIPT_DIR = Path(__file__).resolve().parent
LOGO_PATH = SCRIPT_DIR / "CaveSprite.jpeg"


# =============================================================================
# SHARED UTILITIES
# =============================================================================
def pillow_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    rgba_img = pil_img.convert("RGBA")
    data = rgba_img.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba_img.width, rgba_img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


def remove_background_chroma(image: QImage, target_color: QColor, tolerance: int) -> QImage:
    """Removes a solid background color based on a color tolerance threshold."""
    img = image.convertToFormat(QImage.Format_ARGB32)
    width, height = img.width(), img.height()
    tr, tg, tb = target_color.red(), target_color.green(), target_color.blue()
    for y in range(height):
        for x in range(width):
            c = QColor(img.pixel(x, y))
            if abs(c.red() - tr) <= tolerance and abs(c.green() - tg) <= tolerance and abs(c.blue() - tb) <= tolerance:
                img.setPixelColor(x, y, QColor(0, 0, 0, 0))
    return img


def wrap_in_scroll(content: QWidget) -> QScrollArea:
    """Wraps a control-panel widget in a borderless scroll area so tall
    control stacks never overflow the fixed-width sidebar gutter."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(content)
    return scroll


# =============================================================================
# GENERIC "LIVE RANGE PREVIEW" WIDGET
# -----------------------------------------------------------------------------
# This is the feature CaveSpriteWB6's VU Meter tab pioneered — real-time
# viewing of the *actual rendered* sprite sheet across its full frame range
# before exporting. Every engine tab in this workbench gets one.
# =============================================================================
class SpriteScrubPreview(QGroupBox):
    def __init__(self, title="Sprite Range Preview (before export)"):
        super().__init__(title)
        layout = QVBoxLayout(self)

        self.image_label = QLabel("Render a sprite to preview its frames here.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet(SCRUB_PREVIEW_STYLE)
        # Ignored size policy: don't let the label's own sizeHint (which Qt
        # derives from whatever pixmap is currently set) influence layout.
        # Without this, scaling a new frame to "the label's current width"
        # and then setting it back on the label can nudge that width a
        # little wider each time — compounding on every scrub step, most
        # visibly with wide (Horizontal LED) sprites. Ignored makes the
        # label purely take whatever space the layout gives it.
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.image_label)

        scrub_row = QHBoxLayout()
        self.lbl_frame = QLabel("Frame: -/-")
        self.lbl_frame.setMinimumWidth(90)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._render_frame)
        scrub_row.addWidget(self.lbl_frame)
        scrub_row.addWidget(self.slider, 1)
        layout.addLayout(scrub_row)

        self.sheet_pixmap = None
        self.frame_w = 0
        self.frame_h = 0
        self.total_frames = 0

    def set_sheet(self, sheet, frame_w: int, frame_h: int, total_frames: int):
        """`sheet` may be a QPixmap (Qt-rendered engines) or a PIL.Image
        (Pillow-rendered engines) — either is accepted transparently."""
        if isinstance(sheet, Image.Image):
            self.sheet_pixmap = pillow_to_qpixmap(sheet)
        else:
            self.sheet_pixmap = sheet
        self.frame_w = max(1, frame_w)
        self.frame_h = max(1, frame_h)
        self.total_frames = max(1, total_frames)

        self.slider.blockSignals(True)
        self.slider.setRange(0, self.total_frames - 1)
        self.slider.setValue(self.total_frames - 1)
        self.slider.blockSignals(False)
        self._render_frame(self.total_frames - 1)

    def clear(self):
        self.sheet_pixmap = None
        self.total_frames = 0
        self.slider.setRange(0, 0)
        self.image_label.setText("Render a sprite to preview its frames here.")
        self.lbl_frame.setText("Frame: -/-")

    def _render_frame(self, index: int):
        if not self.sheet_pixmap or self.total_frames == 0:
            return
        index = max(0, min(index, self.total_frames - 1))
        src_rect = QRect(0, index * self.frame_h, self.frame_w, self.frame_h)
        frame_pix = self.sheet_pixmap.copy(src_rect)
        # Scale against THIS group box's own width/height, not the label's —
        # the label's size can be influenced by the pixmap it's holding, so
        # using it as the scaling target creates a feedback loop. This
        # widget's own geometry is set purely by the surrounding tab layout.
        target_w = max(80, self.width() - 24)
        target_h = max(80, self.image_label.minimumHeight())
        scaled = frame_pix.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.lbl_frame.setText(f"Frame: {index + 1}/{self.total_frames}")


# =============================================================================
# LIVE PARAMETRIC "FEEL TEST" CANVASES  (from CaveSpriteWB6)
# =============================================================================
class KnobCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.val = 0.5
        self.min_a = -135.0
        self.max_a = 135.0
        self.setMinimumSize(220, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        cx, cy = rect.width() / 2, rect.height() / 2
        r = min(cx, cy) - 30

        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.5)
        grad.setColorAt(0.0, QColor("#3b2082"))
        grad.setColorAt(1.0, QColor(COLOR_GALAXY_PURPLE))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(COLOR_CAVE_TEAL), 2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        angle = self.min_a + (self.val * (self.max_a - self.min_a))
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.setPen(QPen(QColor(COLOR_CAVE_TEAL), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, -int(r * 0.25), 0, -int(r * 0.85))
        painter.restore()


class LEDMeterCanvas(QWidget):
    """Live feel-test for the LED level meter — mirrors the same lit/unlit
    logic used by generate_led_meter_filmstrip() so the preview always
    matches what gets exported."""
    def __init__(self):
        super().__init__()
        self.segments = 10
        self.level = 0.5   # 0..1 across the meter's frame range
        self.active_color = QColor(COLOR_CAVE_TEAL)
        self.inactive_color = QColor("#1f1442")
        self.setMinimumSize(180, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        sw, sh, spacing = 60, 8, 4
        cx = rect.width() / 2 - sw / 2
        start_y = rect.height() - 30
        lit_count = int(round(self.level * self.segments))

        for i in range(self.segments):
            sy = start_y - (i * (sh + spacing))
            if sy < 20:
                break
            active = i < lit_count
            painter.setBrush(QBrush(self.active_color if active else self.inactive_color))
            painter.setPen(QPen(self.active_color.lighter(130) if active else QColor(COLOR_BORDER_INDIGO), 1))
            painter.drawRoundedRect(int(cx), int(sy), sw, sh, 2, 2)


class ButtonCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.is_pressed = False
        self.accent_color = QColor(COLOR_CAVE_TEAL)
        self.setMinimumSize(200, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        cx, cy = rect.width() / 2, rect.height() / 2
        bw = bh = 110
        b_rect = QRectF(cx - bw / 2, cy - bh / 2, bw, bh)
        offset = 4 if self.is_pressed else 0

        painter.setBrush(QBrush(QColor("#0d061f")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(b_rect.translated(0, 6), 16, 16)

        painter.setBrush(QBrush(QColor("#2a185c" if not self.is_pressed else "#1b0f3d")))
        painter.setPen(QPen(self.accent_color if self.is_pressed else QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(b_rect.translated(0, offset), 16, 16)

        led_color = self.accent_color if self.is_pressed else QColor("#442b82")
        painter.setBrush(QBrush(led_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy + offset), 10, 10)


class SwitchCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.pos = 0.0  # -1.0 .. 1.0
        self.setMinimumSize(200, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        cx, cy = rect.width() / 2, rect.height() / 2
        painter.setBrush(QBrush(QColor("#180c38")))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawEllipse(QPointF(cx, cy), 45, 45)

        angle = self.pos * 30.0
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(angle)
        painter.setPen(QPen(QColor(COLOR_CAVE_TEAL), 8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(0, 0, 0, -38)
        painter.restore()


class PreampCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.drive = 0.4
        self.warmup = 0.7
        self.glow_color = QColor(COLOR_CAVE_TEAL)
        self.setMinimumSize(200, 240)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        cx, cy = rect.width() / 2, rect.height() / 2
        glass = QRectF(cx - 40, cy - 80, 80, 140)

        glow_r = 20 + (self.drive * 25)
        r, g, b = self.glow_color.red(), self.glow_color.green(), self.glow_color.blue()
        grad = QRadialGradient(cx, cy + 20, glow_r)
        grad.setColorAt(0.0, QColor(min(255, r + 100), min(255, g + 100), min(255, b + 100), int(220 * self.warmup)))
        grad.setColorAt(0.6, QColor(r, g, b, int(180 * self.drive)))
        grad.setColorAt(1.0, QColor(r, g, b, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy + 20), glow_r, glow_r)

        painter.setPen(QPen(QColor(COLOR_STAR_LAVENDER), 2))
        painter.setBrush(QBrush(QColor(25, 14, 52, 140)))
        painter.drawRoundedRect(glass, 30, 30)


class VUMeterCanvas(QWidget):
    zoomChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self.face_pix = None
        self.needle_pix = None
        self.pivot_x_pct = 50.0
        self.pivot_y_pct = 82.0
        self.min_angle = -42.0
        self.max_angle = 42.0
        self.val = 0.5
        self.use_overlay = True
        self.vector_color = QColor(COLOR_CAVE_TEAL)
        self.needle_length_pct = 100.0
        self.orientation_offset = 0.0
        self.zoom = 1.0
        self.setMinimumSize(260, 200)
        self.setToolTip("Scroll to zoom in/out, centered on the pivot point.")

    def wheelEvent(self, event):
        step = 0.1 if event.angleDelta().y() > 0 else -0.1
        new_zoom = max(1.0, min(4.0, round(self.zoom + step, 2)))
        if new_zoom != self.zoom:
            self.zoom = new_zoom
            self.update()
            self.zoomChanged.emit(self.zoom)
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(COLOR_GALAXY_PURPLE))
        painter.setPen(QPen(QColor(COLOR_BORDER_INDIGO), 2))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)

        cx, cy = rect.width() / 2, rect.height() / 2
        fw, fh = (self.face_pix.width(), self.face_pix.height()) if self.face_pix else (280, 180)
        base_scale = min((rect.width() - 40) / fw, (rect.height() - 40) / fh)

        # At 100% zoom the whole face is centered in the canvas (unchanged
        # from before). As zoom increases, scale up anchored on the pivot
        # point instead of the canvas center, so the needle/pivot you're
        # calibrating stays put on screen instead of drifting off it.
        pivot_content_x = fw * (self.pivot_x_pct / 100.0)
        pivot_content_y = fh * (self.pivot_y_pct / 100.0)
        anchor_x = (cx - fw * base_scale / 2.0) + pivot_content_x * base_scale
        anchor_y = (cy - fh * base_scale / 2.0) + pivot_content_y * base_scale

        scale = base_scale * self.zoom
        dw, dh = fw * scale, fh * scale
        dx = anchor_x - pivot_content_x * scale
        dy = anchor_y - pivot_content_y * scale

        if self.face_pix:
            painter.drawPixmap(QRectF(dx, dy, dw, dh).toRect(), self.face_pix)
        else:
            painter.setBrush(QBrush(QColor("#100826")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(dx, dy, dw, dh), 10, 10)

        px = dx + (dw * (self.pivot_x_pct / 100.0))
        py = dy + (dh * (self.pivot_y_pct / 100.0))
        angle = self.orientation_offset + self.min_angle + (self.val * (self.max_angle - self.min_angle))
        length_scale = self.needle_length_pct / 100.0

        if self.use_overlay and self.needle_pix:
            # size_scale keeps the overlay needle asset visually matched to
            # the face at whatever zoom/fit scale the canvas is displaying —
            # the actual export always draws needles at native resolution,
            # so this only affects this live preview, not the sprite output.
            draw_vu_needle_overlay(painter, self.needle_pix, px, py, angle, length_scale, size_scale=scale)
        else:
            draw_vu_needle_vector(painter, px, py, angle, dh * 0.65 * length_scale, self.vector_color)

        painter.setPen(QPen(QColor(COLOR_CAVE_TEAL), 1, Qt.DashLine))
        painter.drawLine(int(px - 12), int(py), int(px + 12), int(py))
        painter.drawLine(int(px), int(py - 12), int(px), int(py + 12))


# Shared needle-drawing helpers used by BOTH the live VUMeterCanvas preview
# and the actual render_vu_filmstrip() export path, so what you calibrate
# is exactly what gets baked into the sprite sheet.
def draw_vu_needle_vector(painter: QPainter, px: float, py: float, angle: float, length: float, color: QColor):
    painter.save()
    painter.translate(px, py)
    painter.rotate(angle)
    painter.setPen(QPen(QColor(0, 0, 0, 80), 2))
    painter.drawLine(2, 2, 2, int(-length + 2))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(color))
    points = [QPointF(-1.5, 10), QPointF(1.5, 10), QPointF(0.5, -length), QPointF(-0.5, -length)]
    painter.drawPolygon(points)
    painter.setBrush(QBrush(QColor(20, 20, 20)))
    painter.setPen(QPen(QColor(80, 80, 80), 1))
    painter.drawEllipse(QPointF(0, 0), 6, 6)
    painter.restore()


def draw_vu_needle_overlay(painter: QPainter, needle_pixmap: QPixmap, px: float, py: float, angle: float,
                            length_scale: float = 1.0, size_scale: float = 1.0):
    """`length_scale` stretches/shrinks the needle along its own long axis
    only (its authored height) while keeping its thickness (width) fixed —
    so a needle asset gets visibly longer or shorter rather than fatter.
    `size_scale` uniformly scales the whole needle asset — used by the live
    calibration canvas to keep the needle matched to the face image's
    current zoom/fit scale; the actual sprite export always draws at native
    resolution and leaves this at 1.0."""
    nw = needle_pixmap.width() * max(0.05, size_scale)
    nh = needle_pixmap.height() * max(0.05, size_scale)
    scaled_h = nh * max(0.05, length_scale)
    painter.save()
    painter.translate(px, py)
    painter.rotate(angle)
    painter.drawPixmap(QRectF(-nw / 2, -scaled_h * 0.85, nw, scaled_h).toRect(), needle_pixmap)
    painter.restore()


# =============================================================================
# INTERACTIVE "CLICK TO LATCH" PREVIEW  (from CaveSpriteWB1 — Button Engine)
# =============================================================================
class InteractiveButtonPreview(QWidget):
    """Plays the *actual* rendered button filmstrip between its rest and
    latched frames when clicked, so you can feel the press animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite_sheet = None
        self.frame_size = 128
        self.total_frames = 12
        self.current_frame = 0
        self.is_latched = False

        self.setFixedSize(128, 128)
        self.setCursor(Qt.PointingHandCursor)

        self.timeline = QTimeLine(130, self)
        self.timeline.setUpdateInterval(16)
        self.timeline.valueChanged.connect(self._on_value_changed)

    def update_spritesheet(self, pil_sheet: Image.Image, frame_size: int, total_frames: int):
        self.frame_size = frame_size
        self.total_frames = total_frames
        self.sprite_sheet = pillow_to_qpixmap(pil_sheet)
        self.setFixedSize(frame_size, frame_size)
        self.current_frame = total_frames - 1 if self.is_latched else 0
        self.update()

    def _on_value_changed(self, value: float):
        self.current_frame = int(round(value * (self.total_frames - 1)))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.sprite_sheet:
            self.is_latched = not self.is_latched
            self.timeline.stop()
            self.timeline.setDirection(QTimeLine.Forward if self.is_latched else QTimeLine.Backward)
            self.timeline.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.sprite_sheet:
            src_rect = QRect(0, self.current_frame * self.frame_size, self.frame_size, self.frame_size)
            painter.drawPixmap(QRect(0, 0, self.frame_size, self.frame_size), self.sprite_sheet, src_rect)


# =============================================================================
# GENERATION LOGIC — KNOB ENGINE  (base: CaveSpriteWB1, angle range from WB3)
# =============================================================================
def render_knob_filmstrip(source_img: Image.Image, num_frames: int,
                           min_angle: float = -135.0, max_angle: float = 135.0,
                           source_at_min_angle: bool = True) -> Image.Image:
    """`source_at_min_angle=True` (the common case) treats the source PNG's
    indicator as already drawn at `min_angle` — e.g. an image whose indicator
    is baked in at -135°. Each frame then rotates by the *delta* from that
    baseline, so frame 0 is an exact, unrotated copy of the source and the
    full sweep still lands on `max_angle` at the last frame.

    `source_at_min_angle=False` treats the source as drawn pointing North
    (0°) and rotates every frame to its absolute angle — the old behavior,
    useful if your indicator art is neutral/unrotated at rest."""
    base_image = source_img.convert("RGBA")
    width, height = base_image.size
    strip_image = Image.new("RGBA", (width, height * num_frames), (0, 0, 0, 0))
    resample_filter = Image.Resampling.BICUBIC
    sweep = max_angle - min_angle

    for i in range(num_frames):
        t = (i / (num_frames - 1)) if num_frames > 1 else 0.0
        if source_at_min_angle:
            angle = sweep * t          # delta from the source's baked-in min-angle pose
        else:
            angle = min_angle + sweep * t   # absolute angle from a North-pointing source
        rotated_frame = base_image.rotate(-angle, resample=resample_filter, expand=False)
        strip_image.paste(rotated_frame, (0, i * height), rotated_frame)

    return strip_image


# =============================================================================
# GENERATION LOGIC — LED LEVEL METER ENGINE
# -----------------------------------------------------------------------------
# Rebuilt from CaveSpriteWB1's LED tab. The original only produced a 2-frame
# strip (all-off / all-on). This version produces a true blended METER
# filmstrip: frame 0 is fully dark and frame `num_leds` is fully lit, with
# every frame in between lighting up exactly that many segments using the
# selected color gradient — the standard format for an animated level meter.
# =============================================================================
def interpolate_color(color_a, color_b, t):
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def get_preset_color(preset_name, index, total_count, start_color, end_color):
    t = index / max(1, (total_count - 1))
    if preset_name == "Custom Gradient":
        return interpolate_color(start_color, end_color, t)
    elif preset_name == "Classic VU (Green-Yellow-Red)":
        if t < 0.6:
            return interpolate_color((20, 220, 60), (240, 220, 20), t / 0.6)
        else:
            return interpolate_color((240, 220, 20), (255, 30, 40), (t - 0.6) / 0.4)
    elif preset_name == "Caveman (Teal-Purple)":
        return interpolate_color((37, 239, 203), (164, 161, 237), t)
    elif preset_name == "Neon Blue-Magenta":
        return interpolate_color((0, 210, 255), (255, 0, 180), t)
    else:  # Amber Mono
        return (255, 170, 0)


def generate_led_meter_filmstrip(
    num_leds: int = 10, led_width: int = 16, led_height: int = 10, spacing: int = 3,
    orientation: str = "Vertical", shape: str = "Rectangle",
    preset: str = "Classic VU (Green-Yellow-Red)",
    start_color: tuple = (37, 239, 203), end_color: tuple = (255, 50, 50),
    bevel: bool = True, glow: bool = True
):
    """Generates an (num_leds + 1)-frame filmstrip: frame 0 = all segments
    dark, frame num_leds = all segments lit, with a progressively filling
    meter in between — a genuine blended level-meter sprite sheet.

    `orientation` is one of "Vertical", "Horizontal", or "Arc (Half-Circle)".
    The arc mode fans the LEDs across a 180\u00b0 dome from a pivot at the
    bottom-center, index 0 at the left horizon sweeping up through the top
    and down to index num_leds-1 at the right horizon — a classic rainbow-
    style VU arc, built from discrete LED segments instead of a needle."""
    is_arc = orientation == "Arc (Half-Circle)"
    SS = 4  # supersample factor: draw shapes bigger, then downsample after any
             # rotation so a small Circle survives rotation as a circle instead
             # of degrading into a faceted diamond at low pixel counts.

    def draw_led_tile_hires(w: int, h: int, rgb: tuple, is_lit: bool) -> Image.Image:
        """Draws one LED shape at rest — apex/long-axis pointing 'up' — onto
        its own transparent tile at SS-times resolution for clean, anti-
        aliased edges. Used directly for linear layouts and rotated
        per-segment for the arc layout, so all three orientations share one
        drawing routine. Caller downsamples with finish_tile() after any
        rotation is applied."""
        sw, sh = w * SS, h * SS
        m = 2 * SS
        tile = Image.new("RGBA", (sw + 2 * m, sh + 2 * m), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        x0, y0, x1, y1 = m, m, m + sw - 1, m + sh - 1
        edge = max(1, SS)

        if shape == "Rectangle":
            d.rectangle([x0 - edge, y0 - edge, x1 + edge, y1 + edge], fill=(12, 8, 25, 255))
            d.rectangle([x0, y0, x1, y1], fill=(*rgb, 255))
            if bevel and (x1 - x0 > 2 * SS) and (y1 - y0 > 2 * SS):
                d.line([(x0, y0), (x1, y0)], fill=(255, 255, 255, 110 if is_lit else 30), width=edge)
                d.line([(x0, y0), (x0, y1)], fill=(255, 255, 255, 110 if is_lit else 30), width=edge)
                d.line([(x1, y0), (x1, y1)], fill=(0, 0, 0, 120), width=edge)
                d.line([(x0, y1), (x1, y1)], fill=(0, 0, 0, 120), width=edge)
        elif shape == "Circle":
            d.ellipse([x0 - edge, y0 - edge, x1 + edge, y1 + edge], fill=(12, 8, 25, 255))
            d.ellipse([x0, y0, x1, y1], fill=(*rgb, 255))
            if bevel and (x1 - x0 > 2 * SS) and (y1 - y0 > 2 * SS):
                # NOTE: PIL's ImageDraw.arc(..., width=N) breaks down into a
                # pac-man-style bite out of the circle when the stroke width
                # is large relative to the ellipse's radius (exactly our
                # case at supersampled scale) — a Pillow rendering
                # limitation, not something tunable away. Instead we paint
                # soft highlight/shadow blobs on a separate layer and clip
                # them to the circle's own silhouette, which can't produce
                # that artifact regardless of size.
                cx_c, cy_c = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
                overlay = Image.new("RGBA", tile.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                hi_alpha = 130 if is_lit else 35
                hx, hy = cx_c - rx * 0.30, cy_c - ry * 0.30
                hr_x, hr_y = rx * 0.62, ry * 0.62
                od.ellipse([hx - hr_x, hy - hr_y, hx + hr_x, hy + hr_y], fill=(255, 255, 255, hi_alpha))
                sx, sy = cx_c + rx * 0.35, cy_c + ry * 0.35
                sr_x, sr_y = rx * 0.55, ry * 0.55
                od.ellipse([sx - sr_x, sy - sr_y, sx + sr_x, sy + sr_y], fill=(0, 0, 0, 110))
                mask = Image.new("L", tile.size, 0)
                ImageDraw.Draw(mask).ellipse([x0, y0, x1, y1], fill=255)
                clipped = Image.composite(overlay, Image.new("RGBA", tile.size, (0, 0, 0, 0)), mask)
                tile = Image.alpha_composite(tile, clipped)
        else:  # Triangle — apex points "up" (radially outward at the arc's top)
            pts = [(x0 + (x1 - x0) / 2, y0), (x0, y1), (x1, y1)]
            pts_bg = [(x0 + (x1 - x0) / 2, y0 - edge), (x0 - edge, y1 + edge), (x1 + edge, y1 + edge)]
            d.polygon(pts_bg, fill=(12, 8, 25, 255))
            d.polygon(pts, fill=(*rgb, 255))
            if bevel:
                d.line([pts[0], pts[1]], fill=(255, 255, 255, 110 if is_lit else 30), width=edge)
                d.line([pts[1], pts[2]], fill=(0, 0, 0, 120), width=edge)
        return tile

    def finish_tile(hires_tile: Image.Image) -> Image.Image:
        """Downsamples a supersampled tile back to true pixel size with a
        high-quality filter — call this AFTER rotating, so rotated edges
        stay smooth instead of picking up the blocky aliasing that a small
        low-res rotate would introduce."""
        fw = max(1, round(hires_tile.width / SS))
        fh = max(1, round(hires_tile.height / SS))
        return hires_tile.resize((fw, fh), Image.Resampling.LANCZOS)

    if is_arc:
        # Radius chosen so num_leds segments (plus spacing) comfortably tile
        # the half-circle's arc length: half-circumference = pi * radius.
        arc_length = (num_leds * led_width) + (max(0, num_leds - 1) * spacing)
        radius = max(24.0, arc_length / math.pi)
        pad = led_width + led_height + 12
        strip_w = int(round(2 * radius + 2 * pad))
        strip_h = int(round(radius + 2 * pad))
        pivot_x = strip_w / 2.0
        pivot_y = strip_h - pad
    elif orientation == "Vertical":
        strip_w = led_width + 4
        strip_h = (led_height * num_leds) + (spacing * (num_leds - 1)) + 4
    else:
        strip_w = (led_width * num_leds) + (spacing * (num_leds - 1)) + 4
        strip_h = led_height + 4

    total_frames = num_leds + 1

    def draw_frame(lit_count: int) -> Image.Image:
        frame = Image.new("RGBA", (strip_w, strip_h), (0, 0, 0, 0))

        for i in range(num_leds):
            rgb = get_preset_color(preset, i, num_leds, start_color, end_color)
            is_lit = i < lit_count
            if not is_lit:
                rgb = (int(rgb[0] * 0.15), int(rgb[1] * 0.15), int(rgb[2] * 0.15))

            if is_arc:
                theta_deg = -90.0 + (i / (num_leds - 1)) * 180.0 if num_leds > 1 else 0.0
                theta_rad = math.radians(theta_deg)
                hires = draw_led_tile_hires(led_width, led_height, rgb, is_lit)
                rotated_hires = hires.rotate(-theta_deg, resample=Image.Resampling.BICUBIC, expand=True)
                rotated = finish_tile(rotated_hires)
                cx = pivot_x + radius * math.sin(theta_rad)
                cy = pivot_y - radius * math.cos(theta_rad)
                paste_x = int(round(cx - rotated.width / 2))
                paste_y = int(round(cy - rotated.height / 2))
                frame.paste(rotated, (paste_x, paste_y), rotated)
            else:
                if orientation == "Vertical":
                    idx = (num_leds - 1 - i)
                    x0, y0 = 2, 2 + idx * (led_height + spacing)
                else:
                    x0, y0 = 2 + i * (led_width + spacing), 2
                hires = draw_led_tile_hires(led_width, led_height, rgb, is_lit)
                if shape == "Triangle" and orientation == "Horizontal":
                    # Preserve the original horizontal look: apex points toward
                    # the direction of increasing signal (rightward) rather
                    # than "up", by rotating the at-rest tile 90° clockwise.
                    hires = hires.rotate(-90, resample=Image.Resampling.BICUBIC, expand=True)
                tile = finish_tile(hires)
                center_x, center_y = x0 + led_width / 2.0, y0 + led_height / 2.0
                paste_x = int(round(center_x - tile.width / 2.0))
                paste_y = int(round(center_y - tile.height / 2.0))
                frame.paste(tile, (paste_x, paste_y), tile)

        if glow and lit_count > 0:
            blurred = frame.filter(ImageFilter.GaussianBlur(2))
            frame = Image.alpha_composite(blurred, frame)
        return frame

    sheet = Image.new("RGBA", (strip_w, strip_h * total_frames), (0, 0, 0, 0))
    for f in range(total_frames):
        sheet.paste(draw_frame(f), (0, f * strip_h))

    metrics = {
        "led_size": (led_width, led_height),
        "footprint": (strip_w, strip_h),
        "sheet_size": (strip_w, strip_h * total_frames),
        "total_frames": total_frames,
    }
    return sheet, metrics


# =============================================================================
# GENERATION LOGIC — BUTTON LATCHING ENGINE  (CaveSpriteWB1, unchanged)
# =============================================================================
def create_radial_brushed_texture(size: int, intensity: int = 18) -> Image.Image:
    img = Image.new("L", (size, size), 128)
    pixels = img.load()
    cx, cy = size / 2.0, size / 2.0
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            angle = math.atan2(dy, dx)
            streak = math.sin(angle * 180) + math.sin(angle * 360) * 0.5
            noise = random.uniform(-intensity, intensity)
            val = int(128 + streak * 8 + noise)
            pixels[x, y] = max(0, min(255, val))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def generate_latching_spritesheet_from_image(
    source_img: Image.Image, frame_size: int = 128, total_frames: int = 12,
    max_travel: int = 8, shadow_intensity: int = 140,
    enable_bevel: bool = True, enable_led: bool = True,
    led_color: tuple = (37, 239, 203)
) -> Image.Image:
    sheet = Image.new("RGBA", (frame_size, frame_size * total_frames), (0, 0, 0, 0))

    padding = max(6, max_travel + 4)
    target_cap_size = frame_size - (padding * 2)
    cap_base = source_img.convert("RGBA").resize((target_cap_size, target_cap_size), Image.Resampling.LANCZOS)

    center_x = frame_size // 2
    cap_r = target_cap_size // 2
    brushed_noise = create_radial_brushed_texture(frame_size) if enable_bevel else None

    for i in range(total_frames):
        progress = i / (total_frames - 1) if total_frames > 1 else 0.0
        frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        y_offset = int(progress * max_travel)
        cy_beveled = center_x + y_offset

        draw_frame = ImageDraw.Draw(frame)
        housing_r = cap_r + 2
        draw_frame.ellipse(
            [center_x - housing_r, center_x - housing_r + y_offset // 2,
             center_x + housing_r, center_x + housing_r + y_offset // 2],
            fill=(15, 17, 22, 180)
        )

        shadow_blur = max(1, int(6 * (1.0 - progress * 0.6)))
        shadow_alpha = int(shadow_intensity * (1.0 - progress * 0.45))
        shadow_mask = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(shadow_mask)
        sh_draw.ellipse(
            [center_x - cap_r, center_x - cap_r + y_offset + 3,
             center_x + cap_r, center_x + cap_r + y_offset + 3],
            fill=(0, 0, 0, shadow_alpha)
        )
        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
        frame.paste(shadow_mask, (0, 0), shadow_mask)

        enhancer = ImageEnhance.Brightness(cap_base)
        darkened_cap = enhancer.enhance(1.0 - (progress * 0.20))
        cap_composite = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
        cap_composite.paste(darkened_cap, (padding, padding + y_offset), darkened_cap)

        if enable_bevel and brushed_noise:
            bevel_img = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
            bevel_pixels = bevel_img.load()
            lx, ly = -0.707, -0.707
            bevel_width = max(4, cap_r // 5)
            for y in range(frame_size):
                for x in range(frame_size):
                    dx, dy = x - center_x, y - cy_beveled
                    dist = math.hypot(dx, dy)
                    if dist <= cap_r and dist > (cap_r - bevel_width):
                        nx, ny = dx / cap_r, dy / cap_r
                        dot = max(0.0, nx * lx + ny * ly)
                        base_lum = 120 + int(dot * 110) - int(progress * 25)
                        noise_val = brushed_noise.getpixel((x, y)) - 128
                        final_lum = max(0, min(255, base_lum + noise_val // 2))
                        bevel_pixels[x, y] = (final_lum, final_lum + 2, final_lum + 5, 255)
            cap_composite.paste(bevel_img, (0, 0), bevel_img)

        if enable_led:
            led_r = max(4, cap_r // 5)
            led_draw = ImageDraw.Draw(cap_composite)
            ind_r = int(40 + (led_color[0] - 40) * progress)
            ind_g = int(45 + (led_color[1] - 45) * progress)
            ind_b = int(50 + (led_color[2] - 50) * progress)
            led_draw.ellipse(
                [center_x - led_r, cy_beveled - led_r, center_x + led_r, cy_beveled + led_r],
                fill=(ind_r, ind_g, ind_b, 255)
            )
            if progress > 0.1:
                glow_layer = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
                g_draw = ImageDraw.Draw(glow_layer)
                glow_alpha = int(255 * progress)
                g_draw.ellipse(
                    [center_x - led_r - 4, cy_beveled - led_r - 4, center_x + led_r + 4, cy_beveled + led_r + 4],
                    fill=(led_color[0], led_color[1], led_color[2], glow_alpha)
                )
                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
                cap_composite.paste(glow_layer, (0, 0), glow_layer)
            led_draw.ellipse(
                [center_x - led_r, cy_beveled - led_r, center_x + led_r, cy_beveled + led_r],
                outline=(20, 22, 28, 200), width=2
            )

        frame.paste(cap_composite, (0, 0), cap_composite)
        sheet.paste(frame, (0, i * frame_size))

    return sheet


# =============================================================================
# GENERATION LOGIC — DIAL SCALE DESIGNER
# -----------------------------------------------------------------------------
# Produces the printed tick/label ring that sits BEHIND or AROUND an
# (independently animated) knob sprite — not a filmstrip, a single static
# PNG with a transparent center where the knob itself lives.
# =============================================================================
def _get_dial_font(size: int):
    """Best-effort scalable font lookup that degrades gracefully across
    Pillow versions and platforms — never raises."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Arial.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()


def format_dial_value(value: float, decimals: int, suffix: str) -> str:
    if decimals <= 0:
        s = str(int(round(value)))
    else:
        s = f"{value:.{decimals}f}"
    return f"{s}{suffix}"


def draw_arc_band(base_img: Image.Image, cx: float, cy: float, r_in: float, r_out: float,
                   start_deg: float, end_deg: float, color: tuple, alpha: int = 255):
    """Paints a filled annular band (a ring segment) from r_in to r_out,
    sweeping start_deg..end_deg in the app's angle convention (0deg = up,
    positive = clockwise). Built from two pieslice masks rather than a
    stroked arc — PIL's thick-stroke arc rendering is unreliable at small
    radius-to-width ratios (see the LED Circle bevel fix), and a pieslice
    difference sidesteps that entirely regardless of size."""
    pil_start, pil_end = start_deg - 90.0, end_deg - 90.0
    if pil_end <= pil_start:
        pil_end += 360.0
    mask = Image.new("L", base_img.size, 0)
    md = ImageDraw.Draw(mask)
    md.pieslice([cx - r_out, cy - r_out, cx + r_out, cy + r_out], pil_start, pil_end, fill=255)
    if r_in > 0:
        md.pieslice([cx - r_in, cy - r_in, cx + r_in, cy + r_in], pil_start, pil_end, fill=0)
    layer = Image.new("RGBA", base_img.size, (*color, alpha))
    base_img.paste(layer, (0, 0), mask)


def generate_dial_scale_image(
    knob_diameter: float = 150.0,
    min_angle: float = -135.0, max_angle: float = 135.0,
    min_value: float = 0.0, max_value: float = 10.0, scale_type: str = "Linear",
    num_major: int = 11, major_len: float = 14.0, major_width: int = 3, major_color: tuple = (164, 161, 237),
    num_sub: int = 1, sub_len: float = 7.0, sub_width: int = 1, sub_color: tuple = (120, 110, 180),
    tick_gap: float = 6.0,
    label_texts=None, label_font_size: int = 14, label_color: tuple = (37, 239, 203), label_gap: float = 8.0,
    show_track: bool = True, track_color: tuple = (51, 26, 118), track_width: float = 5.0, track_gap: float = 2.0,
    show_highlight: bool = False, highlight_start_value: float = None, highlight_end_value: float = None,
    highlight_color: tuple = (255, 60, 60),
    canvas_padding: float = 24.0,
):
    """Builds the tick/label ring as a standalone transparent-background PNG.
    Major ticks are always physically evenly spaced around the sweep (how
    real printed dial scales are made); for a Logarithmic scale, the VALUES
    labeled at those even positions progress by ratio rather than by
    difference — e.g. a frequency dial with evenly spaced 100/200/500/1k/2k
    ticks — while a Linear scale progresses evenly by difference."""
    num_major = max(2, int(num_major))
    sweep = max_angle - min_angle
    is_log = scale_type == "Logarithmic" and min_value > 0 and max_value > 0 and max_value != min_value

    def value_at_index(i: int) -> float:
        t = i / (num_major - 1) if num_major > 1 else 0.0
        if is_log:
            return min_value * ((max_value / min_value) ** t)
        return min_value + t * (max_value - min_value)

    if label_texts is None or len(label_texts) != num_major:
        label_texts = [format_dial_value(value_at_index(i), 1, "") for i in range(num_major)]

    def value_to_t(value: float) -> float:
        if is_log and value > 0:
            t = math.log(value / min_value) / math.log(max_value / min_value)
        else:
            t = (value - min_value) / (max_value - min_value) if max_value != min_value else 0.0
        return max(0.0, min(1.0, t))

    def value_to_angle(value: float) -> float:
        return min_angle + value_to_t(value) * sweep

    knob_radius = knob_diameter / 2.0
    font = _get_dial_font(max(6, int(label_font_size)))

    def measure(text: str):
        if not text:
            return 0, 0
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    max_lw = max_lh = 0
    for t in label_texts:
        w, h = measure(t)
        max_lw, max_lh = max(max_lw, w), max(max_lh, h)

    track_extent = (track_gap + track_width) if show_track else 0.0
    outer_radius = knob_radius + tick_gap + max(major_len, sub_len, track_extent) + label_gap
    canvas_half = outer_radius + max(max_lw, max_lh) / 2.0 + canvas_padding + 8
    size = int(math.ceil(canvas_half * 2))
    cx = cy = canvas_half

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def polar(radius: float, angle_deg: float):
        rad = math.radians(angle_deg)
        return cx + radius * math.sin(rad), cy - radius * math.cos(rad)

    if show_track:
        r_in = knob_radius + track_gap
        draw_arc_band(img, cx, cy, r_in, r_in + track_width, min_angle, max_angle, track_color)

    if show_highlight and highlight_start_value is not None and highlight_end_value is not None:
        a0 = value_to_angle(min(highlight_start_value, highlight_end_value))
        a1 = value_to_angle(max(highlight_start_value, highlight_end_value))
        r_in = knob_radius + track_gap
        band_w = track_width if show_track else major_len
        draw_arc_band(img, cx, cy, r_in, r_in + band_w, a0, a1, highlight_color)

    if num_sub > 0 and num_major > 1:
        for i in range(num_major - 1):
            a_start = min_angle + sweep * (i / (num_major - 1))
            a_end = min_angle + sweep * ((i + 1) / (num_major - 1))
            for s in range(1, num_sub + 1):
                t = s / (num_sub + 1)
                a = a_start + (a_end - a_start) * t
                p0 = polar(knob_radius + tick_gap, a)
                p1 = polar(knob_radius + tick_gap + sub_len, a)
                draw.line([p0, p1], fill=(*sub_color, 255), width=max(1, int(sub_width)))

    for i in range(num_major):
        t = i / (num_major - 1) if num_major > 1 else 0.0
        a = min_angle + sweep * t
        p0 = polar(knob_radius + tick_gap, a)
        p1 = polar(knob_radius + tick_gap + major_len, a)
        draw.line([p0, p1], fill=(*major_color, 255), width=max(1, int(major_width)))

        text = label_texts[i] if i < len(label_texts) else ""
        if text:
            lp = polar(knob_radius + tick_gap + major_len + label_gap, a)
            w, h = measure(text)
            draw.text((lp[0] - w / 2.0, lp[1] - h / 2.0), text, font=font, fill=(*label_color, 255))

    metrics = {"canvas_size": (size, size), "knob_diameter": knob_diameter, "outer_radius": outer_radius}
    return img, metrics


def compose_dial_preview(scale_img: Image.Image, knob_diameter: float, knob_ref_img):
    """Overlays a reference knob (the user's own art if loaded, else a plain
    placeholder disc with a pointer) into the transparent center of a
    rendered dial scale — for the live preview only; the real export leaves
    that center transparent unless explicitly asked to bake it in."""
    composed = scale_img.copy()
    cx = cy = composed.width / 2.0
    r = knob_diameter / 2.0
    if knob_ref_img is not None:
        kb = knob_ref_img.convert("RGBA").resize((max(1, int(knob_diameter)), max(1, int(knob_diameter))), Image.Resampling.LANCZOS)
        composed.paste(kb, (int(cx - r), int(cy - r)), kb)
    else:
        d = ImageDraw.Draw(composed)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(42, 26, 90, 255), outline=(37, 239, 203, 255), width=3)
        d.line([(cx, cy), (cx, cy - r * 0.75)], fill=(37, 239, 203, 255), width=4)
    return composed


# =============================================================================
# MAIN WORKBENCH WINDOW
# =============================================================================
class CaveSpriteWorkbench(QMainWindow):
    SIDEBAR_RATIO = 0.35  # the requested 35% left-hand control lane

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CavemanAI — CaveSprite UI Asset Workbench")
        self.resize(1440, 860)
        self.setStyleSheet(CAVEMAN_STYLESHEET)
        self.setAcceptDrops(True)
        self._init_ui()

    # -------------------------------------------------------------------
    # SHELL: persistent logo + control gutter (left) / tabbed canvas (right)
    # -------------------------------------------------------------------
    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # LEFT: 20% control gutter, logo pinned at top, controls swap per tab
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet(f"#Sidebar {{ background: #140b2c; border-right: 1px solid {COLOR_BORDER_INDIGO}; }}")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        if LOGO_PATH.exists():
            logo_pix = QPixmap(str(LOGO_PATH))
            logo_label.setPixmap(logo_pix.scaledToWidth(230, Qt.SmoothTransformation))
        else:
            logo_label.setText("CaveSprite")
            logo_label.setStyleSheet(f"color: {COLOR_CAVE_TEAL}; font-size: 20px; font-weight: bold;")
        sidebar_layout.addWidget(logo_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {COLOR_BORDER_INDIGO}; background: {COLOR_BORDER_INDIGO}; max-height: 1px;")
        sidebar_layout.addWidget(sep)

        self.control_stack = QStackedWidget()
        sidebar_layout.addWidget(self.control_stack, 1)

        root.addWidget(self.sidebar)

        # RIGHT: tab bar + canvas/preview workspace (controls live in the sidebar)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.tabs.currentChanged.connect(self.control_stack.setCurrentIndex)

        self._add_engine(*self._build_knob_engine())
        self._add_engine(*self._build_dial_scale_engine())
        self._add_engine(*self._build_led_engine())
        self._add_engine(*self._build_button_engine())
        self._add_engine(*self._build_switch_engine())
        self._add_engine(*self._build_tube_engine())
        self._add_engine(*self._build_vu_engine())

        self._resize_sidebar()

    def _add_engine(self, control_widget, view_widget, label):
        self.control_stack.addWidget(wrap_in_scroll(control_widget))
        self.tabs.addTab(view_widget, label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_sidebar()

    def _resize_sidebar(self):
        self.sidebar.setFixedWidth(max(240, int(self.width() * self.SIDEBAR_RATIO)))

    @staticmethod
    def _view_container(canvas_group_title: str, canvas_widget: QWidget, scrub_title: str):
        """Standard right-hand layout for every engine: a live parametric
        feel-test canvas on top, and the real-sprite scrub preview below."""
        view = QWidget()
        v_layout = QVBoxLayout(view)

        canvas_box = QGroupBox(canvas_group_title)
        cb_layout = QVBoxLayout(canvas_box)
        cb_layout.setAlignment(Qt.AlignCenter)
        cb_layout.addWidget(canvas_widget)
        v_layout.addWidget(canvas_box, 1)

        scrub = SpriteScrubPreview(scrub_title)
        v_layout.addWidget(scrub, 1)

        return view, scrub

    # -------------------------------------------------------------------
    # ENGINE 1: ROTATING KNOB  (WB1 single/batch export + angle range UX)
    # -------------------------------------------------------------------
    def _build_knob_engine(self):
        self.knob_input_path = ""
        self.knob_batch_folder = ""
        self.knob_last_sheet = None

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        g1 = QGroupBox("1. Knob Source")
        g1_l = QVBoxLayout(g1)
        btn_single = QPushButton("Select Single File")
        btn_batch = QPushButton("Select Batch Folder")
        self.lbl_knob_input = QLabel("No source selected")
        self.lbl_knob_input.setWordWrap(True)
        g1_l.addWidget(btn_single)
        g1_l.addWidget(btn_batch)
        g1_l.addWidget(self.lbl_knob_input)
        c_layout.addWidget(g1)

        g2 = QGroupBox("2. Rotation Sweep")
        g2_l = QFormLayout(g2)
        self.spin_knob_min = QSpinBox(); self.spin_knob_min.setRange(-360, 0); self.spin_knob_min.setValue(-135)
        self.spin_knob_max = QSpinBox(); self.spin_knob_max.setRange(0, 360); self.spin_knob_max.setValue(135)
        g2_l.addRow("Min Angle:", self.spin_knob_min)
        g2_l.addRow("Max Angle:", self.spin_knob_max)

        self.combo_knob_style = QComboBox()
        self.combo_knob_style.addItems([
            "Continuous Sweep", "3-Position Step Knob", "4-Position Step Knob",
            "5-Position Step Knob", "6-Position Step Knob", "7-Position Step Knob",
        ])
        self.combo_knob_style.setToolTip(
            "Continuous Sweep uses the Frame Count below for a smooth rotation.\n"
            "A Step Knob instead produces exactly one frame per detent position, "
            "evenly spaced from Min Angle to Max Angle — for selector-style knobs."
        )
        g2_l.addRow("Sprite Style:", self.combo_knob_style)

        self.spin_knob_frames = QSpinBox(); self.spin_knob_frames.setRange(2, 360); self.spin_knob_frames.setValue(31)
        g2_l.addRow("Frame Count:", self.spin_knob_frames)
        self.chk_knob_source_at_min = QCheckBox("Source Indicator Already Drawn at Min Angle")
        self.chk_knob_source_at_min.setChecked(True)
        self.chk_knob_source_at_min.setToolTip(
            "On: your source PNG's indicator is already positioned at Min Angle "
            "(e.g. baked in at -135\u00b0) — frame 0 will be an exact copy of the "
            "source and it rotates forward from there.\n"
            "Off: your source PNG's indicator points North (0\u00b0) at rest, and "
            "every frame is rotated to its absolute angle."
        )
        g2_l.addRow(self.chk_knob_source_at_min)
        c_layout.addWidget(g2)

        g3 = QGroupBox("3. Interactive Feel Test")
        g3_l = QVBoxLayout(g3)
        g3_l.addWidget(QLabel("Rotation Angle Test:"))
        sld_test = QSlider(Qt.Horizontal); sld_test.setRange(0, 100); sld_test.setValue(50)
        g3_l.addWidget(sld_test)
        c_layout.addWidget(g3)

        btn_render = QPushButton("Render Knob Filmstrip")
        btn_export = QPushButton("Export Sprite Sheet (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_render)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        canvas = KnobCanvas()
        view, scrub = self._view_container("Live Interactive Knob Canvas", canvas, "Knob Filmstrip Range Preview")

        def sync_canvas():
            canvas.min_a = float(self.spin_knob_min.value())
            canvas.max_a = float(self.spin_knob_max.value())
            canvas.update()

        def effective_frame_count() -> int:
            idx = self.combo_knob_style.currentIndex()
            return self.spin_knob_frames.value() if idx == 0 else idx + 2

        def sync_style_mode():
            is_stepped = self.combo_knob_style.currentIndex() > 0
            self.spin_knob_frames.setEnabled(not is_stepped)
            if is_stepped:
                self.spin_knob_frames.blockSignals(True)
                self.spin_knob_frames.setValue(effective_frame_count())
                self.spin_knob_frames.blockSignals(False)

        def select_single():
            path, _ = QFileDialog.getOpenFileName(self, "Select Starting Knob Image", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                self.knob_input_path = path
                self.knob_batch_folder = ""
                self.lbl_knob_input.setText(f"File: {Path(path).name}")

        def select_batch():
            folder = QFileDialog.getExistingDirectory(self, "Select Folder of Knobs")
            if folder:
                self.knob_batch_folder = folder
                self.knob_input_path = ""
                self.lbl_knob_input.setText(f"Folder: {Path(folder).name}")

        def render():
            if not self.knob_input_path and not self.knob_batch_folder:
                QMessageBox.information(self, "No Source", "Select a single knob image or a batch folder first.")
                return
            sample_path = self.knob_input_path
            if not sample_path and self.knob_batch_folder:
                valid = {'.png', '.jpg', '.jpeg'}
                found = [f for f in Path(self.knob_batch_folder).iterdir() if f.suffix.lower() in valid]
                if not found:
                    QMessageBox.warning(self, "Empty Folder", "No images found in that folder.")
                    return
                sample_path = str(found[0])

            try:
                source = Image.open(sample_path)
                frame_count = effective_frame_count()
                self.knob_last_sheet = render_knob_filmstrip(
                    source, frame_count,
                    self.spin_knob_min.value(), self.spin_knob_max.value(),
                    source_at_min_angle=self.chk_knob_source_at_min.isChecked()
                )
                w, h = source.size
                scrub.set_sheet(self.knob_last_sheet, w, h, frame_count)
                btn_export.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Render Error", str(e))

        def export():
            frames = effective_frame_count()
            try:
                if self.knob_batch_folder:
                    folder = Path(self.knob_batch_folder)
                    export_dir = folder / "sprite_exports"
                    export_dir.mkdir(exist_ok=True)
                    valid = {'.png', '.jpg', '.jpeg'}
                    images = [f for f in folder.iterdir() if f.suffix.lower() in valid]
                    for img_path in images:
                        sheet = render_knob_filmstrip(
                            Image.open(img_path), frames,
                            self.spin_knob_min.value(), self.spin_knob_max.value(),
                            source_at_min_angle=self.chk_knob_source_at_min.isChecked()
                        )
                        sheet.save(export_dir / f"{img_path.stem}_sprite.png", "PNG")
                    QMessageBox.information(self, "Batch Complete", f"Processed {len(images)} file(s) into {export_dir}")
                elif self.knob_input_path and self.knob_last_sheet:
                    save_name, _ = QFileDialog.getSaveFileName(self, "Save Knob Sprite Sheet", "cavesprite_knob.png", "PNG Image (*.png)")
                    if save_name:
                        self.knob_last_sheet.save(save_name, "PNG")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

        btn_single.clicked.connect(select_single)
        btn_batch.clicked.connect(select_batch)
        btn_render.clicked.connect(render)
        btn_export.clicked.connect(export)
        sld_test.valueChanged.connect(lambda v: (setattr(canvas, 'val', v / 100.0), canvas.update()))
        self.spin_knob_min.valueChanged.connect(sync_canvas)
        self.spin_knob_max.valueChanged.connect(sync_canvas)
        self.combo_knob_style.currentIndexChanged.connect(sync_style_mode)
        sync_style_mode()

        return ctrl, view, "Knob Engine"

    # -------------------------------------------------------------------
    # ENGINE (NEW): DIAL SCALE DESIGNER
    # -----------------------------------------------------------------------
    # Builds the printed tick/label ring that surrounds a knob — width,
    # count, and spacing of major/sub ticks, per-tick label text, an
    # optional background track, and an optional highlight zone. The live
    # preview composites your actual knob art (if loaded) in real time as
    # you adjust anything; the export always leaves the center transparent
    # unless you explicitly ask to bake the reference knob in.
    # -------------------------------------------------------------------
    def _build_dial_scale_engine(self):
        self.dial_knob_ref_image = None      # PIL Image or None — preview/optional-export only
        self.dial_export_image = None
        self.dial_colors = {
            "major": [164, 161, 237],
            "sub": [120, 110, 180],
            "label": [37, 239, 203],
            "track": [51, 26, 118],
            "highlight": [255, 60, 60],
        }
        self.dial_label_edits = []

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        # 1. Reference Knob (preview only)
        g1 = QGroupBox("1. Reference Knob (Preview Only)")
        g1_l = QVBoxLayout(g1)
        btn_load_knob_ref = QPushButton("Load Reference Knob Image (Optional)")
        lbl_knob_ref = QLabel("No reference image — showing a placeholder disc")
        lbl_knob_ref.setWordWrap(True)
        g1_l.addWidget(btn_load_knob_ref)
        g1_l.addWidget(lbl_knob_ref)
        form1 = QFormLayout()
        spin_knob_diam = QSpinBox(); spin_knob_diam.setRange(20, 2000); spin_knob_diam.setValue(150)
        spin_knob_diam.setToolTip("The pixel diameter of the knob this scale will surround — used to size the tick ring correctly.")
        form1.addRow("Knob Diameter (px):", spin_knob_diam)
        g1_l.addLayout(form1)
        chk_bake_knob = QCheckBox("Include Reference Knob Graphic in Export")
        chk_bake_knob.setToolTip("Off by default: the exported PNG's center stays transparent so it can sit behind a separately animated knob sprite.")
        g1_l.addWidget(chk_bake_knob)
        c_layout.addWidget(g1)

        # 2. Sweep & Value Range
        g2 = QGroupBox("2. Sweep & Value Range")
        g2_l = QFormLayout(g2)
        spin_dial_min_angle = QSpinBox(); spin_dial_min_angle.setRange(-360, 0); spin_dial_min_angle.setValue(-135)
        spin_dial_max_angle = QSpinBox(); spin_dial_max_angle.setRange(0, 360); spin_dial_max_angle.setValue(135)
        spin_min_value = QDoubleSpinBox(); spin_min_value.setRange(-999999, 999999); spin_min_value.setDecimals(3); spin_min_value.setValue(0.0)
        spin_max_value = QDoubleSpinBox(); spin_max_value.setRange(-999999, 999999); spin_max_value.setDecimals(3); spin_max_value.setValue(10.0)
        combo_scale_type = QComboBox(); combo_scale_type.addItems(["Linear", "Logarithmic"])
        combo_scale_type.setToolTip(
            "Logarithmic keeps ticks physically evenly spaced (like real printed "
            "gear) but labels them with ratio-progressing values — e.g. a "
            "frequency dial's 100/200/500/1k/2k. Requires Min Value > 0."
        )
        g2_l.addRow("Min Angle:", spin_dial_min_angle)
        g2_l.addRow("Max Angle:", spin_dial_max_angle)
        g2_l.addRow("Min Value:", spin_min_value)
        g2_l.addRow("Max Value:", spin_max_value)
        g2_l.addRow("Value Scale:", combo_scale_type)
        c_layout.addWidget(g2)

        # 3. Major Ticks
        g3 = QGroupBox("3. Major Ticks")
        g3_l = QFormLayout(g3)
        spin_num_major = QSpinBox(); spin_num_major.setRange(2, 21); spin_num_major.setValue(11)
        spin_major_len = QSpinBox(); spin_major_len.setRange(1, 120); spin_major_len.setValue(14)
        spin_major_width = QSpinBox(); spin_major_width.setRange(1, 20); spin_major_width.setValue(3)
        btn_major_color = QPushButton("Major Tick Color")
        spin_tick_gap = QSpinBox(); spin_tick_gap.setRange(0, 100); spin_tick_gap.setValue(6)
        g3_l.addRow("Number of Major Ticks:", spin_num_major)
        g3_l.addRow("Tick Length (px):", spin_major_len)
        g3_l.addRow("Tick Width (px):", spin_major_width)
        g3_l.addRow(btn_major_color)
        g3_l.addRow("Gap from Knob Edge (px):", spin_tick_gap)
        c_layout.addWidget(g3)

        # 4. Major Tick Labels
        g4 = QGroupBox("4. Major Tick Labels")
        g4_l = QVBoxLayout(g4)
        form4 = QFormLayout()
        spin_decimals = QSpinBox(); spin_decimals.setRange(0, 3); spin_decimals.setValue(0)
        edit_suffix = QLineEdit("")
        edit_suffix.setPlaceholderText("e.g. dB, Hz, %")
        spin_label_font = QSpinBox(); spin_label_font.setRange(6, 48); spin_label_font.setValue(14)
        btn_label_color = QPushButton("Label Color")
        spin_label_gap = QSpinBox(); spin_label_gap.setRange(0, 100); spin_label_gap.setValue(8)
        form4.addRow("Decimal Places:", spin_decimals)
        form4.addRow("Label Suffix:", edit_suffix)
        form4.addRow("Font Size (px):", spin_label_font)
        form4.addRow(btn_label_color)
        form4.addRow("Label Gap (px):", spin_label_gap)
        g4_l.addLayout(form4)
        btn_autofill = QPushButton("Auto-Fill Labels From Range")
        g4_l.addWidget(btn_autofill)
        g4_l.addWidget(QLabel("Per-Tick Label Text (edit any to override):"))
        label_list_container = QWidget()
        label_list_layout = QVBoxLayout(label_list_container)
        label_list_layout.setContentsMargins(0, 0, 0, 0)
        g4_l.addWidget(label_list_container)
        c_layout.addWidget(g4)

        # 5. Sub-Ticks
        g5 = QGroupBox("5. Sub-Ticks")
        g5_l = QFormLayout(g5)
        spin_num_sub = QSpinBox(); spin_num_sub.setRange(0, 10); spin_num_sub.setValue(1)
        spin_sub_len = QSpinBox(); spin_sub_len.setRange(1, 80); spin_sub_len.setValue(7)
        spin_sub_width = QSpinBox(); spin_sub_width.setRange(1, 10); spin_sub_width.setValue(1)
        btn_sub_color = QPushButton("Sub-Tick Color")
        g5_l.addRow("Sub-Ticks Between Majors:", spin_num_sub)
        g5_l.addRow("Sub-Tick Length (px):", spin_sub_len)
        g5_l.addRow("Sub-Tick Width (px):", spin_sub_width)
        g5_l.addRow(btn_sub_color)
        c_layout.addWidget(g5)

        # 6. Arc Track & Highlight Zone
        g6 = QGroupBox("6. Arc Track & Highlight Zone")
        g6_l = QVBoxLayout(g6)
        chk_show_track = QCheckBox("Show Background Track"); chk_show_track.setChecked(True)
        g6_l.addWidget(chk_show_track)
        form6 = QFormLayout()
        btn_track_color = QPushButton("Track Color")
        spin_track_width = QSpinBox(); spin_track_width.setRange(1, 60); spin_track_width.setValue(5)
        spin_track_gap = QSpinBox(); spin_track_gap.setRange(0, 80); spin_track_gap.setValue(2)
        form6.addRow(btn_track_color)
        form6.addRow("Track Width (px):", spin_track_width)
        form6.addRow("Track Gap from Knob Edge (px):", spin_track_gap)
        g6_l.addLayout(form6)
        chk_show_highlight = QCheckBox("Show Highlight Zone")
        g6_l.addWidget(chk_show_highlight)
        form6b = QFormLayout()
        spin_hl_start = QDoubleSpinBox(); spin_hl_start.setRange(-999999, 999999); spin_hl_start.setDecimals(3); spin_hl_start.setValue(8.0)
        spin_hl_end = QDoubleSpinBox(); spin_hl_end.setRange(-999999, 999999); spin_hl_end.setDecimals(3); spin_hl_end.setValue(10.0)
        btn_hl_color = QPushButton("Highlight Color")
        form6b.addRow("Start Value:", spin_hl_start)
        form6b.addRow("End Value:", spin_hl_end)
        form6b.addRow(btn_hl_color)
        g6_l.addLayout(form6b)
        c_layout.addWidget(g6)

        # 7. Canvas
        g7 = QGroupBox("7. Canvas")
        g7_l = QFormLayout(g7)
        spin_padding = QSpinBox(); spin_padding.setRange(0, 300); spin_padding.setValue(24)
        g7_l.addRow("Canvas Padding (px):", spin_padding)
        c_layout.addWidget(g7)

        btn_render = QPushButton("Render Dial Scale")
        btn_export = QPushButton("Export Scale Image (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_render)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        # ---- Workspace: real-time composite preview + export-ready scrub ----
        view = QWidget()
        v_layout = QVBoxLayout(view)

        live_box = QGroupBox("Live Dial Scale Preview (with reference knob)")
        live_box_l = QVBoxLayout(live_box)
        live_preview_label = QLabel("Adjust any setting to preview in real time.")
        live_preview_label.setAlignment(Qt.AlignCenter)
        live_preview_label.setMinimumHeight(260)
        live_preview_label.setStyleSheet(SCRUB_PREVIEW_STYLE)
        live_preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        live_box_l.addWidget(live_preview_label)
        v_layout.addWidget(live_box, 1)

        scrub = SpriteScrubPreview("Exported Scale Image Preview")
        v_layout.addWidget(scrub, 1)

        # ---- Helpers -----------------------------------------------------
        def make_color_picker(btn: QPushButton, key: str, dialog_title: str):
            def update_style():
                r, g, b = self.dial_colors[key]
                btn.setStyleSheet(f"background-color: rgb({r},{g},{b});")
            def pick():
                c = QColorDialog.getColor(QColor(*self.dial_colors[key]), self, dialog_title)
                if c.isValid():
                    self.dial_colors[key] = [c.red(), c.green(), c.blue()]
                    update_style()
                    update_live_preview()
            btn.clicked.connect(pick)
            update_style()

        def value_at_index(i: int, n: int) -> float:
            t = i / (n - 1) if n > 1 else 0.0
            if combo_scale_type.currentText() == "Logarithmic" and spin_min_value.value() > 0 and spin_max_value.value() > 0:
                return spin_min_value.value() * ((spin_max_value.value() / spin_min_value.value()) ** t)
            return spin_min_value.value() + t * (spin_max_value.value() - spin_min_value.value())

        def rebuild_label_edits(preserve_values: bool = True):
            old_texts = [e.text() for e in self.dial_label_edits]
            while label_list_layout.count():
                item = label_list_layout.takeAt(0)
                w_ = item.widget()
                if w_:
                    w_.deleteLater()
            self.dial_label_edits = []
            n = spin_num_major.value()
            for i in range(n):
                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(0, 0, 0, 0)
                tag = QLabel(f"Tick {i + 1}:")
                tag.setFixedWidth(50)
                edit = QLineEdit()
                if preserve_values and i < len(old_texts):
                    edit.setText(old_texts[i])
                else:
                    edit.setText(format_dial_value(value_at_index(i, n), spin_decimals.value(), edit_suffix.text()))
                edit.textChanged.connect(update_live_preview)
                row.addWidget(tag)
                row.addWidget(edit)
                label_list_layout.addWidget(row_widget)
                self.dial_label_edits.append(edit)

        def autofill_labels():
            n = spin_num_major.value()
            for i, edit in enumerate(self.dial_label_edits):
                edit.blockSignals(True)
                edit.setText(format_dial_value(value_at_index(i, n), spin_decimals.value(), edit_suffix.text()))
                edit.blockSignals(False)
            update_live_preview()

        def gather_params():
            n = spin_num_major.value()
            labels = [e.text() for e in self.dial_label_edits]
            if len(labels) != n:
                labels = [format_dial_value(value_at_index(i, n), spin_decimals.value(), edit_suffix.text()) for i in range(n)]
            return dict(
                knob_diameter=float(spin_knob_diam.value()),
                min_angle=float(spin_dial_min_angle.value()), max_angle=float(spin_dial_max_angle.value()),
                min_value=spin_min_value.value(), max_value=spin_max_value.value(),
                scale_type=combo_scale_type.currentText(),
                num_major=n, major_len=float(spin_major_len.value()), major_width=spin_major_width.value(),
                major_color=tuple(self.dial_colors["major"]),
                num_sub=spin_num_sub.value(), sub_len=float(spin_sub_len.value()), sub_width=spin_sub_width.value(),
                sub_color=tuple(self.dial_colors["sub"]),
                tick_gap=float(spin_tick_gap.value()),
                label_texts=labels, label_font_size=spin_label_font.value(),
                label_color=tuple(self.dial_colors["label"]), label_gap=float(spin_label_gap.value()),
                show_track=chk_show_track.isChecked(), track_color=tuple(self.dial_colors["track"]),
                track_width=float(spin_track_width.value()), track_gap=float(spin_track_gap.value()),
                show_highlight=chk_show_highlight.isChecked(),
                highlight_start_value=spin_hl_start.value(), highlight_end_value=spin_hl_end.value(),
                highlight_color=tuple(self.dial_colors["highlight"]),
                canvas_padding=float(spin_padding.value()),
            )

        def update_live_preview():
            try:
                params = gather_params()
                img, _ = generate_dial_scale_image(**params)
            except Exception:
                return
            composed = compose_dial_preview(img, params["knob_diameter"], self.dial_knob_ref_image)
            pix = pillow_to_qpixmap(composed)
            target_w = max(80, live_box.width() - 24)
            target_h = max(80, live_preview_label.minimumHeight())
            scaled = pix.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            live_preview_label.setPixmap(scaled)

        def load_knob_ref():
            path, _ = QFileDialog.getOpenFileName(self, "Select Reference Knob Image", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                try:
                    self.dial_knob_ref_image = Image.open(path)
                    lbl_knob_ref.setText(Path(path).name)
                    update_live_preview()
                except Exception as e:
                    lbl_knob_ref.setText(f"Error loading image: {e}")

        def render():
            if combo_scale_type.currentText() == "Logarithmic" and spin_min_value.value() <= 0:
                QMessageBox.warning(
                    self, "Invalid Range for Log Scale",
                    "Logarithmic scale requires Min Value greater than 0. Rendering as Linear instead."
                )
            params = gather_params()
            img, metrics = generate_dial_scale_image(**params)
            export_img = compose_dial_preview(img, params["knob_diameter"], self.dial_knob_ref_image) if chk_bake_knob.isChecked() else img
            self.dial_export_image = export_img
            w, h = export_img.size
            scrub.set_sheet(export_img, w, h, 1)
            btn_export.setEnabled(True)

        def export():
            if not self.dial_export_image:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save Dial Scale Image", "cavesprite_dial_scale.png", "PNG Files (*.png)")
            if path:
                self.dial_export_image.save(path, "PNG")

        # ---- Wiring --------------------------------------------------------
        make_color_picker(btn_major_color, "major", "Major Tick Color")
        make_color_picker(btn_sub_color, "sub", "Sub-Tick Color")
        make_color_picker(btn_label_color, "label", "Label Color")
        make_color_picker(btn_track_color, "track", "Track Color")
        make_color_picker(btn_hl_color, "highlight", "Highlight Color")

        btn_load_knob_ref.clicked.connect(load_knob_ref)
        btn_autofill.clicked.connect(autofill_labels)
        btn_render.clicked.connect(render)
        btn_export.clicked.connect(export)

        spin_num_major.valueChanged.connect(lambda _: (rebuild_label_edits(True), update_live_preview()))
        for w_ in (spin_knob_diam, spin_dial_min_angle, spin_dial_max_angle, spin_min_value, spin_max_value,
                   spin_major_len, spin_major_width, spin_tick_gap, spin_decimals, spin_label_font, spin_label_gap,
                   spin_num_sub, spin_sub_len, spin_sub_width, spin_track_width, spin_track_gap,
                   spin_hl_start, spin_hl_end, spin_padding):
            w_.valueChanged.connect(update_live_preview)
        combo_scale_type.currentIndexChanged.connect(update_live_preview)
        edit_suffix.textChanged.connect(update_live_preview)
        chk_show_track.toggled.connect(update_live_preview)
        chk_show_highlight.toggled.connect(update_live_preview)
        chk_bake_knob.toggled.connect(update_live_preview)

        rebuild_label_edits(preserve_values=False)
        update_live_preview()

        return ctrl, view, "Dial Scale Designer"

    # -------------------------------------------------------------------
    # ENGINE 2: LED LEVEL METER  (rebuilt to actually blend as a meter)
    # -------------------------------------------------------------------
    def _build_led_engine(self):
        self.led_start_color = (37, 239, 203)
        self.led_end_color = (255, 50, 50)
        self.led_last_sheet = None

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        g1 = QGroupBox("1. Array Configuration")
        g1_l = QFormLayout(g1)
        combo_shape = QComboBox(); combo_shape.addItems(["Rectangle", "Circle", "Triangle"])
        spin_count = QSpinBox(); spin_count.setRange(2, 32); spin_count.setValue(10)
        combo_orient = QComboBox(); combo_orient.addItems(["Vertical", "Horizontal", "Arc (Half-Circle)"])
        combo_orient.setToolTip(
            "Arc (Half-Circle) fans the LEDs across a 180\u00b0 dome from a "
            "bottom-center pivot — index 0 at the left horizon sweeping up "
            "and over to the last LED at the right horizon."
        )
        spin_w = QSpinBox(); spin_w.setRange(2, 256); spin_w.setValue(16)
        spin_h = QSpinBox(); spin_h.setRange(2, 256); spin_h.setValue(10)
        spin_spacing = QSpinBox(); spin_spacing.setRange(0, 32); spin_spacing.setValue(3)
        chk_bevel = QCheckBox("Inner Bevel"); chk_bevel.setChecked(True)
        chk_glow = QCheckBox("Soft Glow on Lit Segments"); chk_glow.setChecked(True)
        g1_l.addRow("LED Shape:", combo_shape)
        g1_l.addRow("LED Count:", spin_count)
        g1_l.addRow("Orientation:", combo_orient)
        g1_l.addRow("LED Width (px):", spin_w)
        g1_l.addRow("LED Height (px):", spin_h)
        g1_l.addRow("Spacing (px):", spin_spacing)
        g1_l.addRow(chk_bevel)
        g1_l.addRow(chk_glow)
        c_layout.addWidget(g1)

        g2 = QGroupBox("2. Color Gradient Preset")
        g2_l = QVBoxLayout(g2)
        combo_preset = QComboBox()
        combo_preset.addItems([
            "Classic VU (Green-Yellow-Red)", "Caveman (Teal-Purple)",
            "Neon Blue-Magenta", "Amber Mono", "Custom Gradient"
        ])
        g2_l.addWidget(combo_preset)
        color_row = QHBoxLayout()
        btn_start = QPushButton("Start Color"); btn_start.setEnabled(False)
        btn_end = QPushButton("End Color"); btn_end.setEnabled(False)
        color_row.addWidget(btn_start); color_row.addWidget(btn_end)
        g2_l.addLayout(color_row)
        c_layout.addWidget(g2)

        g3 = QGroupBox("3. Interactive Level Test")
        g3_l = QVBoxLayout(g3)
        g3_l.addWidget(QLabel("Test Signal Level:"))
        sld_level = QSlider(Qt.Horizontal); sld_level.setRange(0, 100); sld_level.setValue(50)
        g3_l.addWidget(sld_level)
        c_layout.addWidget(g3)

        btn_render = QPushButton("Render LED Meter Filmstrip")
        btn_export = QPushButton("Export Sprite Sheet (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_render)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        canvas = LEDMeterCanvas()
        view, scrub = self._view_container("Live Level-Meter Feel Test", canvas, "LED Meter Filmstrip Range Preview")

        def on_preset_changed(text):
            is_custom = (text == "Custom Gradient")
            btn_start.setEnabled(is_custom)
            btn_end.setEnabled(is_custom)

        def pick_start():
            c = QColorDialog.getColor(QColor(*self.led_start_color), self)
            if c.isValid():
                self.led_start_color = (c.red(), c.green(), c.blue())

        def pick_end():
            c = QColorDialog.getColor(QColor(*self.led_end_color), self)
            if c.isValid():
                self.led_end_color = (c.red(), c.green(), c.blue())

        def render():
            sheet, metrics = generate_led_meter_filmstrip(
                num_leds=spin_count.value(), led_width=spin_w.value(), led_height=spin_h.value(),
                spacing=spin_spacing.value(), orientation=combo_orient.currentText(),
                shape=combo_shape.currentText(), preset=combo_preset.currentText(),
                start_color=self.led_start_color, end_color=self.led_end_color,
                bevel=chk_bevel.isChecked(), glow=chk_glow.isChecked()
            )
            self.led_last_sheet = sheet
            fw, fh = metrics["footprint"]
            scrub.set_sheet(sheet, fw, fh, metrics["total_frames"])
            canvas.segments = spin_count.value()
            canvas.update()
            btn_export.setEnabled(True)

        def export():
            if not self.led_last_sheet:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save LED Meter Sprite Sheet", "cavesprite_led_meter.png", "PNG Files (*.png)")
            if path:
                self.led_last_sheet.save(path, "PNG")

        combo_preset.currentTextChanged.connect(on_preset_changed)
        btn_start.clicked.connect(pick_start)
        btn_end.clicked.connect(pick_end)
        sld_level.valueChanged.connect(lambda v: (setattr(canvas, 'level', v / 100.0), canvas.update()))
        spin_count.valueChanged.connect(lambda v: (setattr(canvas, 'segments', v), canvas.update()))
        btn_render.clicked.connect(render)
        btn_export.clicked.connect(export)

        return ctrl, view, "LED Meter Engine"

    # -------------------------------------------------------------------
    # ENGINE 3: BUTTON LATCHING  (CaveSpriteWB1, unchanged logic)
    # -------------------------------------------------------------------
    def _build_button_engine(self):
        self.button_pil_image = self._default_button_image()
        self.button_led_color = (37, 239, 203)
        self.button_last_sheet = None

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        g1 = QGroupBox("1. Cap Graphic")
        g1_l = QVBoxLayout(g1)
        btn_load = QPushButton("Select Cap Image...")
        self.lbl_button_file = QLabel("Default CavemanAI cap loaded.")
        self.lbl_button_file.setWordWrap(True)
        g1_l.addWidget(btn_load)
        g1_l.addWidget(self.lbl_button_file)
        c_layout.addWidget(g1)

        g2 = QGroupBox("2. Visual Overlays")
        g2_l = QVBoxLayout(g2)
        chk_bevel = QCheckBox("Overlay Metallic Bevel"); chk_bevel.setChecked(True)
        chk_led = QCheckBox("Overlay Center LED Indicator"); chk_led.setChecked(True)
        color_row = QHBoxLayout()
        btn_color = QPushButton("LED Color")
        lbl_swatch = QLabel(); lbl_swatch.setFixedSize(20, 20)
        color_row.addWidget(btn_color); color_row.addWidget(lbl_swatch); color_row.addStretch()
        g2_l.addWidget(chk_bevel)
        g2_l.addWidget(chk_led)
        g2_l.addLayout(color_row)
        c_layout.addWidget(g2)

        g3 = QGroupBox("3. Motion Parameters")
        g3_l = QFormLayout(g3)
        spin_size = QSpinBox(); spin_size.setRange(32, 512); spin_size.setSingleStep(16); spin_size.setValue(128)
        spin_frames = QSpinBox(); spin_frames.setRange(4, 64); spin_frames.setValue(12)
        spin_travel = QSpinBox(); spin_travel.setRange(1, 32); spin_travel.setValue(8)
        spin_shadow = QSpinBox(); spin_shadow.setRange(0, 255); spin_shadow.setValue(140)
        g3_l.addRow("Frame Size (px):", spin_size)
        g3_l.addRow("Total Frames:", spin_frames)
        g3_l.addRow("Press Travel (px):", spin_travel)
        g3_l.addRow("Shadow Alpha:", spin_shadow)
        c_layout.addWidget(g3)

        btn_export = QPushButton("Export Button Sprite Sheet (.png)")
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        def update_swatch():
            r, g, b = self.button_led_color
            lbl_swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid {COLOR_BORDER_INDIGO}; border-radius: 3px;")
        update_swatch()

        # Right side: click-to-latch feel test (WB1) + universal scrub preview
        view = QWidget()
        v_layout = QVBoxLayout(view)
        feel_box = QGroupBox("Interactive Feeling Test (Click Button)")
        fb_layout = QVBoxLayout(feel_box)
        fb_layout.setAlignment(Qt.AlignCenter)
        feel_preview = InteractiveButtonPreview()
        fb_layout.addWidget(feel_preview)
        hint = QLabel("Click the button to test the latching press feel.")
        hint.setAlignment(Qt.AlignCenter)
        fb_layout.addWidget(hint)
        v_layout.addWidget(feel_box, 1)

        scrub = SpriteScrubPreview("Button Filmstrip Range Preview")
        v_layout.addWidget(scrub, 1)

        def rebuild():
            self.button_last_sheet = generate_latching_spritesheet_from_image(
                source_img=self.button_pil_image,
                frame_size=spin_size.value(), total_frames=spin_frames.value(),
                max_travel=spin_travel.value(), shadow_intensity=spin_shadow.value(),
                enable_bevel=chk_bevel.isChecked(), enable_led=chk_led.isChecked(),
                led_color=self.button_led_color
            )
            feel_preview.update_spritesheet(self.button_last_sheet, spin_size.value(), spin_frames.value())
            scrub.set_sheet(self.button_last_sheet, spin_size.value(), spin_size.value(), spin_frames.value())

        def load_cap():
            path, _ = QFileDialog.getOpenFileName(self, "Select Cap Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
            if path:
                try:
                    self.button_pil_image = Image.open(path)
                    self.lbl_button_file.setText(Path(path).name)
                    rebuild()
                except Exception as e:
                    self.lbl_button_file.setText(f"Error loading image: {e}")

        def pick_color():
            c = QColorDialog.getColor(QColor(*self.button_led_color), self, "Select LED Glow Color")
            if c.isValid():
                self.button_led_color = (c.red(), c.green(), c.blue())
                update_swatch()
                rebuild()

        def export():
            if not self.button_last_sheet:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save Button Sprite Sheet", "cavesprite_button_sheet.png", "PNG Files (*.png)")
            if path:
                self.button_last_sheet.save(path, "PNG")

        btn_load.clicked.connect(load_cap)
        btn_color.clicked.connect(pick_color)
        chk_bevel.stateChanged.connect(rebuild)
        chk_led.stateChanged.connect(rebuild)
        spin_size.valueChanged.connect(rebuild)
        spin_frames.valueChanged.connect(rebuild)
        spin_travel.valueChanged.connect(rebuild)
        spin_shadow.valueChanged.connect(rebuild)
        btn_export.clicked.connect(export)

        rebuild()
        return ctrl, view, "Button Latching Engine"

    @staticmethod
    def _default_button_image() -> Image.Image:
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 120, 120], fill=(51, 26, 118), outline=(37, 239, 203), width=4)
        draw.ellipse([44, 44, 84, 84], fill=(22, 13, 50))
        return img

    # -------------------------------------------------------------------
    # ENGINE 4: SWITCH & TOGGLE BUILDER  (CaveSpriteWB3, unchanged logic)
    # -------------------------------------------------------------------
    def _build_switch_engine(self):
        self.switch_img_off = None
        self.switch_img_on = None
        self.switch_img_sprite = None
        self.switch_last_pixmap = None
        self.switch_frame_size = (0, 0)

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        mode_box = QGroupBox("Generation Mode")
        mode_l = QVBoxLayout(mode_box)
        combo_mode = QComboBox()
        combo_mode.addItems(["Dual Source (Up/Down Images -> Filmstrip)", "Sprite Slice & Rotate (Left/Right -> Up/Down)"])
        mode_l.addWidget(combo_mode)
        c_layout.addWidget(mode_box)

        dual_box = QGroupBox("Dual Image Inputs")
        dual_l = QVBoxLayout(dual_box)
        btn_off = QPushButton("Load State 0 (Off / Down / Left)")
        lbl_off = QLabel("No image loaded")
        btn_on = QPushButton("Load State 1 (On / Up / Right)")
        lbl_on = QLabel("No image loaded")
        dual_l.addWidget(btn_off); dual_l.addWidget(lbl_off)
        dual_l.addWidget(btn_on); dual_l.addWidget(lbl_on)
        c_layout.addWidget(dual_box)

        sprite_box = QGroupBox("Sprite Sheet Input")
        sprite_l = QVBoxLayout(sprite_box)
        btn_sprite = QPushButton("Load Existing Filmstrip")
        lbl_sprite = QLabel("No sprite loaded")
        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Frame Count:"))
        spin_sprite_frames = QSpinBox(); spin_sprite_frames.setRange(2, 64); spin_sprite_frames.setValue(2)
        frame_row.addWidget(spin_sprite_frames)
        sprite_l.addWidget(btn_sprite); sprite_l.addWidget(lbl_sprite); sprite_l.addLayout(frame_row)
        c_layout.addWidget(sprite_box)

        opts_box = QGroupBox("Processing Options")
        opts_l = QVBoxLayout(opts_box)
        combo_rotation = QComboBox()
        combo_rotation.addItems(["No Rotation", "Rotate 90° CW", "Rotate 90° CCW", "Rotate 180°"])
        opts_l.addWidget(QLabel("Rotation Filter:"))
        opts_l.addWidget(combo_rotation)
        c_layout.addWidget(opts_box)

        g_test = QGroupBox("Interactive Test")
        g_test_l = QVBoxLayout(g_test)
        g_test_l.addWidget(QLabel("Lever Position Sweep:"))
        sld_pos = QSlider(Qt.Horizontal); sld_pos.setRange(-100, 100); sld_pos.setValue(0)
        g_test_l.addWidget(sld_pos)
        c_layout.addWidget(g_test)

        btn_process = QPushButton("Generate Switch Filmstrip")
        btn_export = QPushButton("Export Sprite File (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_process)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        def toggle_mode_ui():
            is_dual = combo_mode.currentIndex() == 0
            dual_box.setVisible(is_dual)
            sprite_box.setVisible(not is_dual)
        combo_mode.currentIndexChanged.connect(toggle_mode_ui)
        toggle_mode_ui()

        canvas = SwitchCanvas()
        view, scrub = self._view_container("Live Interactive Toggle Canvas", canvas, "Switch Filmstrip Range Preview")

        def load_image(target):
            path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if not path:
                return
            pix = QPixmap(path)
            if target == 'off':
                self.switch_img_off = pix; lbl_off.setText(Path(path).name)
            elif target == 'on':
                self.switch_img_on = pix; lbl_on.setText(Path(path).name)
            else:
                self.switch_img_sprite = pix; lbl_sprite.setText(Path(path).name)

        def apply_rotation(pixmap):
            idx = combo_rotation.currentIndex()
            if idx == 0:
                return pixmap
            t = QTransform()
            t.rotate({1: 90, 2: -90, 3: 180}[idx])
            return pixmap.transformed(t, Qt.SmoothTransformation)

        def process():
            if combo_mode.currentIndex() == 0:
                if not self.switch_img_off or not self.switch_img_on:
                    QMessageBox.information(self, "Missing Assets", "Load both state images first.")
                    return
                w = max(self.switch_img_off.width(), self.switch_img_on.width())
                h = max(self.switch_img_off.height(), self.switch_img_on.height())
                off_s = apply_rotation(self.switch_img_off.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                on_s = apply_rotation(self.switch_img_on.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                res_w, res_h = off_s.width(), off_s.height()
                result = QPixmap(res_w, res_h * 2)
                result.fill(Qt.transparent)
                painter = QPainter(result)
                painter.drawPixmap(0, 0, off_s)
                painter.drawPixmap(0, res_h, on_s)
                painter.end()
                self.switch_last_pixmap = result
                self.switch_frame_size = (res_w, res_h)
                total_frames = 2
            else:
                if not self.switch_img_sprite:
                    QMessageBox.information(self, "Missing Assets", "Load a filmstrip to slice first.")
                    return
                frames = spin_sprite_frames.value()
                total_h = self.switch_img_sprite.height()
                frame_h = total_h // frames
                frame_w = self.switch_img_sprite.width()
                sliced = []
                for i in range(frames):
                    crop = self.switch_img_sprite.copy(0, i * frame_h, frame_w, frame_h)
                    sliced.append(apply_rotation(crop))
                out_w, out_h = sliced[0].width(), sliced[0].height()
                result = QPixmap(out_w, out_h * frames)
                result.fill(Qt.transparent)
                painter = QPainter(result)
                for i, fr in enumerate(sliced):
                    painter.drawPixmap(0, i * out_h, fr)
                painter.end()
                self.switch_last_pixmap = result
                self.switch_frame_size = (out_w, out_h)
                total_frames = frames

            fw, fh = self.switch_frame_size
            scrub.set_sheet(self.switch_last_pixmap, fw, fh, total_frames)
            btn_export.setEnabled(True)

        def export():
            if not self.switch_last_pixmap:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Export Filmstrip", "switch_filmstrip.png", "PNG Files (*.png)")
            if path:
                self.switch_last_pixmap.save(path, "PNG")

        btn_off.clicked.connect(lambda: load_image('off'))
        btn_on.clicked.connect(lambda: load_image('on'))
        btn_sprite.clicked.connect(lambda: load_image('sprite'))
        btn_process.clicked.connect(process)
        btn_export.clicked.connect(export)
        sld_pos.valueChanged.connect(lambda v: (setattr(canvas, 'pos', v / 100.0), canvas.update()))

        return ctrl, view, "Switch & Toggle Builder"

    # -------------------------------------------------------------------
    # ENGINE 5: PREAMP TUBE  (CaveSpriteWB3, unchanged logic)
    # -------------------------------------------------------------------
    def _build_tube_engine(self):
        self.tube_image = None
        self.tube_base_color = QColor("#25EFCB")
        self.tube_last_sheet = None

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        g1 = QGroupBox("1. Tube Asset & Dimensions")
        g1_l = QVBoxLayout(g1)
        btn_load_tube = QPushButton("Load Custom Tube Image (Optional)")
        lbl_tube = QLabel("Using Synthesized 12AX7 Glass Shell")
        lbl_tube.setWordWrap(True)
        dims = QHBoxLayout()
        spin_width = QSpinBox(); spin_width.setRange(32, 512); spin_width.setValue(128)
        spin_height = QSpinBox(); spin_height.setRange(64, 1024); spin_height.setValue(256)
        dims.addWidget(QLabel("W:")); dims.addWidget(spin_width)
        dims.addWidget(QLabel("H:")); dims.addWidget(spin_height)
        g1_l.addWidget(btn_load_tube); g1_l.addWidget(lbl_tube); g1_l.addLayout(dims)
        c_layout.addWidget(g1)

        g2 = QGroupBox("2. Gain & Filament Glow")
        g2_l = QFormLayout(g2)
        spin_frames = QSpinBox(); spin_frames.setRange(2, 64); spin_frames.setValue(31)
        combo_curve = QComboBox(); combo_curve.addItems(["Linear Gain", "Logarithmic (Audio)", "Overdrive (Exponential)"])
        slider_idle = QSlider(Qt.Horizontal); slider_idle.setRange(0, 100); slider_idle.setValue(20)
        spin_spread = QDoubleSpinBox(); spin_spread.setRange(0.5, 3.0); spin_spread.setSingleStep(0.1); spin_spread.setValue(1.5)
        btn_pick_color = QPushButton("Set Filament Glow Color")
        chk_reflections = QCheckBox("Render Internal Glass Reflections"); chk_reflections.setChecked(True)
        g2_l.addRow("Frame Count:", spin_frames)
        g2_l.addRow("Drive Curve:", combo_curve)
        g2_l.addRow("Idle Glow:", slider_idle)
        g2_l.addRow("Glow Spread:", spin_spread)
        g2_l.addRow(btn_pick_color)
        g2_l.addRow(chk_reflections)
        c_layout.addWidget(g2)

        g3 = QGroupBox("3. Interactive Drive Test")
        g3_l = QVBoxLayout(g3)
        g3_l.addWidget(QLabel("Input Drive Saturation:"))
        sld_drive = QSlider(Qt.Horizontal); sld_drive.setRange(0, 100); sld_drive.setValue(40)
        g3_l.addWidget(sld_drive)
        c_layout.addWidget(g3)

        btn_render = QPushButton("Render Preamp Tube Filmstrip")
        btn_export = QPushButton("Export Sprite Sheet (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_render)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        canvas = PreampCanvas()
        view, scrub = self._view_container("Live Thermionic Glow Canvas", canvas, "Tube Filmstrip Range Preview")

        def load_tube():
            path, _ = QFileDialog.getOpenFileName(self, "Load Glass Tube Overlay", "", "Images (*.png *.jpg *.bmp)")
            if path:
                self.tube_image = QPixmap(path)
                lbl_tube.setText(Path(path).name)

        def pick_color():
            c = QColorDialog.getColor(self.tube_base_color, self)
            if c.isValid():
                self.tube_base_color = c
                canvas.glow_color = c
                canvas.update()

        def drive_factor(frame_idx, total_frames):
            norm = frame_idx / (total_frames - 1) if total_frames > 1 else 0.0
            idle_boost = slider_idle.value() / 100.0
            curve = combo_curve.currentIndex()
            if curve == 0:
                drive = norm
            elif curve == 1:
                drive = math.log10(1 + 9 * norm)
            else:
                drive = math.pow(norm, 2.2)
            return min(1.0, idle_boost + (1.0 - idle_boost) * drive)

        def draw_synth_tube(painter, w, h, drive):
            center_x, center_y = w / 2, h * 0.55
            painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
            painter.setBrush(QBrush(QColor(20, 20, 25, 180)))
            painter.drawRoundedRect(w * 0.15, h * 0.1, w * 0.7, h * 0.8, w * 0.3, w * 0.3)

            plate_w, plate_h = w * 0.35, h * 0.45
            painter.setBrush(QBrush(QColor(10, 10, 12, 230)))
            painter.setPen(QPen(QColor(60, 60, 70), 1))
            painter.drawRoundedRect(center_x - plate_w / 2, center_y - plate_h / 2, plate_w, plate_h, 6, 6)

            spread = spin_spread.value()
            glow_radius = ((w * 0.35) + (drive * w * 0.6)) * spread
            r, g, b = self.tube_base_color.red(), self.tube_base_color.green(), self.tube_base_color.blue()
            rad_grad = QRadialGradient(center_x, center_y, glow_radius)
            rad_grad.setColorAt(0.0, QColor(min(255, r + 80), min(255, g + 80), min(255, b + 80), int(255 * drive)))
            rad_grad.setColorAt(0.2, QColor(r, g, b, int(200 * drive)))
            rad_grad.setColorAt(0.7, QColor(r, g, b, int(60 * drive)))
            rad_grad.setColorAt(1.0, QColor(r, g, b, 0))
            painter.setBrush(QBrush(rad_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(center_x, center_y), glow_radius, glow_radius)

            fil_col = QColor(min(255, r + 100), min(255, g + 100), min(255, b + 100), int(210 + 45 * drive))
            painter.setPen(QPen(fil_col, 2 + (drive * 3)))
            painter.drawLine(int(center_x - 4), int(center_y - plate_h / 3), int(center_x - 4), int(center_y + plate_h / 3))
            painter.drawLine(int(center_x + 4), int(center_y - plate_h / 3), int(center_x + 4), int(center_y + plate_h / 3))

            if chk_reflections.isChecked():
                spec = QLinearGradient(w * 0.2, h * 0.1, w * 0.4, h * 0.9)
                spec.setColorAt(0.0, QColor(255, 255, 255, 80))
                spec.setColorAt(0.3, QColor(255, 255, 255, 10))
                spec.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(QBrush(spec))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(w * 0.18, h * 0.12, w * 0.15, h * 0.76, 12, 12)

        def render():
            w, h, frames = spin_width.value(), spin_height.value(), spin_frames.value()
            sheet = QPixmap(w, h * frames)
            sheet.fill(Qt.transparent)
            painter = QPainter(sheet)
            painter.setRenderHint(QPainter.Antialiasing)
            for i in range(frames):
                drive = drive_factor(i, frames)
                painter.save()
                painter.translate(0, i * h)
                if self.tube_image:
                    scaled = self.tube_image.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(0, 0, scaled)
                    spread = spin_spread.value()
                    glow_radius = ((w * 0.35) + (drive * w * 0.5)) * spread
                    r, g, b = self.tube_base_color.red(), self.tube_base_color.green(), self.tube_base_color.blue()
                    grad = QRadialGradient(w / 2, h / 2, glow_radius)
                    grad.setColorAt(0.0, QColor(min(255, r + 80), min(255, g + 80), min(255, b + 80), int(220 * drive)))
                    grad.setColorAt(0.5, QColor(r, g, b, int(120 * drive)))
                    grad.setColorAt(1.0, QColor(r, g, b, 0))
                    painter.setBrush(QBrush(grad))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QPointF(w / 2, h / 2), glow_radius, glow_radius)
                else:
                    draw_synth_tube(painter, w, h, drive)
                painter.restore()
            painter.end()

            self.tube_last_sheet = sheet
            scrub.set_sheet(sheet, w, h, frames)
            btn_export.setEnabled(True)

        def export():
            if not self.tube_last_sheet:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save Tube Filmstrip", "preamp_tube_strip.png", "PNG (*.png)")
            if path:
                self.tube_last_sheet.save(path, "PNG")

        btn_load_tube.clicked.connect(load_tube)
        btn_pick_color.clicked.connect(pick_color)
        sld_drive.valueChanged.connect(lambda v: (setattr(canvas, 'drive', v / 100.0), canvas.update()))
        slider_idle.valueChanged.connect(lambda v: (setattr(canvas, 'warmup', v / 100.0), canvas.update()))
        btn_render.clicked.connect(render)
        btn_export.clicked.connect(export)

        return ctrl, view, "Preamp Tube Engine"

    # -------------------------------------------------------------------
    # ENGINE 6: VU METER  (WB3 render math + WB6 live calibration UX)
    # -------------------------------------------------------------------
    def _build_vu_engine(self):
        self.vu_face_pixmap = None
        self.vu_needle_pixmap = None
        self.vu_needle_color = QColor("#25EFCB")
        self.vu_last_sheet = None

        ctrl = QWidget()
        c_layout = QVBoxLayout(ctrl)

        g1 = QGroupBox("1. Meter Assets")
        g1_l = QVBoxLayout(g1)
        btn_face = QPushButton("Load VU Meter Face")
        lbl_face = QLabel("No face asset loaded")
        chk_overlay = QCheckBox("Use Overlay Needle Image"); chk_overlay.setChecked(False)
        btn_needle = QPushButton("Load Needle Asset")
        btn_needle.setEnabled(False)
        lbl_needle = QLabel("Using vector needle")
        btn_needle_color = QPushButton("Set Vector Needle Color")
        g1_l.addWidget(btn_face); g1_l.addWidget(lbl_face)
        g1_l.addWidget(chk_overlay)
        g1_l.addWidget(btn_needle); g1_l.addWidget(lbl_needle)
        g1_l.addWidget(btn_needle_color)
        c_layout.addWidget(g1)

        g2 = QGroupBox("2. Pivot & Needle Calibration")
        g2_l = QFormLayout(g2)
        spn_px = QDoubleSpinBox(); spn_px.setRange(0, 100); spn_px.setValue(50.0)
        spn_py = QDoubleSpinBox(); spn_py.setRange(0, 100); spn_py.setValue(82.0)
        spn_needle_len = QDoubleSpinBox(); spn_needle_len.setRange(20.0, 300.0); spn_needle_len.setSingleStep(5.0)
        spn_needle_len.setValue(100.0); spn_needle_len.setSuffix(" %")
        spn_needle_len.setToolTip(
            "Scales needle length only (not thickness). 100% = natural length "
            "for a vector needle, or the overlay needle image's native height."
        )
        combo_orientation = QComboBox()
        combo_orientation.addItem("Vertical (Rests Pointing Up)", 0.0)
        combo_orientation.addItem("Horizontal (Rests Pointing Right)", 90.0)
        combo_orientation.addItem("Horizontal (Rests Pointing Left)", -90.0)
        combo_orientation.addItem("Vertical (Rests Pointing Down)", 180.0)
        combo_orientation.setToolTip(
            "Rigidly rotates the whole needle assembly to match a sideways-mounted "
            "meter. Min/Max Angle below still describe the sweep relative to this "
            "rest position."
        )
        g2_l.addRow("Pivot X (% Width):", spn_px)
        g2_l.addRow("Pivot Y (% Height):", spn_py)
        g2_l.addRow("Needle Length:", spn_needle_len)
        g2_l.addRow("Needle Orientation:", combo_orientation)
        c_layout.addWidget(g2)

        g3 = QGroupBox("3. Sweep & Frame Parameters")
        g3_l = QFormLayout(g3)
        spin_frames = QSpinBox(); spin_frames.setRange(4, 128); spin_frames.setValue(31)
        spn_min = QDoubleSpinBox(); spn_min.setRange(-180, 180); spn_min.setValue(-42.0)
        spn_max = QDoubleSpinBox(); spn_max.setRange(-180, 180); spn_max.setValue(42.0)
        g3_l.addRow("Frame Count:", spin_frames)
        g3_l.addRow("Min Angle (-20 VU):", spn_min)
        g3_l.addRow("Max Angle (+3 VU):", spn_max)
        c_layout.addWidget(g3)

        g4 = QGroupBox("4. Interactive Test Signal")
        g4_l = QVBoxLayout(g4)
        sld_signal = QSlider(Qt.Horizontal); sld_signal.setRange(0, 100); sld_signal.setValue(50)
        g4_l.addWidget(sld_signal)
        c_layout.addWidget(g4)

        g5 = QGroupBox("5. Live Canvas Zoom")
        g5_l = QHBoxLayout(g5)
        lbl_zoom = QLabel("100%")
        lbl_zoom.setMinimumWidth(42)
        sld_zoom = QSlider(Qt.Horizontal); sld_zoom.setRange(100, 400); sld_zoom.setValue(100)
        sld_zoom.setToolTip("Zooms the Live Calibration Canvas above, anchored on the pivot point. You can also scroll on the canvas itself.")
        btn_zoom_reset = QPushButton("Reset")
        g5_l.addWidget(lbl_zoom)
        g5_l.addWidget(sld_zoom, 1)
        g5_l.addWidget(btn_zoom_reset)
        c_layout.addWidget(g5)

        btn_render = QPushButton("Render VU Meter Filmstrip")
        btn_export = QPushButton("Export Sprite Sheet (.png)")
        btn_export.setEnabled(False)
        c_layout.addWidget(btn_render)
        c_layout.addWidget(btn_export)
        c_layout.addStretch()

        canvas = VUMeterCanvas()
        view, scrub = self._view_container("Live Calibration Canvas", canvas, "VU Meter Filmstrip Range Preview")

        def toggle_needle_mode(enabled):
            btn_needle.setEnabled(enabled)
            btn_needle_color.setEnabled(not enabled)
            canvas.use_overlay = enabled
            canvas.update()

        def load_face():
            path, _ = QFileDialog.getOpenFileName(self, "Open Meter Face", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                lbl_face.setText(Path(path).name)
                canvas.face_pix = QPixmap(path)
                self.vu_face_pixmap = canvas.face_pix
                canvas.update()

        def load_needle():
            path, _ = QFileDialog.getOpenFileName(self, "Open Needle Asset", "", "Images (*.png)")
            if path:
                lbl_needle.setText(Path(path).name)
                canvas.needle_pix = QPixmap(path)
                self.vu_needle_pixmap = canvas.needle_pix
                canvas.update()

        def pick_needle_color():
            c = QColorDialog.getColor(self.vu_needle_color, self)
            if c.isValid():
                self.vu_needle_color = c
                canvas.vector_color = c
                canvas.update()

        def sync_calibration():
            canvas.pivot_x_pct = spn_px.value()
            canvas.pivot_y_pct = spn_py.value()
            canvas.min_angle = spn_min.value()
            canvas.max_angle = spn_max.value()
            canvas.needle_length_pct = spn_needle_len.value()
            canvas.orientation_offset = combo_orientation.currentData()
            canvas.update()

        def render():
            if not self.vu_face_pixmap:
                QMessageBox.information(self, "No Face Loaded", "Load a VU meter face image first.")
                return
            w, h = self.vu_face_pixmap.width(), self.vu_face_pixmap.height()
            frames = spin_frames.value()
            min_a, max_a = spn_min.value(), spn_max.value()
            px = w * (spn_px.value() / 100.0)
            py = h * (spn_py.value() / 100.0)
            length_scale = spn_needle_len.value() / 100.0
            orientation_offset = combo_orientation.currentData()

            sheet = QPixmap(w, h * frames)
            sheet.fill(Qt.transparent)
            painter = QPainter(sheet)
            painter.setRenderHint(QPainter.Antialiasing)

            for i in range(frames):
                frame_y = i * h
                t = i / (frames - 1) if frames > 1 else 0.0
                angle = orientation_offset + min_a + (max_a - min_a) * t
                painter.drawPixmap(0, frame_y, self.vu_face_pixmap)
                if chk_overlay.isChecked() and self.vu_needle_pixmap:
                    draw_vu_needle_overlay(painter, self.vu_needle_pixmap, px, frame_y + py, angle, length_scale)
                else:
                    draw_vu_needle_vector(painter, px, frame_y + py, angle, h * 0.65 * length_scale, self.vu_needle_color)
            painter.end()

            self.vu_last_sheet = sheet
            scrub.set_sheet(sheet, w, h, frames)
            btn_export.setEnabled(True)

        def export():
            if not self.vu_last_sheet:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Save VU Meter Strip", "vu_meter_strip.png", "PNG (*.png)")
            if path:
                self.vu_last_sheet.save(path, "PNG")

        chk_overlay.toggled.connect(toggle_needle_mode)
        btn_face.clicked.connect(load_face)
        btn_needle.clicked.connect(load_needle)
        btn_needle_color.clicked.connect(pick_needle_color)
        sld_signal.valueChanged.connect(lambda v: (setattr(canvas, 'val', v / 100.0), canvas.update()))
        spn_px.valueChanged.connect(sync_calibration)
        spn_py.valueChanged.connect(sync_calibration)
        spn_min.valueChanged.connect(sync_calibration)
        spn_max.valueChanged.connect(sync_calibration)
        spn_needle_len.valueChanged.connect(sync_calibration)
        combo_orientation.currentIndexChanged.connect(sync_calibration)

        def on_zoom_slider_changed(v):
            lbl_zoom.setText(f"{v}%")
            canvas.zoom = v / 100.0
            canvas.update()

        def on_canvas_zoom_changed(z):
            sld_zoom.blockSignals(True)
            sld_zoom.setValue(int(round(z * 100)))
            sld_zoom.blockSignals(False)
            lbl_zoom.setText(f"{int(round(z * 100))}%")

        sld_zoom.valueChanged.connect(on_zoom_slider_changed)
        canvas.zoomChanged.connect(on_canvas_zoom_changed)
        btn_zoom_reset.clicked.connect(lambda: sld_zoom.setValue(100))

        btn_render.clicked.connect(render)
        btn_export.clicked.connect(export)

        return ctrl, view, "VU Meter Engine"

    # -------------------------------------------------------------------
    # Drag & drop convenience: drop an image onto the window to feed
    # whichever tab is currently active.
    # -------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                idx = self.tabs.currentIndex()
                if idx == 0:  # Knob Engine
                    self.knob_input_path = file_path
                    self.knob_batch_folder = ""
                    self.lbl_knob_input.setText(f"File: {Path(file_path).name}")
                break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = CaveSpriteWorkbench()
    window.show()
    sys.exit(app.exec())
