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
selected_option = 0  # Which menu item is selected

# =============================
# SCREENSAVER VARIABLES (ANIMATED FRAMES)
# =============================
animation_frames = []
try:
    # Try to load animation frames from pngframes folder
    import glob
    frame_paths = sorted(glob.glob("pngframes/nite*.bmp"))
    if not frame_paths:
        # Try uploads directory
        frame_paths = sorted(glob.glob("/mnt/user-data/uploads/pngframes/nite*.bmp"))
    
    if frame_paths:
        print(f"Loading {len(frame_paths)} animation frames...")
        for frame_path in frame_paths:
            try:
                frame = Image.open(frame_path).convert("1")
                # Resize to fit display
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
                animation_frames.append(frame)
            except Exception as e:
                print(f"Error loading {frame_path}: {e}")
        print(f"✓ Loaded {len(animation_frames)} frames")
    else:
        print("No animation frames found, using fallback")
except Exception as e:
    print(f"Error loading animation frames: {e}")

# Fallback if no frames loaded
if len(animation_frames) == 0:
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
except:
    try:
        qr = Image.open("/mnt/user-data/uploads/70dadaa2-7feb-4ccb-bafc-5f7551263fbc.png").convert("1")
        qr = qr.resize((64, 64))
    except Exception as e:
        print(f"Warning: QR code not found, using placeholder pattern")
        qr = Image.new("1", (64, 64), 1)
        draw_qr = ImageDraw.Draw(qr)
        for i in range(0, 64, 8):
            draw_qr.line([(i, 0), (i, 64)], fill=0)
            draw_qr.line([(0, i), (64, i)], fill=0)
        for corner in [(0,0), (56,0), (0,56)]:
            x, y = corner
            draw_qr.rectangle((x, y, x+8, y+8), outline=0)
            draw_qr.rectangle((x+2, y+2, x+6, y+6), fill=0)

# =============================
# HELPER FUNCTIONS
# =============================
def show(img):
    """Display image on OLED screen"""
    try:
        disp.ShowImage(disp.getbuffer(img))
    except Exception as e:
        print(f"Error displaying image: {e}")

def draw_button(draw, x, y, w, h, text, selected=False):
    """Draw a button - filled if selected, outline if not"""
    if selected:
        # Selected - filled
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=0)
        draw.rectangle((x+1, y+1, x+w-1, y+h-1), outline=1, fill=1)
        draw.text((x+4, y+3), text, font=font, fill=0)
    else:
        # Not selected - outline only
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=1)
        draw.text((x+4, y+3), text, font=font, fill=0)

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
        # STATE: SCREENSAVER (ANIMATED FRAMES)
        # =============================
        elif current_state == STATE_SCREENSAVER:
            # Display current frame
            img = Image.new("1", (width, height), 1)
            
            # Show current animation frame
            if animation_frames:
                img.paste(animation_frames[current_frame], (0, 0))
            
            show(img)
            
            # Advance to next frame
            current_frame = (current_frame + 1) % len(animation_frames)
            
            # Frame rate control (adjust for smooth animation)
            time.sleep(0.05)  # ~20 FPS
        
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
