#!/bin/bash

# Copy project files from laptop to raspberry pi
# (for use on laptop)
rsync -avc \
 --exclude="photos*"\
 --exclude="log*"\
 --exclude="images*"\
 --exclude="video*"\
 --exclude="__pycache__"\
 ~/Projects/speed/street-traffic/* \
 pi@pi:/home/pi/Projects/street-traffic
