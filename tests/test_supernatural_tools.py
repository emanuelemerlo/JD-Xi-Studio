"""The SuperNATURAL tools of the Digital editors: link partials, copy / paste /
swap, randomize, the PCM wave browser, «take from A / B», the envelope loop."""

from __future__ import annotations

import random

import pytest
from PySide6.QtCore import QEvent, QSettings
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.v2 import partial_tools as pt
from jdxi_editor.ui.v2 import wave_browser as wb


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def dispose(editor) -> None:
    """Gone for good: nothing queued to send, no timers left for the next tests."""
    editor._pending.clear()
    editor._send_timer.stop()
    editor.history.mark_saved()
    editor.close()
    editor.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def digital(app):
    from jdxi_editor.ui.v2.digital import DigitalToneEditor

    editor = DigitalToneEditor()
    for n in (1, 2):  # partials 1 and 2 on, as read from the JD-Xi: nothing to undo
        pv = editor.pv(f"PARTIAL{n}_SWITCH")
        pv.blockSignals(True)
        pv.setValue(1)
        pv.blockSignals(False)
    yield editor
    pt.clear_clip()
    dispose(editor)


@pytest.fixture
def digital2(app):
    from jdxi_editor.ui.v2.digital import Digital2ToneEditor

    editor = Digital2ToneEditor()
    yield editor
    dispose(editor)


def values(editor, name):
    return [editor.partial(name, p).value() for p in range(3)]


# --------------------------------------------------------------- link partials
def test_linked_edits_go_to_the_partials_that_are_on_in_one_step(digital):
    digital.link_button.setChecked(True)
    digital.partial("FILTER_CUTOFF", 0).setValue(80)
    assert values(digital, "FILTER_CUTOFF") == [80, 80, 0]  # partial 3 is off
    digital.partial("FILTER_CUTOFF", 0).setValue(90)  # the same gesture, a moment later
    assert values(digital, "FILTER_CUTOFF") == [90, 90, 0]
    assert len(digital.history._undo) == 1
    digital.history.undo()
    assert values(digital, "FILTER_CUTOFF") == [0, 0, 0]
    digital.history.redo()
    assert values(digital, "FILTER_CUTOFF") == [90, 90, 0]


def test_the_oscillator_stays_each_partials_own(digital):
    digital.link_button.setChecked(True)
    for name, value in (("OSC_WAVE", 3), ("OSC_PITCH", 7), ("WAVE_NUMBER", 36), ("OSC_DETUNE", -10)):
        digital.partial(name, 1).setValue(value)
        assert values(digital, name)[0] == 0, name
    digital.partial("AMP_ENV_ATTACK_TIME", 1).setValue(50)
    assert values(digital, "AMP_ENV_ATTACK_TIME")[:2] == [50, 50]


def test_values_from_the_jdxi_are_not_linked(digital):
    digital.link_button.setChecked(True)
    pv = digital.partial("FILTER_RESONANCE", 0)
    pv.blockSignals(True)  # as values read from the JD-Xi arrive
    pv.setValue(40)
    pv.blockSignals(False)
    assert values(digital, "FILTER_RESONANCE") == [40, 0, 0]


def test_off_by_default_and_undo_redo_do_not_spread(digital):
    digital.partial("LFO_RATE", 0).setValue(30)
    assert values(digital, "LFO_RATE") == [30, 0, 0]
    digital.link_button.setChecked(True)
    digital.history.undo()
    digital.history.redo()
    assert values(digital, "LFO_RATE") == [30, 0, 0]


# --------------------------------------------------------------- copy / paste / swap
def test_copy_a_section_and_paste_it_on_digital_2(digital, digital2):
    digital.partial("FILTER_CUTOFF", 1).setValue(64)
    digital.partial("FILTER_MODE", 1).setValue(2)
    clip = pt.copy(digital, 1, "FILTER")
    assert "partial 2" in clip.describe() and "Filter" in clip.describe()
    assert pt.paste(digital2, 0) == 2
    assert digital2.partial("FILTER_CUTOFF", 0).value() == 64
    assert digital2.partial("AMP_LEVEL", 0).value() == 0  # only the filter
    assert len(digital2.history._undo) == 1


def test_paste_with_the_link_on_sets_only_the_partial_chosen(digital):
    digital.partial("AMP_LEVEL", 0).setValue(90)
    pt.copy(digital, 0)
    digital.link_button.setChecked(True)
    pt.paste(digital, 2)
    assert values(digital, "AMP_LEVEL") == [90, 0, 90]


def test_swap_partials_in_one_step(digital):
    digital.partial("AMP_LEVEL", 0).setValue(100)
    digital.partial("AMP_LEVEL", 1).setValue(20)
    steps = len(digital.history._undo)
    pt.swap(digital, 0, 1)
    assert values(digital, "AMP_LEVEL")[:2] == [20, 100]
    assert len(digital.history._undo) == steps + 1
    digital.history.undo()
    assert values(digital, "AMP_LEVEL")[:2] == [100, 20]
    digital.history.redo()
    assert values(digital, "AMP_LEVEL")[:2] == [20, 100]


def test_the_menu_acts_on_the_partial_shown(digital):
    digital.show_partial(1)
    digital._fill_partial_menu()
    texts = [a.text() for a in digital.partial_menu.actions()]
    assert texts[0] == "Copy partial 2"
    assert "Swap with partial 1" in texts and "Swap with partial 3" in texts
    paste = next(a for a in digital.partial_menu.actions() if a.text().startswith("Paste"))
    assert not paste.isEnabled()  # nothing copied yet


# --------------------------------------------------------------- randomize
def test_randomize_a_section_little_keeps_the_waveforms(digital):
    digital.partial("OSC_WAVE", 0).setValue(2)
    before = {name: digital.partial(name, 0).value() for name in pt.PARTIAL_PARAMS}
    pt.randomize(digital, "section", "little", partial=0, section="FILTER", rng=random.Random(3))
    after = {name: digital.partial(name, 0).value() for name in pt.PARTIAL_PARAMS}
    changed = {n for n in pt.PARTIAL_PARAMS if before[n] != after[n]}
    assert changed and changed <= set(pt.SECTIONS["FILTER"]) - pt.STEADY_BELOW_MUCH
    assert after["FILTER_CUTOFF"] >= pt.NO_SILENT_FILTER


def test_randomize_much_stays_audible_and_is_one_step(digital):
    rng = random.Random(7)
    for _ in range(5):
        pt.randomize(digital, "tone", "much", rng=rng)
        assert all(level >= pt.MIN_LEVEL for level in values(digital, "AMP_LEVEL"))
    assert len(digital.history._undo) == 5
    assert digital.pv("TONE_CATEGORY").value() == 0 and digital.pv("PARTIAL3_SWITCH").value() == 0


def test_randomize_dialog(digital):
    from jdxi_editor.ui.v2.randomize_dialog import RandomizeDialog

    dialog = RandomizeDialog(digital, 0)
    dialog.partial_radio.setChecked(True)
    assert dialog.chosen_scope() == "partial" and dialog.chosen_amount() == "medium"
    assert dialog.randomize() > 0
    after = {n: digital.partial(n, 0).value() for n in pt.PARTIAL_PARAMS}
    dialog.undo()
    assert not digital.history._undo
    digital.history.redo()
    assert {n: digital.partial(n, 0).value() for n in pt.PARTIAL_PARAMS} == after


# --------------------------------------------------------------- PCM waves
def test_every_wave_has_one_family():
    numbers = [n for family in wb.FAMILIES.values() for n in family]
    assert sorted(numbers) == list(range(1, 161))


def test_search_by_name_family_or_number():
    assert wb.matches(36, "bell") and wb.matches(36, "36") and not wb.matches(36, "saw")
    assert wb.matches(134, "bass") and wb.matches(1, "calc saw")


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)


def test_trying_waves_plays_them_and_ok_is_one_step(digital, settings):
    played = []
    pv = digital.partial("WAVE_NUMBER", 0)
    browser = wb.WaveBrowser(pv, play_note=lambda n, v: played.append((n, v)), history=digital.history,
                             settings=settings)
    browser.try_box.setChecked(True)
    browser.search.setText("bell")
    browser.waves.setCurrentRow(1)
    assert pv.value() == browser.current_number() and played[-1] == (60, 100)
    browser.waves.setCurrentRow(2)
    assert not digital.history._undo  # the tries are not steps
    chosen = browser.current_number()
    browser.accept()
    assert pv.value() == chosen and len(digital.history._undo) == 1
    assert played[-1] == (60, 0)  # the last note stopped


def test_cancel_puts_the_wave_back(digital, settings):
    pv = digital.partial("WAVE_NUMBER", 0)
    pv.setValue(5)
    browser = wb.WaveBrowser(pv, play_note=lambda n, v: None, history=digital.history, settings=settings)
    browser.try_box.setChecked(True)
    browser.waves.setCurrentRow(10)
    browser.reject()
    assert pv.value() == 5


def test_favourites_are_remembered(digital, settings):
    pv = digital.partial("WAVE_NUMBER", 0)
    pv.setValue(36)
    browser = wb.WaveBrowser(pv, settings=settings)
    browser.toggle_star()
    assert wb.favourites(settings) == {36}
    browser.families.setCurrentRow(1)  # ★ Favourites
    assert browser.waves.count() == 1


# --------------------------------------------------------------- take from A / B
def test_take_sections_from_a_photo(digital):
    from jdxi_editor.ui.v2 import ab_compare as ab

    digital.partial("FILTER_CUTOFF", 0).setValue(100)
    digital.partial("AMP_LEVEL", 0).setValue(90)
    photo = ab.take_snapshot(digital, "B", "local")
    digital.history.revert()
    digital.history._undo.clear()
    sections = {name: count for name, _specs, count in ab.differing_sections(digital, photo)}
    assert sections == {"FILTER P1": 1, "AMP P1": 1}
    assert ab.take_sections(digital, photo, ["FILTER P1"]) == 1
    assert digital.partial("FILTER_CUTOFF", 0).value() == 100 and digital.partial("AMP_LEVEL", 0).value() == 0
    assert len(digital.history._undo) == 1


# --------------------------------------------------------------- envelope loop
def test_the_envelope_shows_its_loop(digital):
    from jdxi_editor.ui.v2.widgets import EnvelopeView

    loop, note = digital.pv("ENVELOPE_LOOP_MODE"), digital.pv("ENVELOPE_LOOP_SYNC_NOTE")
    view = EnvelopeView("#eb5757", digital.info_hub, *(digital.partial(n, 0) for n in (
        "AMP_ENV_ATTACK_TIME", "AMP_ENV_DECAY_TIME", "AMP_ENV_SUSTAIN_LEVEL", "AMP_ENV_RELEASE_TIME")),
        loop_mode=loop, loop_note=note)
    assert view.loop_text() == ""
    loop.setValue(1)
    assert view.loop_text() == "loop"
    loop.setValue(2)
    assert view.loop_text().startswith("loop ") and note.text() in view.loop_text()
    view.resize(300, 120)
    view.grab()  # paints
