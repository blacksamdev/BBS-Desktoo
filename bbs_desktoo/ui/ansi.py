# bbs_desktoo/ui/ansi.py
# BBS desktOO — conversion des séquences ANSI en formats Qt.
#
# Un terminal réel colore sa sortie avec des séquences d'échappement
# (ESC[...m). QPlainTextEdit affiche du texte brut, donc sans traitement on
# voit les codes en clair (« [01;32m… »). Ce module parse ces séquences et
# produit des segments (texte, format) que le terminal applique.
#
# Couverture : couleurs 16 (standard + bright), gras, reset. Suffisant pour
# bash, ls --color, git, pip, npm. Les séquences non gérées (curseur, effacement
# d'écran, OSC titres) sont silencieusement retirées pour ne pas polluer.

import re

from PyQt6.QtGui import QTextCharFormat, QColor, QFont

from bbs_desktoo.core.theme import COLORS


# Palette ANSI 16 couleurs, accordée au thème BBS (lisible sur fond sombre).
_ANSI_COLORS = {
    30: "#3A3F47",  # noir (border, lisible)
    31: "#E15561",  # rouge
    32: "#4EC94E",  # vert
    33: "#D4A843",  # jaune
    34: "#5B9BD5",  # bleu
    35: "#CC7ADB",  # magenta
    36: "#4EC9C9",  # cyan
    37: "#FFF8DF",  # blanc (crème BBS)
    90: "#555B63",  # noir clair (gris)
    91: "#FF6B77",  # rouge clair
    92: "#6BE06B",  # vert clair
    93: "#E8C05A",  # jaune clair
    94: "#7AB0E8",  # bleu clair
    95: "#D89AE8",  # magenta clair
    96: "#6BDADA",  # cyan clair
    97: "#FFFFFF",  # blanc vif
}

# Séquence SGR (Select Graphic Rendition) : ESC [ ... m
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

# Autres séquences CSI (curseur, effacement…) SAUF SGR ('m', traité à part).
_CSI_OTHER_RE = re.compile(r"\x1b\[[0-9;?]*[A-DfGhilnpsuJKST]")
_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


def _base_format() -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(COLORS["text_main"]))
    return fmt


def parse_ansi(text: str, carry: QTextCharFormat | None = None
               ) -> tuple[list[tuple[str, QTextCharFormat]], QTextCharFormat]:
    """Découpe `text` en segments (contenu, format) selon les codes ANSI.

    `carry` : format hérité de la fin du fragment précédent (le streaming du
    terminal arrive par morceaux, un code couleur peut courir d'un morceau au
    suivant). Retourne aussi le format courant à reporter au prochain appel.
    """
    # Retire d'abord OSC (titres de fenêtre, ex. ESC]0;...BEL) et CSI non-SGR.
    text = _OSC_RE.sub("", text)
    text = _CSI_OTHER_RE.sub("", text)

    current = QTextCharFormat(carry) if carry is not None else _base_format()
    segments: list[tuple[str, QTextCharFormat]] = []
    pos = 0

    for m in _SGR_RE.finditer(text):
        # Texte avant la séquence -> format courant
        if m.start() > pos:
            segments.append((text[pos:m.start()], QTextCharFormat(current)))
        # Applique les codes de la séquence
        codes = m.group(1)
        current = _apply_codes(current, codes)
        pos = m.end()

    if pos < len(text):
        segments.append((text[pos:], QTextCharFormat(current)))

    return segments, current


def _apply_codes(fmt: QTextCharFormat, codes: str) -> QTextCharFormat:
    fmt = QTextCharFormat(fmt)
    # "ESC[m" vide == reset
    parts = [int(c) for c in codes.split(";") if c != ""] or [0]
    for code in parts:
        if code == 0:
            fmt = _base_format()
        elif code == 1:
            fmt.setFontWeight(QFont.Weight.Bold)
        elif code == 22:
            fmt.setFontWeight(QFont.Weight.Normal)
        elif code in _ANSI_COLORS:
            fmt.setForeground(QColor(_ANSI_COLORS[code]))
        elif code == 39:  # couleur de premier plan par défaut
            fmt.setForeground(QColor(COLORS["text_main"]))
        # Les couleurs de fond (40-47, 100-107) sont ignorées : on garde le
        # fond uniforme du terminal pour rester lisible.
    return fmt
