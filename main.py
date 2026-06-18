#!/usr/bin/env python3
# BBS desktOO — point d'entrée.
#
#   python main.py
#
# IDE natif Linux (PyQt6 + QScintilla), panneau IA agnostique.
# GPL-3.0 — développé par blacksamdev — en hommage à Samuel Bellamy 🏴‍☠️,
# le Prince des Pirates, capitaine du Whydah.

import sys

from bbs_desktoo.app import run

if __name__ == "__main__":
    sys.exit(run())
