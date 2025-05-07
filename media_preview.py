# ==============================
# media_preview.py
# ==============================
import os
import platform
import subprocess
import sys

def open_media(filepath):
    if platform.system() != "Linux":
        print("[!] Media preview is Linux-only.")
        return
    subprocess.call(("xdg-open", filepath))
