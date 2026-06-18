# bbs_desktoo/ui/terminal.py
# BBS desktOO — terminal intégré sur PTY réel.
#
# Contrairement à un QProcess sur pipes, on alloue un vrai pseudo-terminal
# (pty.openpty) et on lance bash dessus comme terminal de contrôle. Résultat :
# sudo, ssh, vim, les prompts de mot de passe et les programmes interactifs
# fonctionnent DANS desktOO — sudo demande son mot de passe ici, plus dans la
# console de lancement.
#
# La sortie est lue via QSocketNotifier sur le descripteur maître et rendue en
# couleur (parseur ANSI). La saisie se fait dans le champ du bas ; chaque ligne
# est écrite sur le PTY (qui se charge de l'écho).

import os
import pty
import fcntl
import termios
import struct
import signal
import subprocess
import re

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QLabel
from PyQt6.QtCore import Qt, QSocketNotifier
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

from bbs_desktoo.core.theme import COLORS
from bbs_desktoo.ui.ansi import parse_ansi


# Détection d'un prompt de mot de passe (sudo, ssh, passphrase…) pour masquer
# la saisie. On teste la fin de la sortie courante.
_PW_PROMPT_RE = re.compile(
    r"(\[sudo\]\s*)?(mot de passe|password|passphrase)\b[^\n]*[:：]\s*$",
    re.IGNORECASE,
)


class BBSTerminal(QWidget):
    """Terminal bash sur PTY réel (supporte sudo et les programmes interactifs)."""

    def __init__(self, cwd: str | None = None, parent=None):
        super().__init__(parent)
        self.cwd = cwd or os.path.expanduser("~")
        self._ansi_carry = None
        self.master_fd: int | None = None
        self.proc: subprocess.Popen | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Zone de sortie
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        mono = QFont("JetBrains Mono", 10)
        mono.setFixedPitch(True)
        self.output.setFont(mono)
        layout.addWidget(self.output)

        # Ligne de saisie
        input_row = QWidget(self)
        row_layout = QHBoxLayout(input_row)
        row_layout.setContentsMargins(10, 4, 10, 6)
        row_layout.setSpacing(6)
        self.prompt_label = QLabel("$", input_row)
        self.prompt_label.setStyleSheet(
            f"color: {COLORS['accent']}; font-weight: 700; font-family: 'JetBrains Mono';"
        )
        self.input = QLineEdit(input_row)
        self.input.setFont(mono)
        self.input.setPlaceholderText("commande…")
        self.input.returnPressed.connect(self._run_input)
        row_layout.addWidget(self.prompt_label)
        row_layout.addWidget(self.input)
        layout.addWidget(input_row)

        # Historique
        self._history: list[str] = []
        self._hist_idx = 0

        self._start_pty()

    # ------------------------------------------------------------------ #
    def _start_pty(self) -> None:
        """Lance bash sur un PTY réel."""
        self.master_fd, slave_fd = pty.openpty()

        # Taille initiale du terminal (lignes, colonnes)
        winsize = struct.pack("HHHH", 40, 140, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

        def _preexec():
            # Nouvelle session + PTY esclave comme terminal de contrôle
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        env = dict(os.environ)
        env["TERM"] = "xterm-256color"

        try:
            self.proc = subprocess.Popen(
                ["bash", "-i"],
                stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                preexec_fn=_preexec, env=env, cwd=self.cwd,
                close_fds=True,
            )
        finally:
            os.close(slave_fd)  # le parent n'a plus besoin de l'esclave

        # Lecture asynchrone de la sortie du PTY
        self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Type.Read, self)
        self.notifier.activated.connect(self._read_output)

        self._append(f"[BBS desktOO] terminal prêt — {self.cwd}\n")

    # ------------------------------------------------------------------ #
    def _read_output(self) -> None:
        if self.master_fd is None:
            return
        try:
            data = os.read(self.master_fd, 8192)
        except OSError:
            data = b""
        if not data:
            # bash terminé / PTY fermé
            self.notifier.setEnabled(False)
            return
        text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "")
        self._append(text)
        self._update_password_mode()

    def _update_password_mode(self) -> None:
        """Masque la saisie si la sortie se termine par un prompt de mot de passe."""
        # On regarde la dernière ligne non vide affichée.
        tail = self.output.toPlainText()[-200:]
        last_line = tail.splitlines()[-1] if tail.splitlines() else ""
        is_password = bool(_PW_PROMPT_RE.search(last_line))
        if is_password and self.input.echoMode() != QLineEdit.EchoMode.Password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
            self.prompt_label.setText("🔒")
            self.input.setPlaceholderText("mot de passe (masqué)…")
        elif not is_password and self.input.echoMode() != QLineEdit.EchoMode.Normal:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.prompt_label.setText("$")
            self.input.setPlaceholderText("commande…")

    # ------------------------------------------------------------------ #
    def set_cwd(self, path: str) -> None:
        if os.path.isdir(path):
            self.cwd = path
            self.send_command(f"cd {self._quote(path)}")

    def send_command(self, command: str) -> None:
        """Écrit une commande sur le PTY (le PTY se charge de l'écho).

        Point d'entrée de l'injection IA -> terminal. La confirmation a déjà
        eu lieu côté CommandCard.
        """
        if self.master_fd is not None:
            os.write(self.master_fd, (command + "\n").encode("utf-8"))

    # ------------------------------------------------------------------ #
    def _run_input(self) -> None:
        cmd = self.input.text()
        # En mode mot de passe : on envoie sans historiser ni rien afficher.
        if self.input.echoMode() == QLineEdit.EchoMode.Password:
            self.send_command(cmd)
            self.input.clear()
            return
        if not cmd.strip():
            self.send_command("")
            self.input.clear()
            return
        self._history.append(cmd)
        self._hist_idx = len(self._history)
        self.send_command(cmd)
        self.input.clear()

    def _append(self, text: str) -> None:
        """Insère du texte en interprétant les séquences ANSI (couleurs)."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        segments, self._ansi_carry = parse_ansi(text, self._ansi_carry)
        for content, fmt in segments:
            cursor.setCharFormat(fmt)
            cursor.insertText(content)
        self.output.setTextCursor(cursor)
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def _append_plain(self, text: str) -> None:
        """Message interne desktOO, sans interprétation ANSI."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(COLORS["text_muted"]))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event):
        if self.input.hasFocus() and self._history:
            if event.key() == Qt.Key.Key_Up:
                self._hist_idx = max(0, self._hist_idx - 1)
                self.input.setText(self._history[self._hist_idx])
                return
            if event.key() == Qt.Key.Key_Down:
                self._hist_idx = min(len(self._history), self._hist_idx + 1)
                self.input.setText(
                    self._history[self._hist_idx] if self._hist_idx < len(self._history) else ""
                )
                return
        super().keyPressEvent(event)

    @staticmethod
    def _quote(path: str) -> str:
        return "'" + path.replace("'", "'\\''") + "'"

    # ------------------------------------------------------------------ #
    def shutdown(self) -> None:
        """Termine bash et ferme le PTY proprement."""
        if hasattr(self, "notifier"):
            self.notifier.setEnabled(False)
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
