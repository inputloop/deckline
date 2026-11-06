#!/bin/sh
# Second reader: checks a scripted --fake session against the protocol using
# only POSIX sh and awk, so it shares no code (or language) with deckline or
# with tests/py.  Usage: transcript.sh PROGRAM   (PROGRAM is run with python3)
#
# Copyright 2026 Corwin Brust <corwin@bru.st>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mentat (for Corwin, claude-sonnet-5-5)
here=$(cd "$(dirname "$0")" && pwd)
prog=${1:-$here/../../deckline}
py=${PYTHON:-python3}
tmp=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp"' EXIT

# The script (what we send) and what each command must answer.
cat > "$tmp/script" <<'SCRIPT'
list
open 0
brightness 60
key 0 text "Hi"
key 1 clear
key 2 clear
sim press 2
sim release 2
sim dump 0
sim dump 14
key 15 clear
frobnicate
brightness 500
reset
quit
SCRIPT
cat > "$tmp/expect" <<'EXPECT'
ok
ok
ok
ok
ok
ok
ok
ok
ok
error
error
error
error
ok
ok
EXPECT
# sim dump 14 has no image yet: it is an error, so fix the expectation.
awk 'NR==10{print "error"; next} {print}' "$tmp/expect" > "$tmp/expect2"

"$py" "$prog" --fake < "$tmp/script" > "$tmp/out" || { echo "FAIL: deckline exited with an error"; exit 1; }

awk -v scriptf="$tmp/script" -v expectf="$tmp/expect2" '
BEGIN {
  while ((getline l < scriptf) > 0) cmd[++nc] = l
  while ((getline l < expectf) > 0) want[++ne] = l
  bad = 0; term = 0; prev = ""; dim = ""
}
function fail(msg) { print "FAIL line " NR ": " msg " [" $0 "]"; bad = 1 }
{
  if ($0 ~ /^deck /) {
    if (NF != 7) fail("deck line needs 7 fields")
    split($6, cr, "x"); split($7, wh, "x")
    if ($5 != cr[1] * cr[2]) fail("KEYS is not COLS*ROWS")
    dim = $7
  } else if ($0 ~ /^(press|release) [0-9]+$/) {
    # an event: must be followed (next line) by the ok of its sim command
  } else if ($0 ~ /^image [0-9]+ [A-Z]+ [0-9]+x[0-9]+ [0-9]+$/) {
    if ($4 != dim) fail("image size " $4 " differs from the deck IMAGE_WxH " dim)
    if ($5 + 0 <= 0) fail("empty image")
  } else if ($0 ~ /^(ok|error) /) {
    term++
    if (term > nc) { fail("more replies than commands"); next }
    kind = ($1 == "ok") ? "ok" : "error"
    if (kind != want[term]) fail("reply " term " should be " want[term] " for command: " cmd[term])
    if (cmd[term] ~ /^sim (press|release) /) {
      split(cmd[term], c, " ")
      if (prev != c[2] " " c[3]) fail("no echo of " c[2] " " c[3] " before the ok")
    }
  } else fail("line fits no part of the protocol")
  prev = $0
}
END {
  if (term != nc) { print "FAIL: " nc " commands but " term " replies"; bad = 1 }
  if (!bad) print "transcript ok: " term " commands, " term " replies"
  exit bad
}' "$tmp/out"
