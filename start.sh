#!/bin/sh
KEYS=$(/usr/bin/env python ssh.py)
ssh-add - <<< "${KEYS}"
