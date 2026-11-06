# deckline

A deck spoken to by lines. `deckline` is a small free program that lets any other program drive an
Elgato Stream Deck by writing plain lines to it and reading plain lines back, so a Windows user can
run a Stream Deck with no vendor software at all. (Draw, Emacs, OBS scripts, PowerShell and
StreamController are all meant to be callers.)

Why it exists, in one sentence: you bought the device, so you should be able to make it do what you
want without installing the maker's app, and this is a repair of that right.

Version 0.1.0. Python 3, Pillow, and the device library (included in `vendor/`). GPL-3.0-or-later.

## Install (MSYS2 UCRT64)

In a UCRT64 shell:

    pacman -S mingw-w64-ucrt-x86_64-hidapi mingw-w64-ucrt-x86_64-python-pillow

(`mingw-w64-ucrt-x86_64-python` too, if `python --version` says nothing.) That is all: the device
library is vendored in `vendor/` (see `vendor/VENDORED.txt`). If you would rather use your own copy,
`pip install git+https://github.com/StreamController/sc-python-elgato-streamdeck.git` into a venv
works, and `DECKLINE_LIB=/path/containing/StreamDeck` points deckline at any other copy.

No hidapi from pacman? Put `hidapi.dll` in the same folder as `deckline`; it is looked for there too.
Quit any program that already holds the deck (Elgato's app, StreamController); only one may.

## The first real test

    echo list | python deckline

With a deck plugged in, that prints something like

    deck 0 Stream-Deck-XL A00NA1234567 32 8x4 96x96
    ok list 1

Then, to set brightness and put a word on key 0:

    printf 'open 0\nbrightness 60\nkey 0 text "Hello"\n' | python deckline

The program quits when its input ends, so to watch presses keep the pipe open for a while:

    (printf 'open 0\nkey 0 text Hi\n'; sleep 30) | python deckline

Press keys during the 30 seconds and `press 0` / `release 0` lines appear.

No deck at hand? `python deckline --fake` is a simulated 15-key deck, and every example below works
against it.

## The protocol

One command per line on stdin. Every command gets exactly one reply line, `ok ...` or
`error <plain words>`. Events come on their own lines at any time. Blank lines and lines starting
with `#` are ignored. The program ends at `quit` or when stdin closes.

| command | what it does | reply |
|---|---|---|
| `list` | find decks | one `deck N MODEL SERIAL KEYS COLSxROWS IMAGE_WxH` line each, then `ok list COUNT` |
| `open N` | take deck N from the list (closes any other) | `ok open N` |
| `brightness PCT` | 0 to 100 | `ok brightness PCT` |
| `key K image PATH` | picture on key K, scaled to fit on black, converted to the deck's format | `ok key K image` |
| `key K text "LABEL"` | white text on black, sized to fit; `\n` in quotes is a new line | `ok key K text` |
| `key K clear` | black | `ok key K clear` |
| `reset` | the library's reset (back to the deck's own logo) | `ok reset` |
| `quit` | close and exit | `ok quit` |

Words are split on spaces. Wrap a word in double quotes to keep spaces in it. Inside quotes only
`\"`, `\\` and `\n` are escapes, so `"C:\pics\a.png"` works as typed. Keys count from 0, left to
right, top row first. MODEL has hyphens for spaces (`Stream-Deck-XL`); SERIAL is `busy` when another
program holds that deck during `list`.

Events (no reply, no `ok`):

    press K            release K
    dial D turn N      (N negative for counter-clockwise)      dial D press      dial D release
    touch short X Y    touch long X Y      touch drag X Y XOUT YOUT

The `dial` and `touch` lines come from Plus-type decks; they are written to follow the library's
callbacks and have not been seen on real hardware.

Errors are one line, `error ` and plain words, for example:

    error hidapi not found: install mingw-w64-ucrt-x86_64-hidapi or put hidapi.dll beside deckline
    error deck busy: another program (perhaps the Elgato app) holds it
    error no deck is open: send open N first
    error key 15 is out of range 0-14
    error unknown command: frobnicate

### --fake

`python deckline --fake` has one simulated deck, `Stream-Deck-Fake`, 15 keys, 5x3, 72x72 JPEG. It
adds a `sim` command (and only in this mode) so front ends and tests can play the hardware:

    sim press K     sim release K     (answers with the event, then `ok sim`)
    sim dump K      (what was sent to key K: `image K FORMAT WxH BYTES`, then `ok sim`)
    sim brightness  (`brightness N`, then `ok sim`)

A scripted session:

    $ printf 'list\nopen 0\nkey 1 text "Go"\nsim press 1\nsim dump 1\nquit\n' | python deckline --fake
    deck 0 Stream-Deck-Fake FAKE00000001 15 5x3 72x72
    ok list 1
    ok open 0
    ok key 1 text
    press 1
    ok sim
    image 1 JPEG 72x72 3298   (BYTES varies with the font found)
    ok sim
    ok quit

## Tests

    sh tests/run.sh               # or: make check
    sh tests/run.sh --prove-red   # or: make prove-red

The first runs the protocol and image tests (Python, against `--fake` and a stub of the library) and
a second reader written in POSIX sh and awk that checks a scripted `--fake` transcript against the
protocol on its own. The second plants four faults in copies of the program (hidapi missing not said
plainly, a press not echoed, a wrong image size, an unknown command ignored) and must see each one
fail, ending `PROVE-RED OK (4 of 4 caught; control passed)`. None of this touches real hardware.

## Credit and licence

deckline is Copyright 2026 Corwin Brust <corwin@bru.st>, GPL-3.0-or-later (`COPYING`).

The device library in `vendor/StreamDeck/` is not ours and stays under its own MIT licence
(`vendor/LICENSE-streamdeck`): `python-elgato-streamdeck` by Dean Camera
(<https://github.com/abcminiuser/python-elgato-streamdeck>), and the fork kept up by the
StreamController project, `sc-python-elgato-streamdeck`
(<https://github.com/StreamController/sc-python-elgato-streamdeck>), which adds the newer decks. All
the hard part, speaking the decks' USB protocol, is theirs; deckline is the line-shaped door on it.

"Elgato" and "Stream Deck" are trademarks of their owner; this project is independent of them.

Mentat (for Corwin, claude-sonnet-5-5)
