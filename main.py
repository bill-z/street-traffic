import logging
import logging.handlers
import os
import sys
import time
import json
import re

import cv2
import numpy as np

from vehicle_tracker import VehicleTracker
# from debug_video import DebugVideo


IMAGE_DIR = "images"
IMAGE_FILENAME_FORMAT = IMAGE_DIR + "/frame_%04d.png"

# Time to wait between frames, 0=forever
WAIT_TIME = 1 # 250 # ms

LOG_TO_FILE = True

# Colours for drawing on processed frames 
BOUNDING_BOX_COLOR = (255, 0, 0)

# -----------------------------------------------------------------------------
def init_logging():
    main_logger = logging.getLogger()

    formatter = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(levelname)-8s [%(name)s] %(message)s'
        , datefmt='%Y-%m-%d %H:%M:%S')

    handler_stream = logging.StreamHandler(sys.stdout)
    handler_stream.setFormatter(formatter)
    main_logger.addHandler(handler_stream)

    if LOG_TO_FILE:
        handler_file = logging.handlers.RotatingFileHandler("debug.log"
            , maxBytes = 2**24
            , backupCount = 10)
        handler_file.setFormatter(formatter)
        main_logger.addHandler(handler_file)

    main_logger.setLevel(logging.DEBUG)

    return main_logger

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
    return image[y:y+h, x:x+w]

# -----------------------------------------------------------------------------
def filter_mask (mask):
    # if not kernels:
        # I want some pretty drastic 
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4, 4))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 8))
    # kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    # kernels = True

    # Remove noise
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    # Close holes within contours
    # mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    mask = cv2.dilate(mask, kernel_close, iterations = 1)
    return mask

# -----------------------------------------------------------------------------
def process_mask(frame, bg_subtractor):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    mask = bg_subtractor.apply(gray)
    mask = filter_mask(mask)

    return mask

# -----------------------------------------------------------------------------
def find_matches (mask):
    MIN_CONTOUR_WIDTH = 80
    MIN_CONTOUR_HEIGHT = 30

    # contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    matches = []

    # Hierarchy stuff:
    # https://stackoverflow.com/questions/11782147/python-opencv-contour-tree-hierarchy
    for (i, contour) in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        contour_valid = (w >= MIN_CONTOUR_WIDTH) and (h >= MIN_CONTOUR_HEIGHT)

        if not contour_valid or not hierarchy[0,i,3] == -1:
            continue

        matches.append((x,y,w,h))

    return matches

# -----------------------------------------------------------------------------
def draw_matches(matches, frame, mask):
    processed = frame.copy()

    for (i, match) in enumerate(matches):
        x,y,w,h = match
        cv2.rectangle(processed, (x,y), (x+w-1, y+h-1), BOUNDING_BOX_COLOR, 1)
        cv2.rectangle(mask, (x,y), (x+w-1, y+h-1), BOUNDING_BOX_COLOR, 1)

    return processed, mask


# -----------------------------------------------------------------------------
# I was going to use a haar cascade, but i decided against it because I don't want to train one, and even if I did it probably wouldn't work across different traffic cameras
def main ():
    # I think KNN works better than MOG2, specifically with trucks/large vehicles
    # bg_subtractor = cv2.createBackgroundSubtractorKNN(dist2Threshold=400.0, detectShadows=True)
    
    bg_subtractor = cv2.createBackgroundSubtractorKNN(history=10, dist2Threshold=100.0, detectShadows=False)
    # bg_subtractor = cv2.createBackgroundSubtractorMOG2()
    log.debug("Pre-training the background subtractor...")
    default_bg = cv2.imread(IMAGE_FILENAME_FORMAT % 1)
    if default_bg.size:
        bg_subtractor.apply(default_bg, None, 1.0)

    tracker = None

    cap = cv2.VideoCapture('testvideo2.mp4')
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # video_out = DebugVideo('output.mp4', width, height, fps, log)

    tracker = VehicleTracker(width, height, fps, log)

    cv2.namedWindow('Source Image')

    frame_number = -1

    while True:
        frame_number += 1
        ret, frame = cap.read()
        if not ret:
            log.debug('Frame capture failed, stopping...')
            break

        # crop to region of interest
        cropped = crop(frame)

        mask = process_mask(cropped, bg_subtractor)

        matches = find_matches(mask)

        processed, mask = draw_matches(matches, cropped, mask)

        currentVehicles = tracker.track(matches, frame_number, processed)

        result = cv2.vconcat([cropped, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), processed])
        cv2.imshow("traffic", result)

        # video_out.write(result)

        if currentVehicles > 0:
            save_frame(IMAGE_FILENAME_FORMAT, frame_number, result, "frame #%d")

        # log.debug("Frame #%d processed.", frame_number)

        key = cv2.waitKey(WAIT_TIME)
        if key == ord('q') or key == 27:
            log.debug("ESC or q key, stopping...")
            break

        # Keep video's speed stable
        # I think that this causes the abrupt jumps in the video
        # time.sleep( 1.0 / cap.get(cv2.CAP_PROP_FPS) )

    log.debug('Closing video capture...')
    cap.release()
    # video_out.release()
    cv2.destroyAllWindows()
    log.debug('Done.')

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    log = init_logging()

    if not os.path.exists(IMAGE_DIR):
        log.debug("Creating image directory `%s`...", IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    main()