"""
The new interface (1.0): editors built for a desktop screen.

Principles, for every screen:

1. Every parameter of the Parameter Guide / MIDI Implementation has a control
   (tests check it).
2. Each control shows what it does to the sound: graphs for filter, envelopes
   and LFO, pictures for waveforms; knobs only where a picture adds nothing.
3. The information is on screen: range, unit and a short explanation from the
   Parameter Guide for the parameter under the pointer, and which settings it
   depends on.
4. The manual is the reference: names, groups and order as on the JD-Xi
   display; where the instrument cannot do something, the screen says so.

The MIDI side (sending, receiving, presets, .syx) is the one of the existing
editors: these classes only replace the widgets.
"""
