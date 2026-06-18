# bbs_desktoo/core/theme.py
# BBS desktOO — palette et feuille de style globale (QSS)
#
# Palette dérivée de l'icône officielle BBS, adaptée à un IDE :
# fond plus profond pour le confort de lecture du code.

COLORS = {
    "bg_deep":    "#16191D",   # fond éditeur / terminal
    "bg_panel":   "#22262B",   # panneaux latéraux (couleur BBS)
    "bg_input":   "#2C3138",   # champs de saisie
    "bg_hover":   "#2A2F36",   # survol
    "accent":     "#E11D2E",   # rouge BBS
    "accent_hi":  "#C4172A",   # rouge survol
    "text_main":  "#FFF8DF",   # crème BBS
    "text_muted": "#8A8F98",   # texte secondaire
    "text_dim":   "#555B63",   # texte tertiaire / placeholders
    "border":     "#3A3F47",   # séparateurs
    "green":      "#4EC94E",   # statut OK
    "yellow":     "#D4A843",   # statut en cours
}


def build_qss() -> str:
    """Retourne la feuille de style globale appliquée à QApplication."""
    c = COLORS
    return f"""
    QMainWindow, QWidget {{
        background: {c['bg_deep']};
        color: {c['text_main']};
        font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
        font-size: 13px;
    }}

    /* ---- Splitters ---- */
    QSplitter::handle {{
        background: {c['border']};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QSplitter::handle:vertical   {{ height: 1px; }}
    QSplitter::handle:hover {{ background: {c['accent']}; }}

    /* ---- Panneaux ---- */
    QTreeView {{
        background: {c['bg_panel']};
        border: none;
        outline: none;
        color: {c['text_muted']};
        font-size: 12px;
    }}
    QTreeView::item {{
        padding: 3px 4px;
        border: none;
    }}
    QTreeView::item:hover {{
        background: {c['bg_hover']};
        color: {c['text_main']};
    }}
    QTreeView::item:selected {{
        background: {c['bg_input']};
        color: {c['text_main']};
    }}

    /* ---- Onglets ---- */
    QTabWidget::pane {{
        border: none;
        background: {c['bg_deep']};
    }}
    QTabBar {{
        background: {c['bg_panel']};
    }}
    QTabBar::tab {{
        background: {c['bg_panel']};
        color: {c['text_muted']};
        padding: 7px 14px;
        border: none;
        border-right: 1px solid {c['border']};
        font-size: 12px;
    }}
    QTabBar::tab:hover {{
        background: {c['bg_hover']};
        color: {c['text_main']};
    }}
    QTabBar::tab:selected {{
        background: {c['bg_deep']};
        color: {c['text_main']};
        border-bottom: 2px solid {c['accent']};
    }}

    /* ---- Terminal / zones texte ---- */
    QPlainTextEdit, QTextEdit {{
        background: {c['bg_deep']};
        color: {c['text_main']};
        border: none;
        selection-background-color: {c['accent']};
        selection-color: #FFFFFF;
    }}

    /* ---- Champs de saisie ---- */
    QLineEdit {{
        background: {c['bg_input']};
        color: {c['text_main']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 5px 8px;
        selection-background-color: {c['accent']};
    }}
    QLineEdit:focus {{ border: 1px solid {c['accent']}; }}

    /* ---- Boutons ---- */
    QPushButton {{
        background: {c['bg_input']};
        color: {c['text_main']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 5px 12px;
        font-size: 12px;
    }}
    QPushButton:hover {{ border: 1px solid {c['text_dim']}; background: {c['bg_hover']}; }}
    QPushButton:pressed {{ background: {c['bg_panel']}; }}

    QPushButton#accent {{
        background: {c['accent']};
        color: #FFFFFF;
        border: none;
        font-weight: 700;
    }}
    QPushButton#accent:hover {{ background: {c['accent_hi']}; }}

    /* ---- ComboBox (sélecteur provider / repo) ---- */
    QComboBox {{
        background: {c['bg_input']};
        color: {c['text_main']};
        border: 1px solid {c['border']};
        border-radius: 5px;
        padding: 4px 8px;
        font-size: 12px;
    }}
    QComboBox:hover {{ border: 1px solid {c['text_dim']}; }}
    QComboBox QAbstractItemView {{
        background: {c['bg_input']};
        color: {c['text_main']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
    }}

    /* ---- Barres de défilement ---- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['text_dim']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['text_dim']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ---- Menu ---- */
    QMenuBar {{
        background: {c['bg_panel']};
        color: {c['text_muted']};
        border-bottom: 1px solid {c['border']};
    }}
    QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
    QMenuBar::item:selected {{ background: {c['bg_hover']}; color: {c['text_main']}; }}
    QMenu {{
        background: {c['bg_input']};
        color: {c['text_main']};
        border: 1px solid {c['border']};
    }}
    QMenu::item:selected {{ background: {c['accent']}; }}

    /* ---- Labels de section ---- */
    QLabel#sectionHeader {{
        color: {c['text_muted']};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        padding: 8px 12px;
    }}
    """
