#!/usr/bin/python3
# -*- coding:utf-8 -*-

import SH1106
import config
import time
import subprocess
import random
import os
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

width = disp.width
height = disp.height

try:
    font = ImageFont.load_default()
except:
    font = None

# =============================
# SCREEN STATES
# =============================
STATE_IDENTIFY       = 0
STATE_DEVICES_FOUND  = 1
STATE_BIOMETRIC_MENU = 2
STATE_ARM_LOADING    = 3
STATE_ARM_SUCCESS    = 4
STATE_FORMAT_LOADING = 5
STATE_FORMAT_SUCCESS = 6
STATE_SCREENSAVER    = 7
STATE_QR             = 8

current_state   = STATE_IDENTIFY
selected_option = 0

# =============================
# SCREENSAVER — bouncing pic.png sprite
# =============================
def _load_sprite(path):
    img = Image.open(path).convert("1")
    img.thumbnail((32, 32), Image.Resampling.LANCZOS)
    return img, img.size[0], img.size[1]

try:
    bmp, bmp_w, bmp_h = _load_sprite("pic.png")
    print(f"✓ Loaded pic.png ({bmp_w}x{bmp_h})")
except Exception:
    try:
        bmp, bmp_w, bmp_h = _load_sprite("/mnt/user-data/uploads/pic.png")
        print(f"✓ Loaded pic.png from uploads ({bmp_w}x{bmp_h})")
    except Exception as e:
        print(f"Warning: pic.png not found ({e}), using fallback diamond")
        bmp = Image.new("1", (16, 16), 1)
        ImageDraw.Draw(bmp).polygon([(8,0),(16,8),(8,16),(0,8)], outline=0, fill=0)
        bmp_w, bmp_h = bmp.size

diamond_x = 10
diamond_y = 10
vel = [2, 2]   # mutable list — no global declaration needed

# =============================
# QR IMAGE
# =============================
try:
    qr = Image.open("qr.png").convert("1").resize((64, 64))
except Exception:
    try:
        qr = Image.open("/mnt/user-data/uploads/qr.png").convert("1").resize((64, 64))
    except Exception as e:
        print(f"Warning: qr.png not found ({e}), using placeholder")
        qr = Image.new("1", (64, 64), 1)
        dq = ImageDraw.Draw(qr)
        for i in range(0, 64, 8):
            dq.line([(i, 0), (i, 64)], fill=0)
            dq.line([(0, i), (64, i)], fill=0)
        for cx, cy in [(0,0), (56,0), (0,56)]:
            dq.rectangle((cx, cy, cx+8, cy+8), outline=0)
            dq.rectangle((cx+2, cy+2, cx+6, cy+6), fill=0)

# =============================
# HELPERS
# =============================
def show(img):
    try:
        disp.ShowImage(disp.getbuffer(img))
    except Exception as e:
        print(f"Display error: {e}")

def draw_button(draw, x, y, w, h, text, selected=False):
    if selected:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=0)
        draw.rectangle((x+1, y+1, x+w-1, y+h-1), outline=1, fill=1)
        draw.text((x+4, y+3), text, font=font, fill=0)
    else:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=1)
        draw.text((x+4, y+3), text, font=font, fill=0)

def _draw_centered_text_in_box(draw, message,
                                box_x1=10, box_y1=15, box_x2=118, box_y2=50):
    """
    Draw double-border box and render message centred inside it.
    Wraps by pixel width; clamps y so text never escapes the box.
    """
    # Outer + inner border
    draw.rectangle((box_x1,   box_y1,   box_x2,   box_y2),   outline=0)
    draw.rectangle((box_x1+2, box_y1+2, box_x2-2, box_y2-2), outline=0)

    pad    = 4
    ix1    = box_x1 + pad   # 14
    iy1    = box_y1 + pad   # 19
    ix2    = box_x2 - pad   # 114
    iy2    = box_y2 - pad   # 46
    iw     = ix2 - ix1      # 100 px available width
    ih     = iy2 - iy1      # 27 px available height
    line_h = 10             # ~8 px glyph + 2 px leading

    # Pixel-accurate word wrap
    words = message.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).lstrip()
        tw = font.getlength(candidate) if hasattr(font, "getlength") else len(candidate) * 6
        if tw <= iw:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    # Vertical centre
    total_h = len(lines) * line_h
    y0 = iy1 + max(0, (ih - total_h) // 2)

    for i, line in enumerate(lines):
        tw = font.getlength(line) if hasattr(font, "getlength") else len(line) * 6
        x  = ix1 + max(0, (iw - int(tw)) // 2)
        y  = min(y0 + i * line_h, iy2 - line_h)   # clamp bottom
        draw.text((x, y), line, font=font, fill=0)

def arch_boot_animation(lines, final_message):
    """Arch Linux style boot animation: scrolling lines → cat bar → result box."""
    # Phase 1: scrolling boot lines
    for i in range(len(lines)):
        img  = Image.new("1", (width, height), 1)
        draw = ImageDraw.Draw(img)
        y_pos = 5
        for j in range(max(0, i - 4), i + 1):
            if y_pos < height - 10:
                draw.text((5, y_pos), lines[j], font=font, fill=0)
                y_pos += 12
        show(img)
        time.sleep(0.3)

    time.sleep(0.3)

    # Phase 2: cat progress bar
    for progress in range(0, 101, 3):
        img  = Image.new("1", (width, height), 1)
        draw = ImageDraw.Draw(img)

        draw.text((30, 5),  "Processing",    font=font, fill=0)
        draw.text((100, 5), f"{progress}%",  font=font, fill=0)

        track_y = 25
        draw.rectangle((10, track_y, 118, track_y + 8), outline=0)
        draw.rectangle((11, track_y + 1, 117, track_y + 7), outline=0)

        cat_x = 12 + int((104 * progress) / 100)
        if progress > 0:
            fill_width = int((106 * progress) / 100)
            draw.rectangle((12, track_y + 2, 12 + fill_width, track_y + 6), fill=0)

        frame = (progress // 5) % 2
        if frame == 0:
            draw.rectangle((cat_x, track_y-5, cat_x+8, track_y), fill=0)
            draw.rectangle((cat_x+6, track_y-8, cat_x+10, track_y-4), fill=0)
            draw.polygon([(cat_x+6,track_y-8),(cat_x+7,track_y-10),(cat_x+8,track_y-8)], fill=0)
            draw.polygon([(cat_x+8,track_y-8),(cat_x+9,track_y-10),(cat_x+10,track_y-8)], fill=0)
            draw.line([(cat_x,track_y-4),(cat_x-2,track_y-7)], fill=0)
            draw.line([(cat_x+7,track_y),(cat_x+7,track_y+2)], fill=0)
            draw.line([(cat_x+2,track_y),(cat_x+1,track_y+2)], fill=0)
        else:
            draw.rectangle((cat_x, track_y-4, cat_x+8, track_y), fill=0)
            draw.rectangle((cat_x+6, track_y-7, cat_x+10, track_y-3), fill=0)
            draw.polygon([(cat_x+6,track_y-7),(cat_x+7,track_y-9),(cat_x+8,track_y-7)], fill=0)
            draw.polygon([(cat_x+8,track_y-7),(cat_x+9,track_y-9),(cat_x+10,track_y-7)], fill=0)
            draw.line([(cat_x,track_y-3),(cat_x-2,track_y-5)], fill=0)
            draw.line([(cat_x+4,track_y),(cat_x+4,track_y+2)], fill=0)
            draw.line([(cat_x+5,track_y),(cat_x+5,track_y+2)], fill=0)

        draw.text((25, 40), "Please wait...", font=font, fill=0)
        show(img)
        time.sleep(0.05)

    # Phase 3: result box — properly centred text inside box
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    _draw_centered_text_in_box(draw, final_message)
    show(img)
    time.sleep(2)

# =============================
# SCREEN FUNCTIONS
# =============================
def draw_identify_screen():
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((15, 3),  "BIOMETRIC ATTACK", font=font, fill=1)
    draw.text((20, 25), "IDENTIFY",         font=font, fill=0)
    draw.text((25, 37), "DEVICE",           font=font, fill=0)
    draw.text((10, 52), "Press [CENTER]",   font=font, fill=0)
    show(img)

def draw_devices_found_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((20, 3), "DEVICES FOUND", font=font, fill=1)
    draw_button(draw, 10, 20, 108, 15, "Biometric Lock", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "Re-scan",        selected == 1)
    show(img)

def draw_biometric_menu_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((10, 3), "BIOMETRIC LOCK", font=font, fill=1)
    draw_button(draw, 10, 20, 108, 15, "ARM",    selected == 0)
    draw_button(draw, 10, 40, 108, 15, "FORMAT", selected == 1)
    show(img)

def arm_attack_sequence():
    arch_boot_animation([
        "[ OK ] Starting ARM",
        "[ OK ] Loading exploit",
        "[ OK ] Bypassing auth",
        "[ OK ] Injecting code",
        "[ ** ] Executing...",
    ], "DOOR OPEN")

    # Launch door.py
    door_script = None
    if os.path.exists("door.py"):
        door_script = "door.py"
    elif os.path.exists("/mnt/user-data/uploads/door.py"):
        door_script = "/mnt/user-data/uploads/door.py"

    if door_script:
        try:
            subprocess.Popen(["python3", door_script])
            print(f"✓ Launched {door_script}")
        except Exception as e:
            print(f"Error launching door.py: {e}")
    else:
        print("door.py not found — continuing without it")

    # DISARMED splash
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((10, 10, 118, 40), outline=0)
    draw.rectangle((12, 12, 116, 38), outline=0)
    draw.text((30, 18), "DISARMED", font=font, fill=0)
    show(img)
    time.sleep(1.5)

def draw_arm_success_screen(selected):
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((30, 3),  "DISARMED",          font=font, fill=1)
    draw.text((15, 20), "Attack Complete",   font=font, fill=0)
    draw_button(draw, 10, 35, 108, 12, "Rerun Attack", selected == 0)
    draw.text((15, 52), "Press [3] to exit", font=font, fill=0)
    show(img)

def format_attack_sequence():
    arch_boot_animation([
        "[ OK ] Starting FORMAT",
        "[ OK ] Accessing DB",
        "[ OK ] Clearing users",
        "[ ** ] Wiping data...",
        "[ OK ] Cleanup done",
    ], "FORMAT COMPLETE")

def draw_format_success_screen():
    img  = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((20, 3),  "FORMAT DONE",       font=font, fill=1)
    draw.text((10, 25), "All users cleared", font=font, fill=0)
    draw.text((15, 45), "Press [3] to exit", font=font, fill=0)
    show(img)

# =============================
# MAIN LOOP
# =============================
print("Starting Biometric Attack Interface...")
print("Controls: UP/DOWN=navigate  CENTER=select  1=screensaver  2=QR  3=home")

try:
    last_time       = time.time()
    frame_delay     = 0.05
    button_debounce = {}

    while True:
        now = time.time()
        if now - last_time < frame_delay:
            time.sleep(frame_delay - (now - last_time))
        last_time = time.time()

        # --- Global keys ---
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN):
            if current_state != STATE_SCREENSAVER:
                current_state = STATE_SCREENSAVER
                print("→ Screensaver")
            time.sleep(0.3)

        if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN):
            if current_state != STATE_QR:
                current_state = STATE_QR
                print("→ QR Code")
            time.sleep(0.3)

        if disp.RPI.digital_read(disp.RPI.GPIO_KEY3_PIN):
            current_state   = STATE_IDENTIFY
            selected_option = 0
            print("→ Home")
            time.sleep(0.3)

        # ---- IDENTIFY ----
        if current_state == STATE_IDENTIFY:
            draw_identify_screen()
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    current_state   = STATE_DEVICES_FOUND
                    selected_option = 0
                    button_debounce['press'] = True
                    time.sleep(0.5)
            else:
                button_debounce['press'] = False

        # ---- DEVICES FOUND ----
        elif current_state == STATE_DEVICES_FOUND:
            draw_devices_found_screen(selected_option)
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_UP_PIN):
                if not button_debounce.get('up', False):
                    selected_option = (selected_option - 1) % 2
                    button_debounce['up'] = True
                    time.sleep(0.2)
            else:
                button_debounce['up'] = False
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_DOWN_PIN):
                if not button_debounce.get('down', False):
                    selected_option = (selected_option + 1) % 2
                    button_debounce['down'] = True
                    time.sleep(0.2)
            else:
                button_debounce['down'] = False
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    current_state   = STATE_BIOMETRIC_MENU if selected_option == 0 else STATE_IDENTIFY
                    selected_option = 0
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False

        # ---- BIOMETRIC MENU ----
        elif current_state == STATE_BIOMETRIC_MENU:
            draw_biometric_menu_screen(selected_option)
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_UP_PIN):
                if not button_debounce.get('up', False):
                    selected_option = (selected_option - 1) % 2
                    button_debounce['up'] = True
                    time.sleep(0.2)
            else:
                button_debounce['up'] = False
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_DOWN_PIN):
                if not button_debounce.get('down', False):
                    selected_option = (selected_option + 1) % 2
                    button_debounce['down'] = True
                    time.sleep(0.2)
            else:
                button_debounce['down'] = False
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    if selected_option == 0:
                        print("→ ARM attack...")
                        arm_attack_sequence()
                        current_state   = STATE_ARM_SUCCESS
                        selected_option = 0
                    else:
                        print("→ FORMAT attack...")
                        format_attack_sequence()
                        current_state = STATE_FORMAT_SUCCESS
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False

        # ---- ARM SUCCESS ----
        elif current_state == STATE_ARM_SUCCESS:
            draw_arm_success_screen(selected_option)
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    print("→ Rerunning ARM...")
                    arm_attack_sequence()
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False

        # ---- FORMAT SUCCESS ----
        elif current_state == STATE_FORMAT_SUCCESS:
            draw_format_success_screen()

        # ---- SCREENSAVER ----
        elif current_state == STATE_SCREENSAVER:
            img = Image.new("1", (width, height), 1)

            diamond_x += vel[0]
            diamond_y += vel[1]

            if diamond_x <= 0 or diamond_x >= width - bmp_w:
                vel[0] *= -1
            if diamond_y <= 0 or diamond_y >= height - bmp_h:
                vel[1] *= -1

            diamond_x = max(0, min(width - bmp_w, diamond_x))
            diamond_y = max(0, min(height - bmp_h, diamond_y))

            img.paste(bmp, (diamond_x, diamond_y))
            show(img)

        # ---- QR ----
        elif current_state == STATE_QR:
            img  = Image.new("1", (width, height), 1)
            qr_x = (width - 64) // 2
            qr_y = 0
            img.paste(qr, (qr_x, qr_y))
            show(img)
            time.sleep(0.1)

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
    except:
        pass
