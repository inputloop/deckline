# Test stub: mimics the library's DeviceManager with a mode from STUB_MODE.
# Copyright 2026 Corwin Brust <corwin@bru.st>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mentat (for Corwin, claude-sonnet-5-5)
import os


class ProbeError(Exception):
    pass


class _Deck:
    def __init__(self, busy):
        self.busy, self.isopen = busy, False

    def open(self):
        if self.busy:
            raise OSError("Could not open HID device.")
        self.isopen = True

    def close(self): self.isopen = False
    def deck_type(self): return "Stream Deck XL"
    def get_serial_number(self): return "STUB1234"
    def key_count(self): return 32
    def key_layout(self): return (4, 8)
    def is_visual(self): return True
    def key_image_format(self):
        return {"size": (96, 96), "format": "JPEG", "flip": (True, True), "rotation": 0}
    def set_key_image(self, key, data): self.last = (key, data)
    def set_key_callback(self, cb): pass
    def set_dial_callback(self, cb): pass
    def set_touchscreen_callback(self, cb): pass


class DeviceManager:
    def __init__(self, transport=None):
        if os.environ.get("STUB_MODE") == "nohidapi":
            raise ProbeError("Probe failed to find any functional HID backend.", {})

    def enumerate(self):
        return [_Deck(os.environ.get("STUB_MODE") == "busy")]
