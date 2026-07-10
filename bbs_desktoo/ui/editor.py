# bbs_desktoo/ui/editor.py
# BBS desktOO — éditeur de code basé sur QScintilla.
#
# Coloration syntaxique selon l'extension, numéros de ligne, ligne courante
# surlignée, thème BBS appliqué au lexer.

import os

from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython,
    QsciLexerJavaScript,
    QsciLexerBash,
    QsciLexerCPP,
    QsciLexerMarkdown,
    QsciLexerHTML,
    QsciLexerJSON,
)
from PyQt6.QtGui import QColor, QFont

from bbs_desktoo.core.theme import COLORS


# Association extension -> classe de lexer QScintilla
_LEXERS = {
    ".py":   QsciLexerPython,
    ".js":   QsciLexerJavaScript,
    ".jsx":  QsciLexerJavaScript,
    ".ts":   QsciLexerJavaScript,
    ".sh":   QsciLexerBash,
    ".bash": QsciLexerBash,
    ".c":    QsciLexerCPP,
    ".h":    QsciLexerCPP,
    ".cpp":  QsciLexerCPP,
    ".hpp":  QsciLexerCPP,
    ".md":   QsciLexerMarkdown,
    ".html": QsciLexerHTML,
    ".htm":  QsciLexerHTML,
    ".json": QsciLexerJSON,
}


class BBSEditor(QsciScintilla):
    """Éditeur mono-fichier. Un onglet de l'éditeur central en instancie un."""

    # Émis quand la taille de police change par zoom (pour persistance globale)
    from PyQt6.QtCore import pyqtSignal as _sig
    font_size_changed = _sig(int)

    MIN_SIZE = 7
    MAX_SIZE = 32

    def __init__(self, font_size: int = 11, parent=None):
        super().__init__(parent)
        self.file_path: str | None = None
        self._font_size = max(self.MIN_SIZE, min(self.MAX_SIZE, font_size))
        self._font = QFont("JetBrains Mono", self._font_size)
        self._font.setFixedPitch(True)
        self.setFont(self._font)
        self._configure()

    # ------------------------------------------------------------------ #
    def set_font_size(self, size: int) -> None:
        """Change la taille de police de l'éditeur (et de son lexer)."""
        size = max(self.MIN_SIZE, min(self.MAX_SIZE, size))
        if size == self._font_size:
            return
        self._font_size = size
        self._font.setPointSize(size)
        self.setFont(self._font)
        lexer = self.lexer()
        if lexer is not None:
            lexer.setFont(self._font)
        self.font_size_changed.emit(size)

    def font_size(self) -> int:
        return self._font_size

    def wheelEvent(self, event):
        # Ctrl + molette : zoom du code
        from PyQt6.QtCore import Qt as _Qt
        if event.modifiers() & _Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_font_size(self._font_size + (1 if delta > 0 else -1))
            event.accept()
            return
        super().wheelEvent(event)

    # ------------------------------------------------------------------ #
    def _configure(self) -> None:
        c = COLORS

        # Couleurs de base de la zone d'édition
        self.setPaper(QColor(c["bg_deep"]))
        self.setColor(QColor(c["text_main"]))

        # --- Marge des numéros de ligne ---
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginsBackgroundColor(QColor(c["bg_deep"]))
        self.setMarginsForegroundColor(QColor(c["text_dim"]))

        # --- Ligne courante surlignée ---
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#1E2228"))
        self.setCaretForegroundColor(QColor(c["accent"]))
        self.setCaretWidth(2)

        # --- Sélection ---
        self.setSelectionBackgroundColor(QColor(c["accent"]))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))

        # --- Indentation ---
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setIndentationGuides(True)

        # --- Confort ---
        self.setUtf8(True)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor(c["bg_input"]))
        self.setMatchedBraceForegroundColor(QColor(c["accent"]))

    # ------------------------------------------------------------------ #
    def _apply_lexer_theme(self, lexer) -> None:
        """Applique la palette BBS au lexer (fond, défaut, commentaires, chaînes)."""
        c = COLORS
        lexer.setDefaultPaper(QColor(c["bg_deep"]))
        lexer.setDefaultColor(QColor(c["text_main"]))
        lexer.setFont(self._font)
        lexer.setPaper(QColor(c["bg_deep"]))  # fond uniforme sur tous les styles

        # Palette commune BBS, éclaircie pour le fond noir (toutes >= 4.5 WCAG AA)
        KW   = "#6FB3E0"  # mots-clés (bleu clair)
        STR  = "#7BD88F"  # chaînes (vert clair)
        CMT  = "#8A919C"  # commentaires (gris clair, lisible)
        NUM  = "#E0C060"  # nombres (jaune doux)
        FUNC = "#82C7F5"  # fonctions (bleu vif)
        CLS  = "#5CCFE6"  # classes / types (cyan)
        OP   = "#F0A868"  # opérateurs / variables (orange clair)
        TXT  = c["text_main"]

        from PyQt6.Qsci import (
            QsciLexerBash, QsciLexerJavaScript, QsciLexerCPP,
            QsciLexerJSON, QsciLexerHTML, QsciLexerMarkdown,
        )

        if isinstance(lexer, QsciLexerPython):
            for st in (lexer.DoubleQuotedString, lexer.SingleQuotedString,
                       lexer.TripleDoubleQuotedString, lexer.TripleSingleQuotedString):
                lexer.setColor(QColor(STR), st)
            lexer.setColor(QColor(KW),  lexer.Keyword)
            lexer.setColor(QColor(CMT), lexer.Comment)
            lexer.setColor(QColor(CMT), lexer.CommentBlock)
            lexer.setColor(QColor(FUNC), lexer.FunctionMethodName)
            lexer.setColor(QColor(CLS),  lexer.ClassName)
            lexer.setColor(QColor(NUM), lexer.Number)
            lexer.setColor(QColor(OP),  lexer.Decorator)

        elif isinstance(lexer, QsciLexerBash):
            lexer.setColor(QColor(TXT),  lexer.Default)
            lexer.setColor(QColor(KW),   lexer.Keyword)
            lexer.setColor(QColor(CMT),  lexer.Comment)
            lexer.setColor(QColor(NUM),  lexer.Number)
            lexer.setColor(QColor(STR),  lexer.DoubleQuotedString)
            lexer.setColor(QColor(STR),  lexer.SingleQuotedString)
            lexer.setColor(QColor(OP),   lexer.Operator)
            lexer.setColor(QColor(TXT),  lexer.Identifier)
            lexer.setColor(QColor(OP),   lexer.Scalar)             # $var
            lexer.setColor(QColor(OP),   lexer.ParameterExpansion) # ${...}
            lexer.setColor(QColor(FUNC), lexer.Backticks)

        elif isinstance(lexer, QsciLexerJavaScript):
            lexer.setColor(QColor(TXT),  lexer.Default)
            lexer.setColor(QColor(KW),   lexer.Keyword)
            lexer.setColor(QColor(CMT),  lexer.Comment)
            lexer.setColor(QColor(CMT),  lexer.CommentLine)
            lexer.setColor(QColor(CMT),  lexer.CommentDoc)
            lexer.setColor(QColor(NUM),  lexer.Number)
            lexer.setColor(QColor(STR),  lexer.DoubleQuotedString)
            lexer.setColor(QColor(STR),  lexer.SingleQuotedString)
            lexer.setColor(QColor(OP),   lexer.Operator)
            lexer.setColor(QColor(CLS),  lexer.GlobalClass)

        elif isinstance(lexer, QsciLexerCPP):
            lexer.setColor(QColor(TXT),  lexer.Default)
            lexer.setColor(QColor(KW),   lexer.Keyword)
            lexer.setColor(QColor(CMT),  lexer.Comment)
            lexer.setColor(QColor(CMT),  lexer.CommentLine)
            lexer.setColor(QColor(CMT),  lexer.CommentDoc)
            lexer.setColor(QColor(NUM),  lexer.Number)
            lexer.setColor(QColor(STR),  lexer.DoubleQuotedString)
            lexer.setColor(QColor(STR),  lexer.SingleQuotedString)
            lexer.setColor(QColor(OP),   lexer.Operator)
            lexer.setColor(QColor(CLS),  lexer.GlobalClass)
            lexer.setColor(QColor(OP),   lexer.PreProcessor)

        elif isinstance(lexer, QsciLexerJSON):
            lexer.setColor(QColor(FUNC), lexer.Property)
            lexer.setColor(QColor(STR),  lexer.String)
            lexer.setColor(QColor(NUM),  lexer.Number)
            lexer.setColor(QColor(KW),   lexer.Keyword)

        elif isinstance(lexer, QsciLexerMarkdown):
            lexer.setColor(QColor(TXT), lexer.Default)

        elif isinstance(lexer, QsciLexerHTML):
            lexer.setColor(QColor(KW),  lexer.Tag)
            lexer.setColor(QColor(OP),  lexer.Attribute)
            lexer.setColor(QColor(STR), lexer.HTMLDoubleQuotedString)
            lexer.setColor(QColor(STR), lexer.HTMLSingleQuotedString)
            lexer.setColor(QColor(CMT), lexer.HTMLComment)

    # ------------------------------------------------------------------ #
    def load_file(self, path: str) -> None:
        """Charge un fichier dans l'éditeur et applique le lexer adéquat."""
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            self.setText(fh.read())
        self.file_path = path

        ext = os.path.splitext(path)[1].lower()
        lexer_cls = _LEXERS.get(ext)
        if lexer_cls is not None:
            lexer = lexer_cls(self)
            self._apply_lexer_theme(lexer)
            self.setLexer(lexer)
        else:
            self.setLexer(None)
            self.setColor(QColor(COLORS["text_main"]))
            self.setPaper(QColor(COLORS["bg_deep"]))

    def save_file(self, path: str | None = None) -> str:
        """Sauvegarde le contenu. Retourne le chemin écrit."""
        target = path or self.file_path
        if target is None:
            raise ValueError("Aucun chemin de fichier associé à cet éditeur.")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(self.text())
        self.file_path = target
        return target
