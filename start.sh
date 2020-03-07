#!/bin/bash
(
KEYS=$(/usr/bin/env python ssh.py)
IFS=';'
read -d '' -ra SPLITKEYS < <(printf '%s;\0' "$KEYS")

for i in ${SPLITKEYS[@]}
do
    ssh-add - <<< "${i}"
done

)