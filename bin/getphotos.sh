#!/bin/bash

# Copy photo files from raspberry pi to local folder.
# Source files are deleted after copying.
# (for use on laptop)
rsync -avcz --remove-source-files\
 pi@pi:/home/pi/Projects/street-traffic/photos/\
 ./photos/
