"""
About JD-Xi Studio: the logo, the version, who made it (this edition and the
original project it is based on), the libraries and the trademark notice.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from jdxi_editor.i18n import tr
from jdxi_editor.project import (
    __display_name__,
    __home_url__,
    __maintainer__,
    __origin_author__,
    __origin_url__,
    release_name,
)
from jdxi_editor.resources import resource_path

ACCENT = "#ff2a1a"  # the JD-Xi's red
STYLE = f"""
QDialog#about {{ background: #121214; }}
QLabel {{ color: #c9cbd1; background: transparent; }}
QLabel a {{ color: {ACCENT}; }}
QFrame#aboutCard {{ background: #1b1c1f; border: 1px solid #2e3036; border-radius: 10px; }}
QLabel#aboutName {{ color: #ffffff; font-size: 22px; font-weight: 800; letter-spacing: 1px; }}
QLabel#aboutVersion {{ color: {ACCENT}; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 13px; }}
QLabel#aboutHead {{ color: {ACCENT}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
QLabel#aboutSmall {{ color: #8a8d94; font-size: 11px; }}
QPushButton {{ background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px;
    padding: 6px 22px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
"""


def _link(url: str, text: str) -> str:
    return f"<a style='color: {ACCENT}; text-decoration: none' href='{url}'>{text}</a>"


def _card(head: str, *labels: QLabel) -> QFrame:
    card = QFrame()
    card.setObjectName("aboutCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 14)
    layout.setSpacing(6)
    title = QLabel(head.upper())
    title.setObjectName("aboutHead")
    layout.addWidget(title)
    for label in labels:
        layout.addWidget(label)
    return card


def _text(html: str, small: bool = False) -> QLabel:
    label = QLabel(html)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setWordWrap(True)
    label.setOpenExternalLinks(True)
    if small:
        label.setObjectName("aboutSmall")
    return label


class UiAboutDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("about")
        self.version_label: Optional[QLabel] = None

    def setup_ui(self, parent: QWidget = None) -> None:
        """Build the dialog (kept as a separate step: the caller then exec()s it)."""
        self.setWindowTitle(tr("About {program}").format(program=__display_name__))
        self.setStyleSheet(STYLE)
        self.setMinimumWidth(640)
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(20)

        # left: the logo
        logo = QLabel()
        pixmap = QPixmap(resource_path("resources/jdxi_studio_logo.png"))
        if pixmap.isNull():  # the drawn mark when the picture is missing
            from jdxi_editor.ui.v2.brand import draw_mark

            pixmap = draw_mark(220)
        logo.setPixmap(
            pixmap.scaled(240, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        # right: who, what, with what
        right = QVBoxLayout()
        right.setSpacing(10)
        name = QLabel(__display_name__)
        name.setObjectName("aboutName")
        self.version_label = QLabel(tr("Version {version}").format(version=release_name()))
        self.version_label.setObjectName("aboutVersion")
        right.addWidget(name)
        right.addWidget(self.version_label)
        right.addWidget(
            _text(tr("An editor and librarian for the Roland JD-Xi synthesizer: every sound, the "
                     "pattern sequencer, the effects and the vocoder, from the computer."))
        )
        right.addWidget(
            _card(
                tr("Authors"),
                _text(
                    tr("{name} — this edition (JD-Xi Studio)").format(
                        name=_link(__home_url__, __maintainer__)
                    )
                ),
                _text(
                    tr("{name} — the original JDXI-Editor, on which it is based").format(
                        name=_link(__origin_url__, __origin_author__)
                    )
                ),
            )
        )
        right.addWidget(
            _card(
                tr("Made with"),
                _text(
                    " · ".join(
                        (
                            _link("https://www.qt.io/", "Qt / PySide6"),
                            _link("https://mido.readthedocs.io/", "Mido"),
                            _link("https://www.music.mcgill.ca/~gary/rtmidi/", "RtMidi"),
                        )
                    )
                    + "<br>"
                    + tr("Source code on {github}, under the {license}.").format(
                        github=_link(__home_url__, "GitHub"),
                        license=_link("https://opensource.org/licenses/MIT", tr("MIT License")),
                    )
                ),
            )
        )
        right.addWidget(
            _text(
                tr("An independent, unofficial tool: not affiliated with, endorsed or sponsored by "
                   "Roland Corporation. Roland and JD-Xi are trademarks of Roland Corporation in the "
                   "United States and/or other countries; all other names belong to their owners."),
                small=True,
            )
        )
        right.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(tr("Close"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        right.addLayout(buttons)
        root.addLayout(right, 1)
