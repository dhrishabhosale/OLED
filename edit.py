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

font = ImageFont.load_default()

# =============================
# TEXT CENTER HELPER
# =============================
def center_text(draw, box, text, fill=0):
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x1 + (x2 - x1 - tw) // 2
    ty = y1 + (y2 - y1 - th) // 2
    draw.text((tx, ty), text, font=font, fill=fill)

# =============================
# STATES
# =============================
STATE_IDENTIFY = 0
STATE_DEVICES_FOUND = 1
STATE_BIOMETRIC_MENU = 2
STATE_ARM_SUCCESS = 4
STATE_FORMAT_SUCCESS = 6
STATE_SCREENSAVER = 7
STATE_QR = 8

current_state = STATE_IDENTIFY
selected_option = 0

# =============================
# SCREENSAVER IMAGE
# =============================
try:
    bmp = Image.open("pic.bmp").convert("1")
    bmp.thumbnail((32, 32))
except:
    bmp = Image.new("1", (16, 16), 1)
    d = ImageDraw.Draw(bmp)
    d.polygon([(8, 0), (16, 8), (8, 16), (0, 8)], fill=0)

bmp_w, bmp_h = bmp.size
diamond_x = 10
diamond_y = 10
dx = 2
dy = 2

# =============================
# QR
# =============================
try:
    qr = Image.open("qr.png").convert("1").resize((64, 64))
except:
    qr = Image.new("1", (64, 64), 1)

# =============================
# DISPLAY
# =============================
def show(img):
    disp.ShowImage(disp.getbuffer(img))

# =============================
# BUTTON
# =============================
def draw_button(draw, x, y, w, h, text, selected=False):
    if selected:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=0)
        draw.rectangle((x+1, y+1, x+w-1, y+h-1), outline=1, fill=1)
        center_text(draw, (x, y, x+w, y+h), text, fill=0)
    else:
        draw.rectangle((x, y, x+w, y+h), outline=0, fill=1)
        center_text(draw, (x, y, x+w, y+h), text, fill=0)

# =============================
# SCREENS
# =============================
def draw_identify_screen():
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 15), fill=0)
    center_text(draw, (0, 0, width, 15), "BIOMETRIC ATTACK", fill=1)

    center_text(draw, (0, 20, width, 40), "IDENTIFY")
    center_text(draw, (0, 35, width, 55), "DEVICE")
    center_text(draw, (0, 50, width, 64), "Press [CENTER]")

    show(img)

def draw_devices_found_screen(selected):
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 15), fill=0)
    center_text(draw, (0, 0, width, 15), "DEVICES FOUND", fill=1)

    draw_button(draw, 10, 20, 108, 15, "Biometric Lock", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "Re-scan", selected == 1)

    show(img)

def draw_biometric_menu_screen(selected):
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 15), fill=0)
    center_text(draw, (0, 0, width, 15), "BIOMETRIC LOCK", fill=1)

    draw_button(draw, 10, 20, 108, 15, "ARM", selected == 0)
    draw_button(draw, 10, 40, 108, 15, "FORMAT", selected == 1)

    show(img)

def draw_arm_success_screen():
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 15), fill=0)
    center_text(draw, (0, 0, width, 15), "DISARMED", fill=1)
    center_text(draw, (0, 20, width, 35), "Attack Complete")
    center_text(draw, (0, 45, width, 60), "Press [3] to exit")

    show(img)

def draw_format_success_screen():
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, width, 15), fill=0)
    center_text(draw, (0, 0, width, 15), "FORMAT DONE", fill=1)
    center_text(draw, (0, 25, width, 45), "All users cleared")
    center_text(draw, (0, 45, width, 60), "Press [3] to exit")

    show(img)

# =============================
# MAIN LOOP
# =============================
try:
    while True:

        if current_state == STATE_IDENTIFY:
            draw_identify_screen()

        elif current_state == STATE_DEVICES_FOUND:
            draw_devices_found_screen(selected_option)

        elif current_state == STATE_BIOMETRIC_MENU:
            draw_biometric_menu_screen(selected_option)

        elif current_state == STATE_ARM_SUCCESS:
            draw_arm_success_screen()

        elif current_state == STATE_FORMAT_SUCCESS:
            draw_format_success_screen()

        elif current_state == STATE_SCREENSAVER:
            img = Image.new("1", (width, height), 1)
            diamond_x += dx
            diamond_y += dy

            if diamond_x <= 0 or diamond_x >= width - bmp_w:
                dx *= -1
            if diamond_y <= 0 or diamond_y >= height - bmp_h:
                dy *= -1

            img.paste(bmp, (diamond_x, diamond_y))
            show(img)

        elif current_state == STATE_QR:
            img = Image.new("1", (width, height), 1)
            img.paste(qr, ((width - 64)//2, 0))
            show(img)

        time.sleep(0.05)

except KeyboardInterrupt:
    disp.clear()
    disp.RPI.module_exit()
