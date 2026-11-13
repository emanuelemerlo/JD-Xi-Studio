"""
Main entry point for the JD-Xi Editor application.

This module sets up the application environment, including logging, MIDI message listening,
and application window initialization. It also manages the application's lifecycle,
from initialization to event loop execution.

Functions:
    midi_callback(msg): Callback function for handling incoming MIDI messages.

    listen_midi(port_name, callback): Listens for MIDI messages on the specified port
    and triggers the provided callback function.

    setup_logging(): Configures logging for the application, including console and file
     logging with rotation.

    main(): Main entry point to initialize and run the JD-Xi Editor application,
    set up the window, and handle MIDI message listening.

"""

import logging
import os
import platform
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    # Run as a file (python jdxi_editor/main.py, VS Code's "Run Python File"):
    # use this checkout's package, not another installed copy, and do not let
    # the jdxi_editor folder shadow top-level modules (log, utils, resources...)
    _here = Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != _here]
    sys.path.insert(0, str(_here.parent))

from decologr import setup_logging
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QIcon, QPixmap, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSplashScreen,
    QVBoxLayout,
)

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.i18n import DEFAULT_LANGUAGE, install_qt_translators, set_language, tr
from jdxi_editor.log.message import log_message
from jdxi_editor.project import __data_name__, __organization_name__, __program__, __version__
from jdxi_editor.resources import resource_path
from jdxi_editor.ui.style import JDXiUIDimensions
from jdxi_editor.ui.widgets.digital.title import DigitalTitle
from jdxi_editor.ui.widgets.indicator.startup_sequencer import StartupSequencer
from jdxi_editor.ui.widgets.editor.helper import create_icon_label_with_pixmap
from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument
from jdxi_editor.utils.profiling_decorator import profiling_decorator

os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts=false"


def load_translations(app: QApplication) -> bool:
    """Translate the interface into the language chosen in Preferences.

    jdxi_editor.i18n.tr() reads jdxi_editor/i18n/jdxi_editor_<lang>.qm; this
    also installs Qt's own catalogue so standard buttons and file dialogs
    match. Returns True if a language other than English is in use.
    """
    language = set_language()
    install_qt_translators(app)
    app.setProperty("jdxi_language", language)
    return language != DEFAULT_LANGUAGE


@profiling_decorator()  # Profile is logged and printed when main() returns (after you close the app)
def main() -> None:
    """Main entry point for the JD-Xi Editor application."""
    try:
        # --- Set up logging first
        # JD-Xi Studio's own settings and folder: the original program's copied once
        from jdxi_editor.migrate import migrate

        moved = migrate()
        settings = QSettings(__organization_name__, __program__)
        # the logs go to ~/.jdxi_studio/logs/jdxi_studio-<date>-<time>.log, kept two weeks
        from jdxi_editor.log_files import LOG_KEEP_DAYS, apply_log_level, prune_logs, saved_level

        pruned = prune_logs()
        logger = setup_logging(use_rich=False, project_name=__data_name__)
        apply_log_level(saved_level(settings), logger)  # Preferences > Logs > level
        if pruned:
            logger.info(f"Deleted {pruned} log files older than {LOG_KEEP_DAYS} days")
        if moved["settings"] or moved["files"]:
            logger.info(f"Copied the settings ({moved['settings']}) and files ({moved['files']}) of JDXI-Editor")

        # --- Create application
        app = QApplication(sys.argv)

        from jdxi_editor.ui.widgets.digital.base import load_lcd_font

        load_lcd_font()

        # --- Interface language (Preferences > Language, or the system's)
        load_translations(app)

        # --- Set application metadata
        app.setApplicationName(__program__)
        app.setApplicationVersion(__version__)
        app.setOrganizationName(__organization_name__)
        app.setStyleSheet(
            """
            QTabWidget::tab-bar {
                alignment: center;
            }
        """
        )

        logger.debug("Application initialized")

        # --- Set application icon
        icon_locations = [
            # Installed package, app bundle or repository checkout
            Path(resource_path(os.path.join("resources", "jdxi_icon.png"))),
        ]

        icon_found = False
        for icon_path in icon_locations:
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
                log_message(f"Loaded icon from {icon_path}")
                icon_found = True
                break

        if not icon_found:
            logging.warning(
                f"Icon not found in any of: {[str(p) for p in icon_locations]}"
            )
            # --- Create address fallback icon only for windows, not macOS
            if platform.system() == "Windows":
                icon = QIcon()
                pixmap = QPixmap(128, 128)
                pixmap.fill(QColor("#2897B7"))  # Use the app's theme color
                icon.addPixmap(pixmap)
                app.setWindowIcon(icon)
                log_message("Using fallback icon")

        # --- JD-Xi Studio's own mark on the windows (the exe keeps its icon)
        try:
            from jdxi_editor.ui.v2.brand import icon as studio_icon

            app.setWindowIcon(studio_icon())
        except Exception:  # the mark is a nicety
            pass

        splash, progress_bar, status_label = setup_splash_screen(app)

        # --- Update splash screen with initial progress
        status_label.setText(tr("Initializing MIDI subsystem…"))
        progress_bar.setValue(10)
        app.processEvents()

        # --- Create window and pass splash screen components
        window = JDXiInstrument(
            splash=splash, progress_bar=progress_bar, status_label=status_label
        )

        # --- Finalize splash screen (every step lit)
        progress_bar.setValue(100)
        app.processEvents()
        splash.finish(window)
        window.show()

        # --- Start event loop
        return app.exec()

    except Exception as ex:
        logging.exception(f"Fatal error {ex} occurred")
        raise


def setup_splash_screen(
    app: QApplication,
) -> tuple[QSplashScreen, StartupSequencer, DigitalTitle]:
    """Setup and digital a professional application splash screen with rotating status text.

    Returns:
        tuple: (splash_screen, progress_bar, status_label) for updating progress
    """
    splash = QSplashScreen()
    # Need to use the screen center to digital the splash screen
    # In Qt 6, QApplication.desktop() was removed, use QScreen instead
    screen = app.primaryScreen()
    if screen:
        screen_geometry = screen.availableGeometry()
        screen_center = screen_geometry.center()
        splash.move(
            int(screen_center.x() - JDXiUIDimensions.SPLASH.WIDTH / 2),
            int(screen_center.y() - JDXiUIDimensions.SPLASH.HEIGHT / 2),
        )
    splash.setWindowFlags(
        Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    )
    splash.setFixedSize(JDXiUIDimensions.SPLASH.WIDTH, JDXiUIDimensions.SPLASH.HEIGHT)

    splash.setStyleSheet(
        """
        QSplashScreen { background-color: #111111; border: 1px solid #2c2c2c; }
        QLabel#TitleLabel { color: #f3f3f3; font-size: 28px; font-weight: 600; letter-spacing: 1px; }
        QLabel#SubtitleLabel { color: #bbbbbb; font-size: 14px; }
        QLabel#StatusLabel { color: #88ccff; font-size: 18px; font-style: italic; font-weight: 500; }
        QLabel#CreditLabel { color: #888888; font-size: 10px; }
        QLabel#NoticeLabel { color: #7d8088; font-size: 10px; }
        QFrame#Card { 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1c1c1c, stop:1 #0f0f0f);
            border-radius: 14px; border: 1px solid #2a2a2a; 
        }
        QFrame#StartupSequencer { background: transparent; }
    """
    )

    root = QVBoxLayout(splash)
    root.setContentsMargins(20, 20, 20, 20)
    root.setSpacing(10)

    # --- Content container (so we can overlay the title on top)
    content = QFrame()
    content.setObjectName("Card")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(28, 24, 28, 18)
    content_layout.setSpacing(14)

    # --- JD-Xi Studio's mark on the left; name, origin and trademark notice on the right
    # (its own mark and name: an independent edition of JDXI-Editor, not to be confused with it)
    from jdxi_editor.project import __display_name__
    from jdxi_editor.ui.v2.brand import draw_mark, origin_line, title_font

    side = min(JDXiUIDimensions.SPLASH.IMAGE_WIDTH, JDXiUIDimensions.SPLASH.IMAGE_HEIGHT, 168)
    logo = create_icon_label_with_pixmap(draw_mark(side))

    title = QLabel(__display_name__)
    title.setObjectName("TitleLabel")
    title.setFont(title_font(34))
    title.setStyleSheet("color: #f3f3f3; background: transparent;")
    origin = QLabel(origin_line())
    origin.setObjectName("SubtitleLabel")
    origin.setStyleSheet("color: #a3a6ad; font-size: 14px; background: transparent;")

    notice = QLabel(
        tr("An independent, unofficial tool: not affiliated with, endorsed or sponsored by "
           "Roland Corporation. Roland and JD-Xi are trademarks of Roland Corporation in the "
           "United States and/or other countries; all other names belong to their owners.")
    )
    notice.setObjectName("NoticeLabel")
    notice.setWordWrap(True)

    from jdxi_editor.project import release_name

    version = QLabel(tr("Version {version}").format(version=release_name()))
    version.setStyleSheet(
        "color: #ff2a1a; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 13px;"
        " background: transparent;"
    )

    # the name, its origin and the version, beside the mark, centred on it
    side_layout = QVBoxLayout()
    side_layout.setContentsMargins(0, 0, 0, 0)
    side_layout.setSpacing(6)
    side_layout.addStretch()
    side_layout.addWidget(title)
    side_layout.addWidget(origin)
    side_layout.addSpacing(6)
    side_layout.addWidget(version)
    side_layout.addStretch()

    header_layout = QHBoxLayout()
    header_layout.setSpacing(24)
    header_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
    header_layout.addLayout(side_layout, 1)
    content_layout.addLayout(header_layout)
    content_layout.addStretch(1)

    # --- 16 step startup sequencer, then what is starting, on the display, the card's width
    progress_bar = StartupSequencer()
    content_layout.addWidget(progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
    status_label = DigitalTitle("Starting...")
    status_label.setObjectName("StatusLabel")
    status_label.setMinimumWidth(0)
    status_label.setSizePolicy(QSizePolicy.Policy.Expanding, status_label.sizePolicy().verticalPolicy())
    content_layout.addWidget(status_label)

    # --- the trademark notice, small, above the credits
    content_layout.addWidget(notice)

    # --- Footer credits
    from jdxi_editor.project import __home_url__

    credits = QLabel(  # name, origin and version are at the top already
        tr("{home}  •  MIT licence").format(home=__home_url__.replace("https://", ""))
    )
    credits.setObjectName("CreditLabel")
    credits.setAlignment(Qt.AlignLeft)
    content_layout.addWidget(credits)

    root.addWidget(content)

    splash.show()
    splash.raise_()
    splash.activateWindow()

    # Return splash screen components for updating progress
    return splash, progress_bar, status_label


if __name__ == "__main__":
    try:
        # Profiling only on request (JDXI_PROFILE=1): main() is profiled by its
        # decorator, and a second profiler, or a debugger's, cannot run with it
        exit_code = main()
        sys.exit(exit_code)

    except Exception as ex:
        print(f"Application crashed: {str(ex)}")  # Fallback if logging fails
        logging.exception("Application crashed")
        sys.exit(1)
