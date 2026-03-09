#!/bin/bash

python generate_layout.py \
    -l gl553vd-base.kbd \
    -p gl553vd-mapping.txt \
    -o gl553vd-miryoku-output.kbd \
    -df /dev/input/by-id/usb-ITE_Tech._Inc._ITE_Device_8910_-event-kbd
