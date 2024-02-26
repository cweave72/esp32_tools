#!/bin/bash

(\
source $ESP32_TOOLS/init_env.sh && \
python generator/nanopb_generator.py $@ 1>/dev/null \
)
