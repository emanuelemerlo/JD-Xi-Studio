"""
USBRecorder
"""

import wave
from typing import Optional

import pyaudio
from decologr import Decologr as log


class USBRecorder:
    """
    A convenient class for recording audio from a USB input device.
    """

    def __init__(
        self,
        input_device_index: int = None,
        channels: int = 2,  # the JD-Xi sends stereo over USB
        rate: int = 44100,
        frames_per_buffer: int = 1024,
    ):
        """
        Initializes the recorder with the specified settings.

        PortAudio starts on first use (see ``p``), not here: initialising it
        enumerates every audio driver, which takes seconds on some Windows
        machines and fails where there is no audio system (CI, servers).
        """
        self._p = None
        self.error: str = ""
        self.input_device_index = input_device_index
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self.file_save_recording: bool = False  # Default to false
        self.usb_port_input_device_index = None
        # 16-bit PCM: what the recording thread opens and writes (the WAV header
        # says the same); a wider format would need both changed together
        self.sample_format = pyaudio.paInt16

    @property
    def p(self) -> "pyaudio.PyAudio":
        """The PyAudio instance, created on first use (may raise OSError)."""
        if self._p is None:
            self._p = pyaudio.PyAudio()
        return self._p

    def input_devices(self) -> list[tuple[int, str]]:
        """
        The devices that can record: (PortAudio index, label), [] without an
        audio system. Output-only devices (speakers, the JD-Xi's playback side)
        are left out: opening one for input fails.
        """
        try:
            count = self.p.get_device_count()
        except Exception as ex:  # no audio system: nothing to record from
            self.error = str(ex)
            log.warning(f"[USBRecorder] Audio system unavailable: {ex}")
            return []
        host_apis = {}
        try:
            for api in range(self.p.get_host_api_count()):
                host_apis[api] = self.p.get_host_api_info_by_index(api).get("name", "")
        except Exception:
            host_apis = {}
        devices = []
        for i in range(count):
            info = self.p.get_device_info_by_index(i)
            channels = int(info.get("maxInputChannels", 0) or 0)
            if channels <= 0:
                continue
            label = f"{info['name']}"
            api = host_apis.get(info.get("hostApi"))
            if api and len(host_apis) > 1:  # Windows: MME, WASAPI, … list a device several times
                label += f" — {api}"
            label += " (stereo)" if channels >= 2 else " (mono)"
            devices.append((i, label))
        return devices

    def default_host_api(self) -> Optional[int]:
        try:
            return int(self.p.get_default_host_api_info()["index"])
        except Exception:
            return None

    def list_devices(self):
        """The labels of the devices that can record ([] without an audio system)."""
        log.message("[USBRecorder] Available audio input devices:")
        device_list = []
        for index, label in self.input_devices():
            device_info = f"{index}: {label}"
            log.info(device_info)
            device_list.append(device_info)
        return device_list

    def record(self, duration, output_file):
        """
        Records audio for the specified duration and saves to a .wav file.
        """
        log.message("[USBRecorder] Recording...")
        try:
            stream = self.p.open(
                format=self.sample_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.frames_per_buffer,
            )
        except Exception as e:
            log.error(f"[USBRecorder] Unable to open stream: {e}")
            return

        frames = []

        try:
            for _ in range(0, int(self.rate / self.frames_per_buffer * duration)):
                data = stream.read(self.frames_per_buffer)
                frames.append(data)
        except Exception as ex:
            log.error(f"[USBRecorder] Error while recording: {ex}")

        stream.stop_stream()
        stream.close()

        log.message("[USBRecorder] Recording finished")

        if not frames:
            log.warning("[USBRecorder] No audio captured.")
            return

        with wave.open(output_file, "wb") as f:
            f.setnchannels(self.channels)
            f.setsampwidth(self.p.get_sample_size(self.sample_format))
            f.setframerate(self.rate)
            f.writeframes(b"".join(frames))

        print(f"[USBRecorder] File successfully saved to {output_file}")

    def close(self):
        """Closes the PyAudio instance, if it was started."""
        if self._p is not None:
            self._p.terminate()
            self._p = None

    def stop_recording(self):
        """
        stop_recording

        :return: None
        """
        try:
            if hasattr(self, "usb_recording_thread"):
                self.usb_recording_thread.stop_recording()
        except Exception as ex:
            log.error(f"[USBRecorder] Error {ex} occurred stopping USB recording")


# 🔹 Example usage 🔹
if __name__ == "__main__":
    recorder = USBRecorder()
    recorder.list_devices()
    recorder.input_device_index = 7  # Change to your preferred device index
    recorder.record(duration=270, output_file="new_order_ceremony.wav")
    recorder.close()
