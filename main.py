
import os
import time
import json
import re

import cv2
import numpy as np
from imutils.video import FileVideoStream

from log import Log
from detector import Detector
from tracker import Tracker

# from debug_video import DebugVideo

LOG_TO_FILE = True

IMAGE_DIR = "images"
IMAGE_FILENAME_FORMAT = IMAGE_DIR + "/frame_%04d.png"

# Time to wait between frames, 0=forever
WAIT_TIME = 1 # 250 # ms

# Colours for drawing on processed frames 
BOUNDING_BOX_COLOR = (255, 0, 0)

# -----------------------------------------------------------------------------
def save_frame(file_name_format, frame_number, frame, label_format):
    file_name = file_name_format % frame_number
    # label = label_format % frame_number

    # log.debug("Saving %s as '%s'", label, file_name)
    cv2.imwrite(file_name, frame)

# -----------------------------------------------------------------------------
# Remove cropped regions from frame
def crop (image):
    # keep the center vertical third of the image, full width (of 1080x720)
    #TODO define these "better"
    x = 0
    y = 240
    w = 1080
    h = 240
    return (image[y:y+h, x:x+w] if image is not None else None)


# -----------------------------------------------------------------------------
# I was going to use a haar cascade, but i decided against it because I don't want to train one, and even if I did it probably wouldn't work across different traffic cameras
def main ():
    fvs = FileVideoStream('testvideo2.mp4').start()
    cap = fvs.stream;
    time.sleep(1.0)

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # video_out = DebugVideo(width, 480, fps, log)

    initial_bg = cv2.imread(IMAGE_FILENAME_FORMAT % 1)
    detector = Detector(initial_bg, log)

    tracker = Tracker(width, height, fps, log)

    frame_number = -1

    while fvs.running():
        frame_number += 1
        frame = fvs.read()
        if frame is None:
            continue

        # crop to region of interest
        cropped = crop(frame)

        matches, mask = detector.detect(cropped);

        mask = detector.draw_matches(matches, mask)

        trackedObjectCount = tracker.track(matches, frame_number, cropped)

        result = cv2.vconcat([cropped, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)])
        cv2.imshow("Traffic", result)

        # video_out.write(result)

        if trackedObjectCount > 0:
            save_frame(IMAGE_FILENAME_FORMAT, frame_number, result, "frame #%d")

        key = cv2.waitKey(WAIT_TIME)
        if key == ord('q') or key == 27:
            log.debug("ESC or q key, stopping...")
            break

    log.debug('Closing video capture...')
    fvs.stop()

    # video_out.release()
    cv2.destroyAllWindows()
    log.debug('Done.')

# -----------------------------------------------------------------------------
if __name__ == '__main__':

    log = Log(LOG_TO_FILE)
    log = log.getLog()

    if not os.path.exists(IMAGE_DIR):
        log.debug("Creating image directory `%s`...", IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    main()