#!/bin/sh
# deckline tests.  `sh tests/run.sh` runs them; `sh tests/run.sh --prove-red`
# plants four faults in copies of the program and demands each one is caught.
#
# Copyright 2026 Corwin Brust <corwin@bru.st>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mentat (for Corwin, claude-sonnet-5-5)
here=$(cd "$(dirname "$0")" && pwd)
root=$(dirname "$here")
py=${PYTHON:-python3}
export PYTHON="$py"

pyt() {   # pyt PROGRAM TEST...   run named tests against PROGRAM; quiet
  prog=$1; shift
  ( cd "$here/py" && DECKLINE="$prog" "$py" -m unittest "$@" >/dev/null 2>&1 )
}

if [ "$1" != "--prove-red" ]; then
  ( cd "$here/py" && DECKLINE="$root/deckline" "$py" -m unittest -v test_deckline ) || { echo "FAIL: python tests"; exit 1; }
  sh "$here/sh/transcript.sh" "$root/deckline" || { echo "FAIL: transcript reader"; exit 1; }
  echo "ALL OK"
  exit 0
fi

tmp=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp"' EXIT
total=0; caught=0; control=ok

# name | the test that must notice | sed expression planting the fault
cat > "$tmp/faults" <<'FAULTS'
hidapi-not-plain|test_deckline.Protocol.test_hidapi_missing_is_plain|s/error hidapi not found/error something went wrong/
press-not-echoed|test_deckline.Protocol.test_press_is_echoed|s/^        self.say(("press %d" if state else "release %d") % key)$/        pass/
image-size-wrong|test_deckline.Images.test_image_file_is_scaled_to_the_key|s/canvas = Image.new("RGB", (w, h), "black")/canvas = Image.new("RGB", (w, h + 1), "black")/
unknown-ignored|test_deckline.Protocol.test_unknown_command_is_an_error|s/raise DeckError("error unknown command: " + cmd)/return None/
FAULTS

# Control: the real program passes every one of those tests.
while IFS='|' read -r name test expr; do
  pyt "$root/deckline" "$test" || { control=FAILED; echo "control: $test failed on the unplanted program"; }
done < "$tmp/faults"

while IFS='|' read -r name test expr; do
  total=$((total + 1))
  sed "$expr" "$root/deckline" > "$tmp/mutant"
  if cmp -s "$tmp/mutant" "$root/deckline"; then
    echo "fault $name: the planting did not change the program (fix the fault line)"; continue
  fi
  if pyt "$tmp/mutant" "$test"; then
    echo "fault $name: NOT caught by $test"
  else
    caught=$((caught + 1)); echo "fault $name: caught"
  fi
done < "$tmp/faults"

# The second reader must also go red on a planted fault (press not echoed).
sed "$(sed -n 's/^press-not-echoed|[^|]*|//p' "$tmp/faults")" "$root/deckline" > "$tmp/mutant2"
if sh "$here/sh/transcript.sh" "$tmp/mutant2" >/dev/null 2>&1; then
  echo "transcript reader: did NOT go red on a planted fault"; control=FAILED
else
  echo "transcript reader: caught the planted fault"
fi

if [ "$caught" = "$total" ] && [ "$control" = ok ]; then
  echo "PROVE-RED OK ($caught of $total caught; control passed)"
else
  echo "PROVE-RED FAILED ($caught of $total caught; control $control)"; exit 1
fi
