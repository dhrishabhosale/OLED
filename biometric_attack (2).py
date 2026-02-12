#!/usr/bin/python3
# -*- coding:utf-8 -*-
#
# biometric_attack.py — Improved embedded firmware
# Fixes applied:
#   1. Non-blocking animations via state machine (no time.sleep in main loop)
#   2. Screensaver state checks buttons every iteration
#   3. Aspect-ratio-preserving frame resize (centered on black canvas)
#   4. Pixel-accurate text wrapping via font.getlength()

import SH1106
import config
import time
import os
import glob
from PIL import Image, ImageDraw, ImageFont

# =============================
# INITIALIZE DISPLAY
# =============================
try:
    disp = SH1106.SH1106()
    disp.Init()
    disp.clear()
except Exception as e:
    print(f"Error initializing display: {e}")
    exit(1)

width  = disp.width   # 128
height = disp.height  # 64

try:
    font = ImageFont.load_default()
except Exception:
    font = None

# =============================
# SCREEN STATES
# =============================
STATE_IDENTIFY        = 0
STATE_DEVICES_FOUND   = 1
STATE_BIOMETRIC_MENU  = 2
STATE_ARM_LOADING     = 3   # non-blocking boot animation
STATE_ARM_SUCCESS     = 4
STATE_FORMAT_LOADING  = 5   # non-blocking boot animation
STATE_FORMAT_SUCCESS  = 6
STATE_SCREENSAVER     = 7
STATE_QR              = 8

current_state   = STATE_IDENTIFY
selected_option = 0

# =============================
# FIX 3 — ASPECT-RATIO-PRESERVING FRAME LOADER
# =============================
def _fit_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Resize *img* so it fits inside (target_w × target_h) while keeping
    its original aspect ratio.  The result is centred on a white canvas.
    """
    orig_w, orig_h = img.size
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("1", (target_w, target_h), 1)   # white background
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas

# =============================
# SCREENSAVER FRAMES
# =============================
animation_frames = []
try:
    frame_paths = sorted(glob.glob("pngframes/nite*.bmp"))
    if not frame_paths:
        frame_paths = sorted(glob.glob("/mnt/user-data/uploads/pngframes/nite*.bmp"))

    if frame_paths:
        print(f"Loading {len(frame_paths)} animation frames...")
        for fp in frame_paths:
            try:
                frame = Image.open(fp).convert("1")
                # FIX 3: preserve aspect ratio instead of a raw .resize()
                frame = _fit_image(frame, width, height)
                animation_frames.append(frame)
            except Exception as e:
                print(f"Error loading {fp}: {e}")
        print(f"✓ Loaded {len(animation_frames)} frames")
    else:
        print("No animation frames found, using fallback")
except Exception as e:
    print(f"Error loading animation frames: {e}")

if not animation_frames:
    print("Using fallback diamond animation")
    bmp = Image.new("1", (16, 16), 1)
    draw_bmp = ImageDraw.Draw(bmp)
    draw_bmp.polygon([(8, 0), (16, 8), (8, 16), (0, 8)], outline=0, fill=0)
    animation_frames = [bmp]

current_frame = 0

# =============================
# QR IMAGE
# =============================
try:
    qr = Image.open("qr.png").convert("1")
    qr = qr.resize((64, 64))
except Exception:
    try:
        qr = Image.open("/mnt/user-data/uploads/qr.png").convert("1")
        qr = qr.resize((64, 64))
    except Exception as e:
        print(f"Warning: QR code not found ({e}), using placeholder")
        qr = Image.new("1", (64, 64), 1)
        dq = ImageDraw.Draw(qr)
        for i in range(0, 64, 8):
            dq.line([(i, 0), (i, 64)], fill=0)
            dq.line([(0, i), (64, i)], fill=0)
        for cx, cy in [(0, 0), (56, 0), (0, 56)]:
            dq.rectangle((cx, cy, cx + 8, cy + 8), outline=0)
            dq.rectangle((cx + 2, cy + 2, cx + 6, cy + 6), fill=0)

# =============================
# HELPER — DISPLAY
# =============================
def show(img: Image.Image):
    try:
        disp.ShowImage(disp.getbuffer(img))
    except Exception as e:
        print(f"Display error: {e}")

# =============================
# FIX 4 — PIXEL-ACCURATE TEXT WRAPPING
# =============================
def _wrap_text(text: str, max_px: int) -> list[str]:
    """
    Split *text* into lines whose rendered width does not exceed *max_px*.
    Uses font.getlength() when available; falls back to character counting.
    """
    def text_width(s: str) -> float:
        if font and hasattr(font, "getlength"):
            return font.getlength(s)
        # Fallback: default font is ~6 px per character
        return len(s) * 6.0

    words  = text.split()
    lines  = []
    line   = ""
    for word in words:
        candidate = (line + " " + word).lstrip()
        if text_width(candidate) <= max_px:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

# =============================
# HELPER — BUTTON (draws a filled or outline button)
# =============================
def draw_button(draw, x, y, w, h, text, selected=False):
    if selected:
        draw.rectangle((x, y, x + w, y + h), outline=0, fill=0)
        draw.text((x + 4, y + 3), text, font=font, fill=1)
    else:
        draw.rectangle((x, y, x + w, y + h), outline=0, fill=1)
        draw.text((x + 4, y + 3), text, font=font, fill=0)

# =============================
# NON-BLOCKING ANIMATION STATE  (FIX 1)
# =============================
# Each "animation" is described by a sequence of steps:
#   steps = list of (phase, data, duration_ms)
# We drive one step per main-loop tick.

_anim_steps        = []    # list of (phase, payload, duration_ms)
_anim_step_index   = 0
_anim_step_start   = 0.0   # wall-clock time when current step began
_anim_done_state   = STATE_ARM_SUCCESS   # state to enter when done

_PHASE_BOOT_LINE  = "boot_line"   # payload = list of visible lines so far
_PHASE_PROGRESS   = "progress"    # payload = int 0-100
_PHASE_SUCCESS    = "success"     # payload = final_message string

def _build_animation_steps(boot_lines: list[str],
                            final_message: str,
                            next_state: int) -> None:
    """Populate _anim_steps with boot-line, progress and success steps."""
    global _anim_steps, _anim_step_index, _anim_step_start, _anim_done_state
    _anim_steps      = []
    _anim_step_index = 0
    _anim_step_start = time.monotonic()
    _anim_done_state = next_state

    # Phase 1 — boot lines, each displayed for 300 ms
    for i in range(len(boot_lines)):
        _anim_steps.append((_PHASE_BOOT_LINE, boot_lines[: i + 1], 300))

    # Phase 2 — progress bar steps, each tick advances 3 %, at 50 ms each
    for pct in range(0, 101, 3):
        _anim_steps.append((_PHASE_PROGRESS, pct, 50))

    # Phase 3 — success / done, held for 2000 ms
    _anim_steps.append((_PHASE_SUCCESS, final_message, 2000))


def _tick_animation() -> bool:
    """
    Called once per main-loop iteration when in STATE_ARM_LOADING or
    STATE_FORMAT_LOADING.

    Renders the current step to the OLED.  Advances to the next step when
    its duration has elapsed.

    Returns True when the entire animation sequence is finished.
    """
    global _anim_step_index, _anim_step_start

    if _anim_step_index >= len(_anim_steps):
        return True  # already done

    phase, payload, duration_ms = _anim_steps[_anim_step_index]
    now = time.monotonic()
    elapsed_ms = (now - _anim_step_start) * 1000.0

    # --- Render current step ---
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    if phase == _PHASE_BOOT_LINE:
        y_pos = 5
        for line in payload[-5:]:   # show at most 5 lines
            if y_pos < height - 10:
                draw.text((5, y_pos), line, font=font, fill=0)
                y_pos += 12

    elif phase == _PHASE_PROGRESS:
        progress = payload
        draw.text((30, 5), "Processing", font=font, fill=0)
        draw.text((100, 5), f"{progress}%", font=font, fill=0)

        track_y = 25
        draw.rectangle((10, track_y, 118, track_y + 8), outline=0)
        draw.rectangle((11, track_y + 1, 117, track_y + 7), outline=0)

        cat_x = 12 + int((104 * progress) / 100)

        if progress > 0:
            fill_width = int((106 * progress) / 100)
            draw.rectangle((12, track_y + 2, 12 + fill_width, track_y + 6), fill=0)

        # Alternating cat pose — use step index for animation variety
        cat_frame = (_anim_step_index // 2) % 2
        if cat_frame == 0:
            draw.rectangle((cat_x, track_y - 5, cat_x + 8, track_y), fill=0)
            draw.rectangle((cat_x + 6, track_y - 8, cat_x + 10, track_y - 4), fill=0)
            draw.polygon([(cat_x + 6, track_y - 8), (cat_x + 7, track_y - 10), (cat_x + 8, track_y - 8)], fill=0)
            draw.polygon([(cat_x + 8, track_y - 8), (cat_x + 9, track_y - 10), (cat_x + 10, track_y - 8)], fill=0)
            draw.line([(cat_x, track_y - 4), (cat_x - 2, track_y - 7)], fill=0)
            draw.line([(cat_x + 7, track_y), (cat_x + 7, track_y + 2)], fill=0)
            draw.line([(cat_x + 2, track_y), (cat_x + 1, track_y + 2)], fill=0)
        else:
            draw.rectangle((cat_x, track_y - 4, cat_x + 8, track_y), fill=0)
            draw.rectangle((cat_x + 6, track_y - 7, cat_x + 10, track_y - 3), fill=0)
            draw.polygon([(cat_x + 6, track_y - 7), (cat_x + 7, track_y - 9), (cat_x + 8, track_y - 7)], fill=0)
            draw.polygon([(cat_x + 8, track_y - 7), (cat_x + 9, track_y - 9), (cat_x + 10, track_y - 7)], fill=0)
            draw.line([(cat_x, track_y - 3), (cat_x - 2, track_y - 5)], fill=0)
            draw.line([(cat_x + 4, track_y), (cat_x + 4, track_y + 2)], fill=0)
            draw.line([(cat_x + 5, track_y), (cat_x + 5, track_y + 2)], fill=0)

        draw.text((25, 40), "Please wait...", font=font, fill=0)

    elif phase == _PHASE_SUCCESS:
        # FIX 4: pixel-accurate wrapping within the box interior (max ~90 px)
        draw.rectangle((10, 15, 118, 50), outline=0)
        draw.rectangle((12, 17, 116, 48), outline=0)

        lines   = _wrap_text(payload, 90)
        total_h = len(lines) * 12
        y_start = 32 - total_h // 2   # vertical-centre inside the box
        for i, ln in enumerate(lines):
            draw.text((20, y_start + i * 12), ln, font=font, fill=0)

    show(img)

    # --- Advance step when duration has elapsed ---
    if elapsed_ms >= duration_ms:
        _anim_step_index += 1
        _anim_step_start  = time.monotonic()

    return _anim_step_index >= len(_anim_steps)

# =============================
# STATIC SCREEN DRAWING FUNCTIONS
# =============================
def draw_identify_screen():
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width - 1, 15), outline=0, fill=0)
    draw.text((15, 3),  "BIOMETRIC ATTACK", font=font, fill=1)
    draw.text((20, 25), "IDENTIFY",         font=font, fill=0)
    draw.text((25, 37), "DEVICE",           font=font, fill=0)
    draw.text((10, 52), "Press [CENTER]",   font=font, fill=0)
    show(img)

def draw_devices_found_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width - 1, 15), outline=0, fill=0)
    draw.text((20, 3), "DEVICES FOUND", font=font, fill=1)
    draw_button(draw, 10, 20, 108, 15, "Biometric Lock", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "Re-scan",        selected == 1)
    show(img)

def draw_biometric_menu_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width - 1, 15), outline=0, fill=0)
    draw.text((10, 3), "BIOMETRIC LOCK", font=font, fill=1)
    draw_button(draw, 10, 20, 108, 15, "ARM",    selected == 0)
    draw_button(draw, 10, 40, 108, 15, "FORMAT", selected == 1)
    show(img)

def draw_arm_success_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width - 1, 15), outline=0, fill=0)
    draw.text((30, 3),  "DISARMED",        font=font, fill=1)
    draw.text((15, 20), "Attack Complete", font=font, fill=0)
    draw_button(draw, 10, 35, 108, 12, "Rerun Attack", selected == 0)
    draw.text((15, 52), "Press [3] to exit", font=font, fill=0)
    show(img)

def draw_format_success_screen():
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width - 1, 15), outline=0, fill=0)
    draw.text((20, 3),  "FORMAT DONE",      font=font, fill=1)
    draw.text((10, 25), "All users cleared", font=font, fill=0)
    draw.text((15, 45), "Press [3] to exit", font=font, fill=0)
    show(img)

# =============================
# MAIN LOOP
# =============================
print("Starting Biometric Attack Interface...")
print("Controls:")
print("  UP/DOWN  : Navigate menu")
print("  CENTER   : Select")
print("  KEY1 (1) : Screensaver")
print("  KEY2 (2) : QR Code")
print("  KEY3 (3) : Return to identify screen (works ANY time, even during animation)")

try:
    FRAME_PERIOD = 0.05          # 20 Hz main loop  (~50 ms per tick)
    last_tick    = time.monotonic()
    button_db    = {}            # debounce registry

    def btn(pin_attr: str) -> bool:
        """Return True on the rising edge of a button (with debounce)."""
        pressed = disp.RPI.digital_read(getattr(disp.RPI, pin_attr))
        was     = button_db.get(pin_attr, False)
        button_db[pin_attr] = pressed
        return pressed and not was

    while True:
        # --- Enforce a consistent tick rate (non-blocking) ---
        now   = time.monotonic()
        delta = now - last_tick
        if delta < FRAME_PERIOD:
            time.sleep(FRAME_PERIOD - delta)
        last_tick = time.monotonic()

        # -------------------------------------------------------
        # GLOBAL BUTTONS — checked every tick, including during
        # animations (FIX 1 side-effect: interruption now works)
        # -------------------------------------------------------
        if btn("GPIO_KEY3_PIN"):
            current_state   = STATE_IDENTIFY
            selected_option = 0
            print("→ [KEY3] Returned to IDENTIFY screen")

        if btn("GPIO_KEY1_PIN") and current_state not in (STATE_ARM_LOADING, STATE_FORMAT_LOADING):
            current_state = STATE_SCREENSAVER
            print("→ [KEY1] Screensaver")

        if btn("GPIO_KEY2_PIN") and current_state not in (STATE_ARM_LOADING, STATE_FORMAT_LOADING):
            current_state = STATE_QR
            print("→ [KEY2] QR Code")

        # -------------------------------------------------------
        # STATE MACHINE
        # -------------------------------------------------------

        # ---- IDENTIFY ----
        if current_state == STATE_IDENTIFY:
            draw_identify_screen()
            if btn("GPIO_KEY_PRESS_PIN"):
                print("→ Scanning for devices...")
                current_state   = STATE_DEVICES_FOUND
                selected_option = 0

        # ---- DEVICES FOUND ----
        elif current_state == STATE_DEVICES_FOUND:
            draw_devices_found_screen(selected_option)
            if btn("GPIO_KEY_UP_PIN"):
                selected_option = (selected_option - 1) % 2
            if btn("GPIO_KEY_DOWN_PIN"):
                selected_option = (selected_option + 1) % 2
            if btn("GPIO_KEY_PRESS_PIN"):
                if selected_option == 0:
                    print("→ Entering BIOMETRIC LOCK menu")
                    current_state   = STATE_BIOMETRIC_MENU
                    selected_option = 0
                else:
                    print("→ Re-scanning...")
                    current_state   = STATE_IDENTIFY
                    selected_option = 0

        # ---- BIOMETRIC MENU ----
        elif current_state == STATE_BIOMETRIC_MENU:
            draw_biometric_menu_screen(selected_option)
            if btn("GPIO_KEY_UP_PIN"):
                selected_option = (selected_option - 1) % 2
            if btn("GPIO_KEY_DOWN_PIN"):
                selected_option = (selected_option + 1) % 2
            if btn("GPIO_KEY_PRESS_PIN"):
                if selected_option == 0:
                    # FIX 1: kick off non-blocking ARM animation
                    print("→ Executing ARM attack (non-blocking)...")
                    _build_animation_steps(
                        boot_lines=[
                            "[ OK ] Starting ARM",
                            "[ OK ] Loading exploit",
                            "[ OK ] Bypassing auth",
                            "[ OK ] Injecting code",
                            "[ ** ] Executing...",
                        ],
                        final_message="DOOR OPEN",
                        next_state=STATE_ARM_SUCCESS,
                    )
                    current_state   = STATE_ARM_LOADING
                    selected_option = 0
                else:
                    # FIX 1: kick off non-blocking FORMAT animation
                    print("→ Executing FORMAT attack (non-blocking)...")
                    _build_animation_steps(
                        boot_lines=[
                            "[ OK ] Starting FORMAT",
                            "[ OK ] Accessing DB",
                            "[ OK ] Clearing users",
                            "[ ** ] Wiping data...",
                            "[ OK ] Cleanup done",
                        ],
                        final_message="FORMAT COMPLETE",
                        next_state=STATE_FORMAT_SUCCESS,
                    )
                    current_state = STATE_FORMAT_LOADING

        # ---- ARM LOADING (non-blocking animation) ----
        elif current_state == STATE_ARM_LOADING:
            # FIX 1: one frame of animation per loop tick; KEY3 can preempt
            if _tick_animation():
                # Also show the "DISARMED" splash for one extra beat
                img  = Image.new("1", (width, height), 1)
                draw = ImageDraw.Draw(img)
                draw.rectangle((10, 10, 118, 40), outline=0)
                draw.rectangle((12, 12, 116, 38), outline=0)
                draw.text((30, 18), "DISARMED", font=font, fill=0)
                show(img)
                time.sleep(1.0)            # single intentional pause after done
                current_state = _anim_done_state

        # ---- FORMAT LOADING (non-blocking animation) ----
        elif current_state == STATE_FORMAT_LOADING:
            # FIX 1: same pattern
            if _tick_animation():
                current_state = _anim_done_state

        # ---- ARM SUCCESS ----
        elif current_state == STATE_ARM_SUCCESS:
            draw_arm_success_screen(selected_option)
            if btn("GPIO_KEY_PRESS_PIN"):
                print("→ Rerunning ARM attack (non-blocking)...")
                _build_animation_steps(
                    boot_lines=[
                        "[ OK ] Starting ARM",
                        "[ OK ] Loading exploit",
                        "[ OK ] Bypassing auth",
                        "[ OK ] Injecting code",
                        "[ ** ] Executing...",
                    ],
                    final_message="DOOR OPEN",
                    next_state=STATE_ARM_SUCCESS,
                )
                current_state = STATE_ARM_LOADING

        # ---- FORMAT SUCCESS ----
        elif current_state == STATE_FORMAT_SUCCESS:
            draw_format_success_screen()
            # Wait for KEY3 (handled globally above)

        # ---- SCREENSAVER ----
        elif current_state == STATE_SCREENSAVER:
            # FIX 2: buttons are already polled at the top of every tick,
            # so KEY1/KEY2/KEY3 respond immediately — no extra handling needed.
            img = Image.new("1", (width, height), 1)
            if animation_frames:
                img.paste(animation_frames[current_frame], (0, 0))
            show(img)
            current_frame = (current_frame + 1) % len(animation_frames)
            # No extra sleep — the FRAME_PERIOD at the top of the loop
            # controls the frame rate (~20 FPS).

        # ---- QR ----
        elif current_state == STATE_QR:
            img   = Image.new("1", (width, height), 1)
            qr_x  = (width  - 64) // 2
            qr_y  = (height - 64) // 2
            img.paste(qr, (qr_x, qr_y))
            show(img)

except KeyboardInterrupt:
    print("\nShutting down...")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        disp.clear()
        disp.RPI.module_exit()
        print("Display cleaned up successfully")
    except Exception:
        pass
