
import os
#import time
#import json
#import re

import cv2

from log import Log
from detector import Detector
from tracker import Tracker
from video import VideoSource

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
    # x = 0
    # y = 240
    # w = 1080
    # h = 240
    #return (image[y:y+h, x:x+w] if image is not None else None)
    return image

# -----------------------------------------------------------------------------
def main ():

    video = VideoSource(video_file, log)
    width, height, fps = video.start()
    initial_bg = video.read()

    # video_out = DebugVideo(width, 480, fps, log)

    detector = Detector(initial_bg, log)

    tracker = Tracker(width, height, fps, log)

    frame_number = 0

    while (not video.done()):
        frame = video.read()
        if frame is None:
            continue
        frame_number += 1

        # crop to region of interest
        cropped = crop(frame)

        matches, mask = detector.detect(cropped);

        # mask = detector.draw_matches(matches, mask)

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

    log.debug('Closing video source...')
    video.stop()       

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

    video_file = None
    # video_file = 'video/testvideo2.mp4'

    main()
