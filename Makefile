# Copyright 2026 Corwin Brust <corwin@bru.st>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Mentat (for Corwin, claude-sonnet-5-5)
.PHONY: check prove-red
check:
	sh tests/run.sh
prove-red:
	sh tests/run.sh --prove-red
