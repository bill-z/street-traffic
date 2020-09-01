import logging
import logging.handlers
import os
import sys
import time
import json
import re

import cv2
import numpy as np

from vehicle_counter import VehicleCounter


IMAGE_DIR = "images"
SOURCE_IMAGE_FILENAME_FORMAT = IMAGE_DIR + "/frame_%04d.png"
MASK_IMAGE_FILENAME_FORMAT = IMAGE_DIR + "/mask%04d.png"
PROCESSED_IMAGE_FILENAME_FORMAT = IMAGE_DIR + "/processed_%04d.png"

# Time to wait between frames, 0=forever
WAIT_TIME = 1 # 250 # ms

LOG_TO_FILE = True

# Colours for drawing on processed frames 
DIVIDER_COLOR = (255, 255, 0)
BOUNDING_BOX_COLOR = (255, 0, 0)
CENTROID_COLOR = (0, 0, 255)



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
    label = label_format % frame_number

    log.debug("Saving %s as '%s'", label, file_name)
    cv2.imwrite(file_name, frame)

# -----------------------------------------------------------------------------

road = None

def load_road(road_name):
    with open('settings.json') as f:
        data = json.load(f)

        try:
            road = data[road_name]
        except KeyError:
            raise Exception('Road name not recognized.')

    # For cropped rectangles
    ref_points = []
    ref_rects = []

    return road

def click_and_crop (event, x, y, flags, param):
    global ref_points

    if event == cv2.EVENT_LBUTTONDOWN:
        ref_points = [(x,y)]

    elif event == cv2.EVENT_LBUTTONUP:
        (x1, y1), x2, y2 = ref_points[0], x, y

        ref_points[0] = ( min(x1,x2), min(y1,y2) )		

        ref_points.append ( ( max(x1,x2), max(y1,y2) ) )

        ref_rects.append( (ref_points[0], ref_points[1]) )

# Write cropped rectangles to file for later use/loading
def save_cropped():
    global ref_rects

    with open('settings.json', 'r+') as f:
        data = json.load(f)
        data[road_name]['cropped_rects'] = ref_rects

        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()

    log.debug('Saved ref_rects to settings.json!')

# Load any saved cropped rectangles
def load_cropped ():
    global ref_rects

    ref_rects = road['cropped_rects']

    log.debug('Loaded ref_rects from settings.json!')

# -----------------------------------------------------------------------------
# Remove cropped regions from frame
def crop (image):
    # cropped = image.copy()

    # for rect in ref_rects:
    #     cropped[ rect[0][1]:rect[1][1], rect[0][0]:rect[1][0] ] = 0
    #TODO define these "better"
    x = 0
    y = 240
    w = 1080
    h = 240
    cropped = image[y:y+h, x:x+w]

    return cropped

# -----------------------------------------------------------------------------
def filter_mask (mask, kernel4, kernel8):
    # # I want some pretty drastic closing
    # kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
    # kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (8, 8))
    # kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # # Remove noise
    # opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    # # Close holes within contours
    # # closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel_close)
    # # Merge adjacent blobs
    # # dilation = cv2.dilate(closing, kernel_dilate, iterations = 2)

    # return dilation

    #----
    # kernel3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    #TODO - don't do this every time!!
    # kernel4 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4, 4))
    # kernel8 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (8, 8))
    # kernel20 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))

    # Remove noise
    opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel4)
    # dilation = cv2.dilate(opening, kernel8, iterations = 2)
    # Close holes within contours
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel8)

    return closing
    #----
    # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # # Fill any small holes
    # closing = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    # # Remove noise
    # opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)

    # # Dilate to merge adjacent blobs
    # dilation = cv2.dilate(opening, kernel, iterations = 2)

    # return dilation

# -----------------------------------------------------------------------------
def get_centroid (x, y, w, h):
    x1 = w // 2
    y1 = h // 2

    return(x+x1, y+y1)

# -----------------------------------------------------------------------------
def detect_vehicles (mask):

    # MIN_CONTOUR_WIDTH = 10
    # MIN_CONTOUR_HEIGHT = 10
    MIN_CONTOUR_WIDTH = 40
    MIN_CONTOUR_HEIGHT = 30

    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    matches = []

    # Hierarchy stuff:
    # https://stackoverflow.com/questions/11782147/python-opencv-contour-tree-hierarchy
    for (i, contour) in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        contour_valid = (w >= MIN_CONTOUR_WIDTH) and (h >= MIN_CONTOUR_HEIGHT)

        if not contour_valid or not hierarchy[0,i,3] == -1:
            continue

        centroid = get_centroid(x, y, w, h)

        matches.append( ((x,y,w,h), centroid) )

    return matches

# -----------------------------------------------------------------------------
def process_mask(frame, bg_subtractor, kernel4, kernel8):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    mask = bg_subtractor.apply(frame)
    mask = filter_mask(mask, kernel4, kernel8)

    return mask

# -----------------------------------------------------------------------------
def draw_matches(matches, frame, mask):
    processed = frame.copy()
    # if car_counter.is_horizontal:
    # 	cv2.line(processed, (0, car_counter.divider), (frame.shape[1], car_counter.divider), DIVIDER_COLOR, 1)
    # else:
    # 	cv2.line(processed, (car_counter.divider, 0), (car_counter.divider, frame.shape[0]), DIVIDER_COLOR, 1)

    for (i, match) in enumerate(matches):
        contour, centroid = match

        x,y,w,h = contour

        cv2.rectangle(processed, (x,y), (x+w-1, y+h-1), BOUNDING_BOX_COLOR, 1)
        cv2.rectangle(mask, (x,y), (x+w-1, y+h-1), BOUNDING_BOX_COLOR, 1)
        # cv2.circle(processed, centroid, 2, CENTROID_COLOR, -1)
    return processed, mask


# -----------------------------------------------------------------------------
# I was going to use a haar cascade, but i decided against it because I don't want to train one, and even if I did it probably wouldn't work across different traffic cameras
def main ():
    # I think KNN works better than MOG2, specifically with trucks/large vehicles
    # bg_subtractor = cv2.createBackgroundSubtractorKNN(dist2Threshold=400.0, detectShadows=True)
    bg_subtractor = cv2.createBackgroundSubtractorKNN(history=10, dist2Threshold=100.0, detectShadows=False)

    log.debug("Pre-training the background subtractor...")
    default_bg = cv2.imread(SOURCE_IMAGE_FILENAME_FORMAT % 40)
    if default_bg.size:
        bg_subtractor.apply(default_bg, None, 1.0)

    car_counter = None

    load_cropped()

    cap = cv2.VideoCapture('testvideo-720.mp4')
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    cv2.namedWindow('Source Image')
    cv2.setMouseCallback('Source Image', click_and_crop)

    kernel4 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4, 4))
    kernel8 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (8, 8))

    # frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    # frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    frame_number = -1

    while True:
        frame_number += 1
        ret, frame = cap.read()

        if not ret:
            log.debug('Frame capture failed, stopping...')
            break

        # log.debug("Got frame #%d: shape=%s", frame_number, frame.shape)

        if car_counter is None:
            car_counter = VehicleCounter(frame.shape[:2], road, cap.get(cv2.CAP_PROP_FPS), log, samples=0)

        # remove specified cropped regions
        cropped = crop(frame);

        mask = process_mask(cropped, bg_subtractor, kernel4, kernel8)

        matches = detect_vehicles(mask)

        processed, mask = draw_matches(matches, cropped, mask)

        currentVehicles = car_counter.update_count(matches, frame_number, processed)

        result = cv2.vconcat([cropped, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), processed])
        cv2.imshow("traffic", result)

        if currentVehicles > 0:
            save_frame(SOURCE_IMAGE_FILENAME_FORMAT, frame_number, result, "frame #%d")

            # save_frame(SOURCE_IMAGE_FILENAME_FORMAT, frame_number, frame, 
            #     "source frame #%d")
            # save_frame(MASK_IMAGE_FILENAME_FORMAT, frame_number, mask, 
            #     "mask frame #%d")
            # save_frame(PROCESSED_IMAGE_FILENAME_FORMAT, frame_number, processed, 
            #     "processed frame #%d")

        # log.debug("Frame #%d processed.", frame_number)

        key = cv2.waitKey(WAIT_TIME)
        if key == ord('s'):
            # save rects!
            save_cropped()
        elif key == ord('q') or key == 27:
            log.debug("ESC or q key, stopping...")
            break

        # Keep video's speed stable
        # I think that this causes the abrupt jumps in the video
        # time.sleep( 1.0 / cap.get(cv2.CAP_PROP_FPS) )


    log.debug('Closing video capture...')
    cap.release()
    cv2.destroyAllWindows()
    log.debug('Done.')

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise Exception("No road specified.")
    road_name = sys.argv[1]

    log = init_logging()

    road = load_road(road_name)

    if not os.path.exists(IMAGE_DIR):
        log.debug("Creating image directory `%s`...", IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    main()