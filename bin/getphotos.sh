#!/bin/bash
rsync -avcz --remove-source-files pi@pi:/home/pi/Projects/street-traffic/photos/ ./photos/
