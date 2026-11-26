.. jdxi-editor documentation master file, created by
   sphinx-quickstart on Sat May 11 10:48:11 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Installation
============

.. note::
   This is the guide of JD-Xi Studio, https://github.com/emanuelemerlo/JD-Xi-Studio. Each
   release has a Windows installer and portable app, macOS disk images and a Linux .deb
   (Method 1); on other systems use Method 2 or 3.

Welcome to the comprehensive installation guide for **JD-Xi Studio**! This guide will walk you through multiple installation methods, from simple pre-built packages to advanced development setups. Choose the method that best suits your needs and technical comfort level.

System Requirements
===================

**Minimum System Requirements**
   - **Operating System**: macOS 10.14+, Windows 10+, or Linux (Ubuntu 18.04+)
   - **Python**: Version 3.10 or higher (for source installation)
   - **Memory**: 4GB RAM minimum, 8GB recommended
   - **Storage**: 500MB available space for application and presets
   - **MIDI Interface**: USB connection to Roland JD-Xi synthesizer
   - **Display**: 1024x768 minimum resolution, 1920x1080 recommended

**Hardware Requirements**
   - **Roland JD-Xi Synthesizer**: Any firmware version supported
   - **USB Cable**: USB-B to USB-A or USB-C cable for MIDI communication
   - **Audio Interface**: Optional, for audio monitoring and recording
   - **MIDI Controller**: Optional, for enhanced performance control

**Software Dependencies**
   - **Qt6 Framework**: Included in pre-built packages
   - **RtMidi Library**: For MIDI communication (included)
   - **Python Libraries**: PySide6, mido, python-rtmidi (for source installation)

Installation Methods
====================

**Method 1: Pre-Built Packages (Recommended)**
   The easiest way to get started with JDXI-Editor.

**Method 2: Python Package Installation**
   For users who prefer pip-based installation.

**Method 3: Source Code Installation**
   For developers and advanced users who want the latest features.

**Method 4: Development Setup**
   For contributors and developers working on JDXI-Editor.

Method 1: Pre-Built Packages (Recommended)
==========================================

The simplest way to install JD-Xi Studio is using our pre-built packages. These include all dependencies and are ready to run immediately.

**macOS Installation**
   Download the disk image from the releases page
   (https://github.com/emanuelemerlo/JD-Xi-Studio/releases), open it and drag
   **JD-Xi Studio** onto **Applications**:

   - ``JD-Xi-Studio-<version>-macos-arm64.dmg`` for Apple silicon (M1 and later);
   - ``JD-Xi-Studio-<version>-macos-x86_64.dmg`` for an Intel Mac (it also runs on Apple
     silicon, through Rosetta).

   **macOS Requirements:**
   - macOS 11 (Big Sur) or later.

   **macOS Installation Notes:**
   - The app is not signed with a Developer ID yet, so macOS stops it the first time. Open it
     once, then in System Settings › Privacy & Security choose **Open Anyway** (on macOS 14 and
     earlier, right-click the app and choose **Open** also works). After that it opens as usual.
   - If macOS says the app «is damaged and can't be opened», remove the download's quarantine
     flag: ``xattr -dr com.apple.quarantine "/Applications/JD-Xi Studio.app"``.
   - The first time the USB recorder records, macOS asks to let JD-Xi Studio use the audio input
     (the JD-Xi's audio over USB): allow it, or the recordings are silent.
   - The app includes Python, Qt and the MIDI and audio libraries; nothing else is needed.

**Windows Installation**
   Download the installer or the portable zip from the releases page
   (https://github.com/emanuelemerlo/JD-Xi-Studio/releases):

   - ``JD-Xi-Studio-<version>-setup-win64.exe``: run it and follow the wizard (English or
     Italian). It installs for the current user in ``%LOCALAPPDATA%\Programs\jdxi_editor``,
     without administrator rights, and adds a Start menu entry (desktop icon optional).
   - ``JD-Xi-Studio-<version>-win64-portable.zip``: unzip it to a folder and run
     ``JD-Xi-Studio\JD-Xi-Studio.exe``. Nothing is installed; delete the folder to remove it.

   **Windows Requirements:**
   - Windows 10 or 11 (64-bit)
   - 4GB RAM minimum, 8GB recommended

   **Windows Installation Notes:**

   - Both packages include Python, Qt and the MIDI libraries; nothing else is needed
   - The files are not signed: if SmartScreen warns, choose "More info" → "Run anyway"
   - Connect the JD-Xi by USB before starting the editor, then choose its MIDI ports in the
     MIDI configuration dialog. Without a JD-Xi the editor opens anyway (Off-line, with a badge in every window)
   - The interface language is chosen in File › Preferences › Interface language
     (English, Italiano, or the system's); it applies at the next start

**Linux Installation**
   Download ``jd-xi-studio_<version>_amd64.deb`` from the releases page and install it
   (Debian, Ubuntu, Linux Mint and the like, 64-bit PC):

   .. code-block:: console

      $ sudo apt install ./jd-xi-studio_<version>_amd64.deb

   It installs in ``/opt/jd-xi-studio`` and adds **JD-Xi Studio** to the applications menu and the
   ``jd-xi-studio`` command; ``sudo apt remove jd-xi-studio`` removes it (settings and patches
   stay). apt installs the few system libraries it needs (ALSA, the X11/Wayland ones Qt uses).

   **Linux Requirements:**
   - Ubuntu 22.04, Debian 12, Linux Mint 21 or later (64-bit PC). Other distributions: the
     one-command install of the README (``install.sh``) or the Python package.
   - To use the JD-Xi over USB your user must be in the ``audio`` group on some systems
     (``sudo usermod -a -G audio $USER``, then log in again).

Method 2: Python Package Installation
=====================================

For users who prefer pip-based installation or want to integrate JD-Xi Studio into their Python environment.

**Prerequisites**
   Ensure you have Python 3.10 or higher installed:

   .. code-block:: console

      # Check Python version
      $ python --version
      # Should show Python 3.10 or higher
      
      # Check pip version
      $ pip --version
      # Should show pip 20.0 or higher

**Installation Steps**

   1. **Create a Virtual Environment (Recommended)**
      .. code-block:: console

         # Create virtual environment
         $ python -m venv jdxi-editor-env
         
         # Activate virtual environment
         # On macOS/Linux:
         $ source jdxi-editor-env/bin/activate
         # On Windows:
         $ jdxi-editor-env\Scripts\activate

   2. **Install JD-Xi Studio**
      .. code-block:: console

         # Install this fork from GitHub (the JD-Xi Studio package on PyPI is
         # the original project, not this fork)
         $ pip install git+https://github.com/emanuelemerlo/JD-Xi-Studio.git

   3. **Run the Application**
      .. code-block:: console

         # Launch JD-Xi Studio
         $ python -m jdxi_editor.main
         
         # Or use the command-line interface
         $ jdxi_manager

**Dependencies**
   The following packages will be automatically installed:
   - PySide6 (Qt6 framework)
   - python-rtmidi (MIDI communication)
   - mido (MIDI message handling)
   - Pillow (image processing)
   - QtAwesome (icons)
   - Additional dependencies as needed

Method 3: Source Code Installation
==================================

For users who want to install from source code, modify the application, or get the latest development features.

**Prerequisites**
   - Python 3.10 or higher
   - Git (for cloning the repository)
   - Development tools for your platform

**Installation Steps**

   1. **Clone the Repository**
      .. code-block:: console

         # Clone the repository
         $ git clone https://github.com/emanuelemerlo/JD-Xi-Studio.git
         $ cd JD-Xi Studio

   2. **Create Virtual Environment**
      .. code-block:: console

         # Create virtual environment
         $ python -m venv venv
         
         # Activate virtual environment
         # On macOS/Linux:
         $ source venv/bin/activate
         # On Windows:
         $ venv\Scripts\activate

   3. **Install Dependencies**
      .. code-block:: console

         # Upgrade pip
         $ python -m pip install --upgrade pip
         
         # Install requirements
         $ pip install -r requirements.txt

   4. **Install in Development Mode**
      .. code-block:: console

         # Install in editable mode
         $ pip install -e .

   5. **Run the Application**
      .. code-block:: console

         # Launch JD-Xi Studio
         $ python -m jdxi_editor.main

**Source Code Structure**
   The source code is organized as follows:
   - ``jdxi_editor/``: Main application code
   - ``doc/``: Documentation source files
   - ``tests/``: Test suite
   - ``resources/``: Application resources and assets
   - ``requirements.txt``: Python dependencies
   - ``pyproject.toml``: Project configuration

Method 4: Development Setup
===========================

For developers who want to contribute to JD-Xi Studio or work on advanced features.

**Prerequisites**
   - Python 3.10 or higher
   - Git
   - Development tools for your platform
   - Optional: IDE (VS Code, PyCharm, etc.)

**Development Installation**

   1. **Fork and Clone Repository**
      .. code-block:: console

         # Fork the repository on GitHub, then clone your fork
         $ git clone https://github.com/YOUR_USERNAME/JDXI-Editor.git
         $ cd JD-Xi Studio
         
         # Add upstream remote
         $ git remote add upstream https://github.com/emanuelemerlo/JD-Xi-Studio.git

   2. **Set Up Development Environment**
      .. code-block:: console

         # Create virtual environment
         $ python -m venv venv
         $ source venv/bin/activate  # On Windows: venv\Scripts\activate
         
         # Install development dependencies
         $ pip install -r requirements.txt
         $ pip install -r requirements-dev.txt  # If available
         
         # Install pre-commit hooks (if available)
         $ pre-commit install

   3. **Run Tests**
      .. code-block:: console

         # Run the test suite (install the dev extra first: pip install -e ".[dev]")
         $ pytest

         # Run with coverage
         $ pytest --cov=jdxi_editor

         # Tests that need local files or play in real time
         $ pytest -m slow

         # Tests against a connected JD-Xi, on the real MIDI ports
         $ pytest -m hardware

      The default run needs no MIDI hardware or driver: ``tests/conftest.py`` replaces
      rtmidi's ports with in-memory ones that show a port named "JD-Xi", so the editor
      connects to it as if a JD-Xi were plugged in. ``pytest -m hardware`` (or
      ``JDXI_TEST_REAL_MIDI=1``) keeps the real ports.

   4. **Build Documentation**
      .. code-block:: console

         # Install documentation dependencies
         $ pip install sphinx sphinx-rtd-theme sphinx-autoapi
         
         # Build documentation
         $ cd doc
         $ sphinx-build -b html . _build/html

**Development Tools**
   - **Code Formatting**: Black, isort
   - **Linting**: flake8, mypy
   - **Testing**: pytest
   - **Documentation**: Sphinx
   - **Type Checking**: mypy

Post-Installation Setup
=======================

**First Launch**
   1. **Connect Your JD-Xi**: Use a USB cable to connect your synthesizer to your computer
   2. **Launch JD-Xi Studio**: Start the application using your preferred method
   3. **MIDI Configuration**: The app will attempt to auto-connect to your JD-Xi
   4. **Verify Connection**: Check that MIDI indicators show active input/output

**MIDI Configuration**
   If auto-connection fails:
   1. **Open MIDI Settings**: Go to the MIDI configuration dialog
   2. **Select Ports**: Choose the correct input and output ports for your JD-Xi
   3. **Test Connection**: Verify that MIDI communication is working
   4. **Save Settings**: Your preferences will be remembered for future launches

**Initial Setup**
   1. **Load a Preset**: Start with a factory preset to familiarize yourself with the interface
   2. **Explore Editors**: Try different editor tabs to understand the capabilities
   3. **Test Controls**: Use the virtual keyboard to test parameter changes
   4. **Save Your Work**: Create and save your first custom preset

Troubleshooting
===============

Installation problems and their solutions are in :doc:`troubleshooting`.

The JD-Xi Studio installation process is designed to be as smooth as possible, with multiple installation methods to suit different user needs and technical comfort levels. Choose the method that works best for you, and don't hesitate to reach out for help if you encounter any issues!


