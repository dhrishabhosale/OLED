#!/usr/bin/python3
# -*- coding:utf-8 -*-

import traceback
import glob
from PIL import Image, ImageDraw, ImageFont, ImageOps
import SH1106
import config
import time
import subprocess
import random
import os

# =============================
# INITIALIZE DISPLAY (ONCE!)
# =============================
try:
    disp = SH1106.SH1106()
    disp.Init()
    disp.clear()
    
    print("\r1.3inch OLED")
    print("***play animation")

    # ---- ANIMATION PART ----
    frames = sorted(glob.glob("images/nite*.bmp"))

    if not frames:
        print("No animation frames found!")
    else:
        for frame_file in frames:
            niteAnim = Image.new('1', (disp.width, disp.height), 255)
            bmp = Image.open(frame_file).resize((128, 64))
            bmp = ImageOps.invert(bmp)
            niteAnim.paste(bmp, (0, 5))
            disp.ShowImage(disp.getbuffer(niteAnim))
            time.sleep(0.00000001)
    
    disp.clear()
    niteTxt = Image.new('1', (disp.width, disp.height), "WHITE")
    draw = ImageDraw.Draw(niteTxt)
    font10 = ImageFont.truetype('Monocraft.ttf', 20)
    draw.text((0, 24), 'CRYPTONITE', font=font10, fill=0)
    disp.ShowImage(disp.getbuffer(niteTxt))
    time.sleep(3)
    disp.clear()

except Exception as e:
    print(f"Error initializing display: {e}")
    exit(1)

width = disp.width
height = disp.height

# Use default font
try:
    font = ImageFont.load_default()
except:
    font = None

# =============================
# SCREEN STATES
# =============================
STATE_IDENTIFY = 0
STATE_DEVICES_FOUND = 1
STATE_BIOMETRIC_MENU = 2
STATE_ARM_LOADING = 3
STATE_ARM_SUCCESS = 4
STATE_FORMAT_LOADING = 5
STATE_FORMAT_SUCCESS = 6
STATE_SCREENSAVER = 7
STATE_QR = 8

current_state = STATE_IDENTIFY
selected_option = 0

# =============================
# SCREENSAVER VARIABLES
# =============================
try:
    bmp = Image.open("pic.bmp").convert("1")
    max_size = (32, 32)
    if bmp.size[0] > max_size[0] or bmp.size[1] > max_size[1]:
        bmp.thumbnail(max_size, Image.Resampling.LANCZOS)
    bmp_w, bmp_h = bmp.size
except:
    try:
        bmp = Image.open("/mnt/user-data/uploads/pic.bmp").convert("1")
        max_size = (32, 32)
        if bmp.size[0] > max_size[0] or bmp.size[1] > max_size[1]:
            bmp.thumbnail(max_size, Image.Resampling.LANCZOS)
        bmp_w, bmp_h = bmp.size
    except:
        bmp = Image.new("1", (16, 16), 1)
        draw_bmp = ImageDraw.Draw(bmp)
        draw_bmp.polygon([(8, 0), (16, 8), (8, 16), (0, 8)], outline=0, fill=0)
        bmp_w, bmp_h = bmp.size

diamond_x = 10
diamond_y = 10
dx = 2
dy = 2

# =============================
# QR IMAGE
# =============================
try:
    qr = Image.open("qr.png").convert("1")
    qr = qr.resize((64, 64))
except:
    qr = Image.new("1", (64, 64), 1)

# =============================
# HELPER FUNCTIONS
# =============================
def show(img):
    try:
        disp.ShowImage(disp.getbuffer(img))
    except Exception as e:
        print(f"Error displaying image: {e}")

# ✅ FIXED BUTTON TEXT ALIGNMENT HERE
def draw_button(draw, x, y, w, h, text, selected=False):
    """Draw a button - filled if selected, outline if not"""

    # Calculate centered position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = x + (w - text_w) // 2
    text_y = y + (h - text_h) // 2

    if selected:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=0)
        draw.rectangle((x+1, y+1, x+w-1, y+h-1), outline=1, fill=1)
        draw.text((text_x, text_y), text, font=font, fill=0)
    else:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=1)
        draw.text((text_x, text_y), text, font=font, fill=0)

# =============================
# (Everything below is EXACTLY your original code)
# =============================



def arch_boot_animation(lines, final_message):
    """Arch Linux style boot animation with loading bar and cat"""
    # Phase 1: Boot messages
    for i, line in enumerate(lines):
        img = Image.new("1", (width, height), 1)
        draw = ImageDraw.Draw(img)
        
        # Show previous lines
        y_pos = 5
        for j in range(max(0, i-4), i+1):
            if y_pos < height - 10:
                draw.text((5, y_pos), lines[j], font=font, fill=0)
                y_pos += 12
        
        show(img)
        time.sleep(0.3)
    
    time.sleep(0.3)
    
    # Phase 2: Loading bar with cat
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    draw.text((20, 5), "Processing...", font=font, fill=0)
    show(img)
    time.sleep(0.3)
    
    for progress in range(0, 101, 3):
        img = Image.new("1", (width, height), 1)
        draw = ImageDraw.Draw(img)
        
        draw.text((30, 5), "Processing", font=font, fill=0)
        draw.text((100, 5), f"{progress}%", font=font, fill=0)
        
        # Loading bar track
        track_y = 25
        draw.rectangle((10, track_y, 118, track_y + 8), outline=0)
        draw.rectangle((11, track_y + 1, 117, track_y + 7), outline=0)
        
        # Cat position
        cat_x = 12 + int((104 * progress) / 100)
        
        # Fill behind cat
        if progress > 0:
            fill_width = int((106 * progress) / 100)
            draw.rectangle((12, track_y + 2, 12 + fill_width, track_y + 6), fill=0)
        
        # Draw running cat (alternating animation)
        frame = (progress // 5) % 2
        
        if frame == 0:
            # Running pose 1
            draw.rectangle((cat_x, track_y - 5, cat_x + 8, track_y), fill=0)
            draw.rectangle((cat_x + 6, track_y - 8, cat_x + 10, track_y - 4), fill=0)
            draw.polygon([(cat_x + 6, track_y - 8), (cat_x + 7, track_y - 10), (cat_x + 8, track_y - 8)], fill=0)
            draw.polygon([(cat_x + 8, track_y - 8), (cat_x + 9, track_y - 10), (cat_x + 10, track_y - 8)], fill=0)
            draw.line([(cat_x, track_y - 4), (cat_x - 2, track_y - 7)], fill=0)
            draw.line([(cat_x + 7, track_y), (cat_x + 7, track_y + 2)], fill=0)
            draw.line([(cat_x + 2, track_y), (cat_x + 1, track_y + 2)], fill=0)
        else:
            # Running pose 2
            draw.rectangle((cat_x, track_y - 4, cat_x + 8, track_y), fill=0)
            draw.rectangle((cat_x + 6, track_y - 7, cat_x + 10, track_y - 3), fill=0)
            draw.polygon([(cat_x + 6, track_y - 7), (cat_x + 7, track_y - 9), (cat_x + 8, track_y - 7)], fill=0)
            draw.polygon([(cat_x + 8, track_y - 7), (cat_x + 9, track_y - 9), (cat_x + 10, track_y - 7)], fill=0)
            draw.line([(cat_x, track_y - 3), (cat_x - 2, track_y - 5)], fill=0)
            draw.line([(cat_x + 4, track_y), (cat_x + 4, track_y + 2)], fill=0)
            draw.line([(cat_x + 5, track_y), (cat_x + 5, track_y + 2)], fill=0)
        
        # Status text
        draw.text((25, 40), "Please wait...", font=font, fill=0)
        
        show(img)
        time.sleep(0.05)
    
    # Phase 3: Success message
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Draw box
    draw.rectangle((10, 15, 118, 50), outline=0)
    draw.rectangle((12, 17, 116, 48), outline=0)
    
    # Split final message into lines if needed
    words = final_message.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + word) < 15:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    
    # Center text
    y_start = 25 - (len(lines) * 6)
    for i, line in enumerate(lines):
        draw.text((20, y_start + i * 12), line, font=font, fill=0)
    
    show(img)
    time.sleep(2)

# =============================
# SCREEN DRAWING FUNCTIONS
# =============================
def draw_identify_screen():
    """Initial screen - IDENTIFY DEVICE"""
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((15, 3), "BIOMETRIC ATTACK", font=font, fill=1)
    
    # Main message
    draw.text((20, 25), "IDENTIFY", font=font, fill=0)
    draw.text((25, 37), "DEVICE", font=font, fill=0)
    
    # Instruction
    draw.text((10, 52), "Press [CENTER]", font=font, fill=0)
    
    show(img)

def draw_devices_found_screen(selected):
    """Devices found screen with two options"""
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((20, 3), "DEVICES FOUND", font=font, fill=1)
    
    # Options
    draw_button(draw, 10, 20, 108, 15, "Biometric Lock", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "Re-scan", selected == 1)
    
    show(img)

def draw_biometric_menu_screen(selected):
    """Biometric lock menu - ARM or FORMAT"""
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((10, 3), "BIOMETRIC LOCK", font=font, fill=1)
    
    # Options
    draw_button(draw, 10, 20, 108, 15, "ARM", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "FORMAT", selected == 1)
    
    show(img)

def arm_attack_sequence():
    """Execute ARM attack with boot animation"""
    boot_lines = [
        "[ OK ] Starting ARM",
        "[ OK ] Loading exploit",
        "[ OK ] Bypassing auth",
        "[ OK ] Injecting code",
        "[ ** ] Executing..."
    ]
    
    arch_boot_animation(boot_lines, "DOOR OPEN")
    
    # Launch door.py if it exists
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
        print("door.py not found - continuing without external script")
    
    # Show DISARMED message
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    draw.rectangle((10, 10, 118, 40), outline=0)
    draw.rectangle((12, 12, 116, 38), outline=0)
    draw.text((30, 18), "DISARMED", font=font, fill=0)
    
    show(img)
    time.sleep(1.5)

def draw_arm_success_screen(selected):
    """After ARM success - show rerun or back options"""
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((30, 3), "DISARMED", font=font, fill=1)
    
    # Status
    draw.text((15, 20), "Attack Complete", font=font, fill=0)
    
    # Options
    draw_button(draw, 10, 35, 108, 12, "Rerun Attack", selected == 0)
    
    # Instruction at bottom
    draw.text((15, 52), "Press [3] to exit", font=font, fill=0)
    
    show(img)

def format_attack_sequence():
    """Execute FORMAT attack with boot animation"""
    boot_lines = [
        "[ OK ] Starting FORMAT",
        "[ OK ] Accessing DB",
        "[ OK ] Clearing users",
        "[ ** ] Wiping data...",
        "[ OK ] Cleanup done"
    ]
    
    arch_boot_animation(boot_lines, "FORMAT COMPLETE")

def draw_format_success_screen():
    """After FORMAT success"""
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Title
    draw.rectangle((0, 0, width-1, 15), outline=0, fill=0)
    draw.text((20, 3), "FORMAT DONE", font=font, fill=1)
    
    # Status
    draw.text((10, 25), "All users cleared", font=font, fill=0)
    
    # Instruction
    draw.text((15, 45), "Press [3] to exit", font=font, fill=0)
    
    show(img)

# =============================
# MAIN LOOP
# =============================
print("Starting Biometric Attack Interface...")
print("Controls:")
print("  UP/DOWN: Navigate menu")
print("  CENTER: Select")
print("  KEY1 (1): Screensaver")
print("  KEY2 (2): QR Code")
print("  KEY3 (3): Return to identify screen")

try:
    last_time = time.time()
    frame_delay = 0.05
    button_debounce = {}
    
    while True:
        # Frame timing
        current_time = time.time()
        if current_time - last_time < frame_delay:
            time.sleep(frame_delay - (current_time - last_time))
        last_time = time.time()
        
        # KEY1 - Screensaver mode
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN):
            if current_state != STATE_SCREENSAVER:
                current_state = STATE_SCREENSAVER
                print("→ Switched to SCREENSAVER mode")
            time.sleep(0.3)
        
        # KEY2 - QR Code mode
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN):
            if current_state != STATE_QR:
                current_state = STATE_QR
                print("→ Switched to QR CODE mode")
            time.sleep(0.3)
        
        # KEY3 always returns to identify screen
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY3_PIN):
            current_state = STATE_IDENTIFY
            selected_option = 0
            print("→ Returned to IDENTIFY screen")
            time.sleep(0.3)
        
        # =============================
        # STATE: IDENTIFY DEVICE
        # =============================
        if current_state == STATE_IDENTIFY:
            draw_identify_screen()
            
            # Center press to continue
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    print("→ Scanning for devices...")
                    current_state = STATE_DEVICES_FOUND
                    selected_option = 0
                    button_debounce['press'] = True
                    time.sleep(0.5)
            else:
                button_debounce['press'] = False
        
        # =============================
        # STATE: DEVICES FOUND
        # =============================
        elif current_state == STATE_DEVICES_FOUND:
            draw_devices_found_screen(selected_option)
            
            # Navigation
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
            
            # Selection
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    if selected_option == 0:
                        # Biometric Lock
                        print("→ Entering BIOMETRIC LOCK menu")
                        current_state = STATE_BIOMETRIC_MENU
                        selected_option = 0
                    else:
                        # Re-scan
                        print("→ Re-scanning...")
                        current_state = STATE_IDENTIFY
                        selected_option = 0
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False
        
        # =============================
        # STATE: BIOMETRIC MENU
        # =============================
        elif current_state == STATE_BIOMETRIC_MENU:
            draw_biometric_menu_screen(selected_option)
            
            # Navigation
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
            
            # Selection
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    if selected_option == 0:
                        # ARM
                        print("→ Executing ARM attack...")
                        arm_attack_sequence()
                        current_state = STATE_ARM_SUCCESS
                        selected_option = 0
                    else:
                        # FORMAT
                        print("→ Executing FORMAT attack...")
                        format_attack_sequence()
                        current_state = STATE_FORMAT_SUCCESS
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False
        
        # =============================
        # STATE: ARM SUCCESS
        # =============================
        elif current_state == STATE_ARM_SUCCESS:
            draw_arm_success_screen(selected_option)
            
            # Selection (only rerun available, KEY3 for exit)
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN):
                if not button_debounce.get('press', False):
                    print("→ Rerunning ARM attack...")
                    arm_attack_sequence()
                    button_debounce['press'] = True
                    time.sleep(0.3)
            else:
                button_debounce['press'] = False
        
        # =============================
        # STATE: FORMAT SUCCESS
        # =============================
        elif current_state == STATE_FORMAT_SUCCESS:
            draw_format_success_screen()
            # Just wait for KEY3 to exit
        
        # =============================
        # STATE: SCREENSAVER
        # =============================
        elif current_state == STATE_SCREENSAVER:
            img = Image.new("1", (width, height), 1)
            
            # Update diamond position
            diamond_x += dx
            diamond_y += dy
            
            # Bounce off edges
            if diamond_x <= 0 or diamond_x >= width - bmp_w:
                dx *= -1
            if diamond_y <= 0 or diamond_y >= height - bmp_h:
                dy *= -1
            
            # Ensure diamond stays in bounds
            diamond_x = max(0, min(width - bmp_w, diamond_x))
            diamond_y = max(0, min(height - bmp_h, diamond_y))
            
            # Paste diamond image
            img.paste(bmp, (diamond_x, diamond_y))
            show(img)
        
        # =============================
        # STATE: QR DISPLAY
        # =============================
        elif current_state == STATE_QR:
            img = Image.new("1", (width, height), 1)
            
            # Center QR code
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
