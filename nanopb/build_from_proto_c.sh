#!/bin/bash

(\
source $ESP32_TOOLS/.venv/bin/activate && \
python generator/nanopb_generator.py $@ 1>/dev/null \
)
