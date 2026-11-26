Troubleshooting
===============

Common problems and how to solve them. When reporting an issue on
`GitHub <https://github.com/emanuelemerlo/JD-Xi-Studio/issues>`_, include the operating system,
the JD-Xi Studio version (**Help › About**), the steps that lead to the problem and the session
log: **Log Viewer** (Ctrl+Shift+L) shows it; the files are in ``~/.jdxi_studio/logs``.

Installing and starting
-----------------------

**Windows**
   - **"Windows protected your PC"**: the build is not signed; choose "More info" → "Run anyway".
   - **Missing DLLs**: install the Microsoft Visual C++ Redistributable (x64).
   - **Antivirus blocking**: add JD-Xi Studio to your antivirus exceptions.

**macOS**
   - **Cannot be opened** (the developer cannot be verified): the app is not signed with a
     Developer ID yet. Open it once, then choose **Open Anyway** in System Settings › Privacy &
     Security.
   - **"JD-Xi Studio is damaged and can't be opened"**: remove the download's quarantine flag,
     ``xattr -dr com.apple.quarantine "/Applications/JD-Xi Studio.app"``, and open it again.
   - **Recordings are silent** (USB recorder): allow JD-Xi Studio in System Settings › Privacy &
     Security › Microphone.

**Linux**
   - **The .deb does not install** (missing dependencies): install it with ``sudo apt install
     ./jd-xi-studio_<version>_amd64.deb`` (``apt``, not ``dpkg -i``: apt brings what it needs).
     It needs Ubuntu 22.04 / Debian 12 or later.
   - **MIDI permissions**: add your user to the audio group
     (``sudo usermod -a -G audio $USER``), then log in again.
   - **"MIDI not available" at startup**: the system has no ALSA sequencer, so the editor runs
     Off-line. Load it with ``sudo modprobe snd-seq`` and restart the editor; containers, VMs and
     WSL often lack it.

**Installing with pip**
   - Use Python 3.10 or later, in a fresh virtual environment, to avoid dependency conflicts.

The connection to the JD-Xi
---------------------------

The badge in each window says the state of the connection: **Off-line**, **Verifying the
JD-Xi…**, **connected**, **Unstable connection**. The JD-Xi counts as connected only once it
answers as a JD-Xi.

- **Off-line with the JD-Xi plugged in**: check the USB cable and that the JD-Xi is on, close
  other programs that use its MIDI ports, then choose the ports in
  **JD-Xi › MIDI Configuration…** (Ctrl+Shift+M). On Windows a port held by another program cannot be opened.
- **The badge stays on Verifying**: the ports are open but the JD-Xi does not answer. Switch it
  off and on again; if it persists, reopen **MIDI Configuration…** and choose the ports again.
- **Changes made Off-line**: when the JD-Xi arrives they are given up for what it holds; use
  **Save as file…** in that notice to keep them first.
- **Settings lost on the JD-Xi**: the editor sends sounds to its temporary memory. To keep them on
  the instrument, save the program with **JD-Xi › Save the program…** (the WRITE on the panel).

Playing MIDI files
------------------

- **Notes hang**: press **Panic** in the MIDI Player.
- **Sounds change by themselves during playback**: the file's program changes select other
  sounds. Keep **GM** checked in the event filter (it blocks the General MIDI program changes),
  or **PC** to block them all, and choose the sounds with **Fit to the JD-Xi**.
- **A part is silent**: check its M (mute) and S (solo) buttons; in Fit to the JD-Xi a track
  set to «Not played» is muted.
- **The JD-Xi plays oddly after a file**: switch it off and on again to clear its state.
