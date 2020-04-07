#!/bin/bash
(
SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPTPATH

KEYS=$(/usr/bin/env python ssh.py)
IFS=';'
read -d '' -ra SPLITKEYS < <(printf '%s;\0' "$KEYS")

for i in ${SPLITKEYS[@]}
do
    ssh-add - <<< "${i}"
done

)