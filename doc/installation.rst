.. jdxi-editor documentation master file, created by
   sphinx-quickstart on Sat May 11 10:48:11 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Installation
============

.. note::
   This is the guide of the independent fork https://github.com/emanuelemerlo/JD-Xi-Studio
   (version 0.10.0 beta). The fork publishes Windows builds only for now; on macOS and Linux
   use Method 2 or 3, or build a package yourself. The macOS and Linux packages below are
   produced by ``python -m building.buildsys``.

Welcome to the comprehensive installation guide for **JDXI-Editor**! This guide will walk you through multiple installation methods, from simple pre-built packages to advanced development setups. Choose the method that best suits your needs and technical comfort level.

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

The simplest way to install JDXI-Editor is using our pre-built packages. These include all dependencies and are ready to run immediately.

**macOS Installation**
   Download and install the macOS package:

   .. code-block:: console

      # Download the DMG file from the releases page
      # https://github.com/emanuelemerlo/JD-Xi-Studio/releases
      
      # Mount the DMG file (version may vary; check releases page)
      $ open JD-Xi-Editor-0.9.dmg
      
      # Drag JD-Xi Editor.app to your Applications folder
      # The application will appear in your Applications folder

   **macOS Requirements:**
   - macOS 10.14 (Mojave) or later
   - Intel or Apple Silicon (M1/M2) processor
   - 4GB RAM minimum, 8GB recommended

   **macOS Installation Notes:**
   - The app is notarized for security
   - You may need to allow the app in System Preferences > Security & Privacy
   - The app includes all necessary Qt6 and MIDI libraries

**Windows Installation**
   Download the installer or the portable zip from the releases page
   (https://github.com/emanuelemerlo/JD-Xi-Studio/releases):

   - ``jdxi_editor-<version>_setup_win_x86-64.exe``: run it and follow the wizard (English or
     Italian). It installs for the current user in ``%LOCALAPPDATA%\Programs\jdxi_editor``,
     without administrator rights, and adds a Start menu entry (desktop icon optional).
   - ``JDXI-Editor-<version>-win64-portable.zip``: unzip it to a folder and run
     ``jdxi_editor\jdxi_editor.exe``. Nothing is installed; delete the folder to remove it.

   **Windows Requirements:**
   - Windows 10 or 11 (64-bit)
   - 4GB RAM minimum, 8GB recommended

   **Windows Installation Notes:**
   - Both packages include Python, Qt, the MIDI libraries and FluidSynth; nothing else is needed
   - The files are not signed: if SmartScreen warns, choose "More info" → "Run anyway"
   - Connect the JD-Xi by USB before starting the editor, then choose its MIDI ports in the
     MIDI configuration dialog. Without a JD-Xi the editor opens anyway (offline mode)
   - The interface language is chosen in Help › Preferences › Interface language
     (English, Italiano, or the system's); it applies at the next start

**Linux Installation**
   Download and install the AppImage package:

   .. code-block:: console

      # Download the AppImage from the releases page
      # https://github.com/emanuelemerlo/JD-Xi-Studio/releases
      
      # Make the AppImage executable (version may vary; check releases page)
      $ chmod +x JD-Xi-Editor-0.9-x86_64.AppImage
      
      # Run the application
      $ ./JD-Xi-Editor-0.8-x86_64.AppImage

   **Linux Requirements:**
   - Ubuntu 18.04+ or equivalent distribution
   - 4GB RAM minimum, 8GB recommended
   - FUSE support for AppImage (usually pre-installed)

Method 2: Python Package Installation
=====================================

For users who prefer pip-based installation or want to integrate JDXI-Editor into their Python environment.

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

   2. **Install JDXI-Editor**
      .. code-block:: console

         # Install this fork from GitHub (the JDXI-Editor package on PyPI is
         # the original project, not this fork)
         $ pip install git+https://github.com/emanuelemerlo/JD-Xi-Studio.git

   3. **Run the Application**
      .. code-block:: console

         # Launch JDXI-Editor
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

   **Optional (SoundFont playback):**
   - pyfluidsynth (FluidSynth for playback without hardware)
   - sf2utils (SoundFont preset list extraction)
   - sounddevice (hardware interface selection for FluidSynth)

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
         $ cd JDXI-Editor

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

         # Launch JDXI-Editor
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

For developers who want to contribute to JDXI-Editor or work on advanced features.

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
         $ cd JDXI-Editor
         
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
   2. **Launch JDXI-Editor**: Start the application using your preferred method
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

**Common Installation Issues**

**macOS Issues**
   - **"App is damaged"**: Right-click the app and select "Open" to bypass Gatekeeper
   - **Permission denied**: Check System Preferences > Security & Privacy
   - **MIDI not working**: Ensure your JD-Xi is connected and powered on

**Windows Issues**
   - **Missing DLLs**: Install the Microsoft Visual C++ Redistributable (x64)
   - **"Windows protected your PC"**: the build is not signed; choose "More info" → "Run anyway"
   - **Antivirus blocking**: Add JDXI-Editor to your antivirus exceptions
   - **MIDI not detected**: Check Device Manager for MIDI devices

**Linux Issues**
   - **AppImage won't run**: Install FUSE: ``sudo apt install fuse``
   - **MIDI permissions**: Add your user to the audio group: ``sudo usermod -a -G audio $USER``
   - **"MIDI not available" at startup**: the system has no ALSA sequencer, so the editor
     runs offline (patches can be edited, opened and saved, nothing is sent to the JD-Xi).
     Load it with ``sudo modprobe snd-seq`` and restart the editor; containers, VMs and
     WSL often lack it
   - **Qt issues**: Install Qt5 libraries: ``sudo apt install qt5-default``

**Python Installation Issues**
   - **Permission denied**: Use ``--user`` flag: ``pip install --user git+https://github.com/emanuelemerlo/JD-Xi-Studio.git``
   - **Virtual environment issues**: Ensure you're using Python 3.10 or later
   - **Dependency conflicts**: Use a fresh virtual environment

**MIDI Connection Issues**
   - **No MIDI devices found**: Check USB connection and JD-Xi power
   - **MIDI not responding**: Try different USB ports or cables
   - **Latency issues**: Check your system's audio/MIDI settings

**Performance Issues**
   - **Slow response**: Close other MIDI applications
   - **High CPU usage**: Check for background processes
   - **Memory issues**: Ensure you have at least 4GB RAM available

Getting Help
============

**Documentation**
   - **User Guide**: Complete documentation in the ``doc/`` directory
   - **API Reference**: Auto-generated API documentation
   - **Video Tutorials**: Available on the project's YouTube channel

**Community Support**
   - **GitHub Issues**: Report bugs and request features
   - **Discussions**: Community discussions and Q&A
   - **Discord**: Real-time community chat (if available)

**Professional Support**
   - **Email Support**: Contact the development team
   - **Custom Development**: Request custom features or modifications
   - **Training**: Professional training and workshops

**System Information**
   When reporting issues, please include:
   - Operating system and version
   - Python version (if applicable)
   - JDXI-Editor version
   - JD-Xi firmware version
   - Error messages or logs
   - Steps to reproduce the issue

The JDXI-Editor installation process is designed to be as smooth as possible, with multiple installation methods to suit different user needs and technical comfort levels. Choose the method that works best for you, and don't hesitate to reach out for help if you encounter any issues!


