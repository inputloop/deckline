# Protocol and image tests for deckline, run against --fake and a library stub.
# Copyright 2026 Corwin Brust <corwin@bru.st>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mentat (for Corwin, claude-sonnet-5-5)
import importlib.machinery
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROG = os.environ.get("DECKLINE", os.path.join(ROOT, "deckline"))
STUB = os.path.join(ROOT, "tests", "stub")


def run(lines, args=("--fake",), env=None):
    """Feed lines to the program; return its stdout lines."""
    e = dict(os.environ)
    e.pop("DECKLINE_LIB", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, PROG, *args], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, env=e, timeout=60)
    return p.stdout.splitlines()


def load_module():
    loader = importlib.machinery.SourceFileLoader("deckline_under_test", PROG)
    spec = importlib.util.spec_from_loader("deckline_under_test", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Protocol(unittest.TestCase):
    def test_list_line_shape(self):
        out = run(["list"])
        m = re.fullmatch(r"deck 0 (\S+) (\S+) (\d+) (\d+)x(\d+) (\d+)x(\d+)", out[0])
        self.assertTrue(m, out)
        keys, cols, rows = int(m.group(3)), int(m.group(4)), int(m.group(5))
        self.assertEqual((keys, cols, rows), (15, 5, 3))
        self.assertEqual(out[1], "ok list 1")

    def test_press_is_echoed(self):
        out = run(["open 0", "sim press 3"])
        self.assertEqual(out, ["ok open 0", "press 3", "ok sim"])

    def test_release_is_echoed(self):
        out = run(["open 0", "sim release 7"])
        self.assertEqual(out, ["ok open 0", "release 7", "ok sim"])

    def test_unknown_command_is_an_error(self):
        out = run(["frobnicate now"])
        self.assertEqual(out, ["error unknown command: frobnicate"])

    def test_sim_is_not_a_command_without_fake(self):
        out = run(["sim press 1"], args=(), env={"STUB_MODE": "one", "DECKLINE_LIB": STUB})
        self.assertEqual(out, ["error unknown command: sim"])

    def test_hidapi_missing_is_plain(self):
        out = run(["list"], args=(), env={"STUB_MODE": "nohidapi", "DECKLINE_LIB": STUB})
        self.assertEqual(out, ["error hidapi not found: install mingw-w64-ucrt-x86_64-hidapi "
                               "or put hidapi.dll beside deckline"])

    def test_busy_deck_is_plain(self):
        out = run(["list", "open 0"], args=(), env={"STUB_MODE": "busy", "DECKLINE_LIB": STUB})
        self.assertEqual(out[-1], "error deck busy: another program (perhaps the Elgato app) holds it")

    def test_commands_need_an_open_deck(self):
        out = run(["brightness 50", "key 0 clear", "reset"])
        self.assertEqual(out, ["error no deck is open: send open N first"] * 3)

    def test_argument_errors(self):
        out = run(["open 0", "key 15 clear", "key x clear", "brightness 101",
                   "brightness lots", "open 4", "key 0 text", "key 0 dance", 'key 0 text "oops'])
        self.assertEqual(out[0], "ok open 0")
        for line in out[1:]:
            self.assertTrue(line.startswith("error "), line)
        self.assertEqual(len(out), 9)

    def test_one_reply_per_command(self):
        cmds = ["list", "open 0", "brightness 10", "key 1 text A", "key 1 clear", "reset", "quit"]
        out = run(cmds)
        replies = [l for l in out if l.startswith(("ok", "error"))]
        self.assertEqual(len(replies), len(cmds))

    def test_comments_and_blank_lines_are_skipped(self):
        self.assertEqual(run(["", "# hello", "open 0"]), ["ok open 0"])

    def test_end_of_input_ends_quietly(self):
        self.assertEqual(run(["open 0"]), ["ok open 0"])


class Images(unittest.TestCase):
    def dump(self, setup, key=1):
        return run(["open 0", *setup, "sim dump %d" % key])[-2]

    def test_image_file_is_scaled_to_the_key(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "wide.png")
            Image.new("RGB", (200, 100), "red").save(path)
            line = self.dump(["key 1 image " + path])
        self.assertRegex(line, r"image 1 JPEG 72x72 \d+")

    def test_image_path_with_spaces_in_quotes(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a b.png")
            Image.new("RGB", (10, 10), "blue").save(path)
            line = self.dump(['key 1 image "%s"' % path])
        self.assertRegex(line, r"image 1 JPEG 72x72 \d+")

    def test_text_and_clear_have_the_key_format(self):
        self.assertRegex(self.dump(['key 1 text "Hi\\nthere"']), r"image 1 JPEG 72x72 \d+")
        self.assertRegex(self.dump(["key 1 clear"]), r"image 1 JPEG 72x72 \d+")

    def test_text_is_not_blank(self):
        a = int(self.dump(["key 1 clear"]).split()[-1])
        b = int(self.dump(['key 1 text "WWW"']).split()[-1])
        self.assertGreater(b, a)

    def test_missing_image_file(self):
        out = run(["open 0", "key 1 image /no/such/file.png"])
        self.assertEqual(out[1], "error no such file: /no/such/file.png")

    def test_native_format_through_the_library_stub(self):
        # The real-library path: a 96x96 JPEG deck from the stub, set_key_image reached.
        out = run(["list", "open 0", "key 2 text K", "key 2 clear"], args=(),
                  env={"STUB_MODE": "one", "DECKLINE_LIB": STUB})
        self.assertEqual(out, ["deck 0 Stream-Deck-XL STUB1234 32 8x4 96x96", "ok list 1",
                               "ok open 0", "ok key 2 text", "ok key 2 clear"])

    def test_to_native_size_and_format(self):
        from PIL import Image
        mod = load_module()
        fmt = {"size": (80, 80), "format": "BMP", "flip": (False, True), "rotation": 90}
        im = Image.open(io.BytesIO(mod.to_native(Image.new("RGB", (30, 10), "white"), fmt)))
        self.assertEqual((im.format, im.size), ("BMP", (80, 80)))


class Pieces(unittest.TestCase):
    def test_split_line(self):
        mod = load_module()
        self.assertEqual(mod.split_line('key 3 text "a b" x'), ["key", "3", "text", "a b", "x"])
        self.assertEqual(mod.split_line(r'key 3 image C:\pics\a.png'), ["key", "3", "image", r"C:\pics\a.png"])
        self.assertEqual(mod.split_line(r'key 3 image "C:\pics\a.png"'), ["key", "3", "image", r"C:\pics\a.png"])
        self.assertEqual(mod.split_line(r'x "say \"hi\"\n"'), ["x", 'say "hi"\n'])
        self.assertEqual(mod.split_line('x ""'), ["x", ""])

    def test_dial_and_touch_lines(self):
        mod = load_module()
        out = io.StringIO()
        s = mod.Session(True, out)

        class K:                       # stands in for the library's enums
            def __init__(self, name): self.name = name
        s.on_dial(None, 1, K("TURN"), -3)
        s.on_dial(None, 0, K("PUSH"), True)
        s.on_dial(None, 0, K("PUSH"), False)
        s.on_touch(None, K("SHORT"), {"x": 10, "y": 20})
        s.on_touch(None, K("LONG"), {"x": 11, "y": 21})
        s.on_touch(None, K("DRAG"), {"x": 1, "y": 2, "x_out": 3, "y_out": 4})
        self.assertEqual(out.getvalue().splitlines(), [
            "dial 1 turn -3", "dial 0 press", "dial 0 release",
            "touch short 10 20", "touch long 11 21", "touch drag 1 2 3 4"])

    def test_vendored_library_imports(self):
        code = ("import sys; sys.path.insert(0, %r);"
                "from StreamDeck.DeviceManager import DeviceManager, ProbeError;"
                "print('ok')" % os.path.join(ROOT, "vendor"))
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(p.stdout.strip(), "ok", p.stderr)


if __name__ == "__main__":
    unittest.main()
