import os
import argparse
from datetime import datetime

import cv2

from log import Log
from detector import Detector
from tracker import Tracker
from video import VideoSource

LOG_TO_FILE = True

IMAGE_DIR = 'images'
PHOTO_DIR = 'photos'

# (arbitrary) maximum value used before wrapping to zero 
MAX_FRAME_NUMBER = 1000000

# Time to wait between frames, 0=forever
WAIT_TIME = 1 # 250 # ms

# Colors for drawing on processed frames
BOUNDING_BOX_COLOR = (255, 0, 0)
RED = (20, 20, 255)
BLACK = (10, 10, 10)

SPEED_LIMIT = 25

VIDEO_RESOLUTION = (640, 360)
VIDEO_FRAME_RATE = 30

# Define an area of the video frame to be observed. 
#  Keep the center vertical ~third of the frame, and the full width.
#  (x, y, w, h)
AREA_OF_INTEREST = (0, 108, 640, 70)

# -----------------------------------------------------------------------------
def save_frame(frame_number, frame, most_recent_vehicle):
    'Save a video frame to an image file'
    file_name = '%s/frame_%05d_%04d.png' % (IMAGE_DIR, frame_number, most_recent_vehicle)

    # draw the timestamp on the frame
    timestamp = datetime.now()
    ts = timestamp.strftime('%A %d %B %Y %I:%M:%S%p')
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.35, (0, 0, 255), 1)

    # log.debug("Saving %s as '%s'", label, file_name)
    cv2.imwrite(file_name, frame)

# -----------------------------------------------------------------------------
def save_vehicle_photo (vehicle):
    'Save vehicle photo (with vehicle data) to an image file'

    if vehicle.photo is None:
        log.debug('no photo %d' % vehicle.id)
        return

    if vehicle.mph <= 0:
        log.debug('vehicle (%d) speed (%2.1f) <= 0' % (vehicle.id, vehicle.mph))
        # TODO: save photo to errors/debug folder
        return

    log.debug('save photo %d %d' % (vehicle.id, vehicle.center_frame))

    photo = vehicle.photo

    # draw date and time on photo image
    now = datetime.now()
    text = now.strftime('%a %b %d %Y %H:%M')
    position = (5, 10)
    scale = 0.25
    color = BLACK
    thickness = 1
    cv2.putText(photo, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    # draw speed on photo image
    text = '%2.1f' % (vehicle.mph)
    position = (10, 35)
    scale = 0.75
    color = RED if vehicle.mph > SPEED_LIMIT else BLACK
    thickness = 2
    cv2.putText(photo, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    # embed data in photo filename
    # use utc time
    utcnow = datetime.utcnow()
    time = utcnow.strftime('%Y-%m-%d-%H-%M-%S')
    speed = vehicle.mph
    direction = 'S' if vehicle.direction > 0 else 'N'  # TODO: make configurable
    vehicle_type = 'V' # for now - more to be defined in future
    file_name = '%s/%s_%2.1f_%c_%c_%d_%d.png' % (
        PHOTO_DIR, time, speed, direction, vehicle_type, vehicle.center_frame, vehicle.id)

    # log.debug("Saving %s as '%s'", label, file_name)
    cv2.imwrite(file_name, photo)

      
# -----------------------------------------------------------------------------
def crop (frame):
    'Crop to frame region of interest'
    x, y, w, h = AREA_OF_INTEREST
    return (frame[y:y+h, x:x+w] if frame is not None else None)

# -----------------------------------------------------------------------------
def get_vehicle_photo (frame):
    'Save center third of frame image as vehicle photo'
    h, w, _c = frame.shape
    new_x = round(w / 3)
    new_w = round(w / 3)
    return (frame[0:h, new_x:new_x+new_w]).copy() if frame is not None else None

# -----------------------------------------------------------------------------
def main ():
    'Street Traffic monitor application'

    resolution = VIDEO_RESOLUTION
    framerate = VIDEO_FRAME_RATE

    video = VideoSource(
        VIDEO_FILE, log, use_pi_camera=use_pi_camera, resolution=resolution, 
        framerate=framerate, night=use_night_mode
    )
    (_width, _height), framerate = video.start()

    initial_bg = video.read()
    detector = Detector(initial_bg, log)

    tracker = Tracker(resolution, framerate, log)

    frame_number = 0
    overall_start_time = datetime.now()

    while not video.done():
        frame = video.read()
        if frame is None:
            continue

        frame_number = frame_number + 1 if frame_number < MAX_FRAME_NUMBER else 0

        # Crop frame to region of interest
        cropped_frame = crop(frame)

        # Detect moving vehicle-like objects
        matches, mask = detector.detect(cropped_frame)
        
        # Track moving objects over time
        vehicles = tracker.track(matches, frame_number, resolution, cropped_frame)

        # Display current video frame and resulting object mask image stacked vertically.
        result = cv2.vconcat([cropped_frame, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)])
        cv2.imshow('Traffic', result)

        for vehicle in vehicles:

            if vehicle.center_frame == frame_number:
                # Tracked vehicle is in center of frame, extract a photo
                log.debug('get photo %d f#%d' % (vehicle.id, frame_number))
                vehicle.photo = get_vehicle_photo(cropped_frame)

            if vehicle.done_frame == frame_number:
                if vehicle.center_frame:
                    # If a center photo was 'taken', save it
                    save_vehicle_photo(vehicle)
                else:
                    log.debug('no center frame %d #f%d' % (vehicle.id, frame_number))

        key = cv2.waitKey(1)
        if key == ord('q') or key == 27:
            log.debug('ESC or q key, stopping...')
            break

    log.debug('Closing video source...')
    video.stop()

    # display overall fps
    elapsed_time = (datetime.now() - overall_start_time).total_seconds()
    fps = frame_number / elapsed_time
    log.debug('fps: %3.4f (%d / %f)', fps, frame_number, elapsed_time)

    # video_out.release()
    cv2.destroyAllWindows()
    log.debug('Done.')

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    logger = Log(LOG_TO_FILE)
    log = logger.getLog()

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--picamera', type=int, default=-1,
        help='whether or not the Raspberry Pi camera should be used')  
    ap.add_argument('-n', '--night', type=int, default=-1,
        help='1 for night mode')
    args = vars(ap.parse_args())

    use_pi_camera = args['picamera'] > 0
    if use_pi_camera:
        log.debug('Using PI Camera')

    use_night_mode = args['night'] > 0
    if use_night_mode:
        log.debug('Using night mode')

    if use_pi_camera:
        VIDEO_FILE = None
    else:
        VIDEO_FILE = 'video/testvideo2.mp4'

    if not os.path.exists(IMAGE_DIR):
        log.debug('Creating image directory `%s`...', IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    if not os.path.exists(PHOTO_DIR):
        log.debug('Creating photo directory `%s`...', PHOTO_DIR)
        os.makedirs(PHOTO_DIR)

    main()
