
import os
import argparse
import datetime

import cv2

from log import Log
from detector import Detector
from tracker import Tracker
from video import VideoSource

LOG_TO_FILE = True

IMAGE_DIR = 'images'
IMAGE_FILENAME_FORMAT = IMAGE_DIR + '/frame_%04d.png'

# Time to wait between frames, 0=forever
WAIT_TIME = 1 # 250 # ms

# Colours for drawing on processed frames 
BOUNDING_BOX_COLOR = (255, 0, 0)

# -----------------------------------------------------------------------------
def save_frame(file_name_format, frame_number, frame, label_format):
    file_name = file_name_format % frame_number
    # label = label_format % frame_number

    # draw the timestamp on the frame
    timestamp = datetime.datetime.now()
    ts = timestamp.strftime('%A %d %B %Y %I:%M:%S%p')
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.35, (0, 0, 255), 1)

    # log.debug("Saving %s as '%s'", label, file_name)
    cv2.imwrite(file_name, frame)

# -----------------------------------------------------------------------------
# Remove cropped regions from frame
def crop (frame):
    #frame = imutils.resize(frame, width=1280)
    
    # keep the center vertical third of the frame, full width (of 1280x720)
    #TODO define these "better"
    x = 0
    y = 160
    w = 540
    h = 120
    return (frame[y:y+h, x:x+w] if frame is not None else None)

# -----------------------------------------------------------------------------
def main ():
    resolution = (540, 360)
    framerate = 30

    video = VideoSource(video_file, log, usePiCamera = usePiCamera, resolution=resolution, framerate = framerate)
    (width, height), framerate = video.start()

    initial_bg = video.read()
    # initial_bg = imutils.resize(frame, width=400)

    # video_out = DebugVideo(width, 480, fps, log)

    detector = Detector(initial_bg, log)

    tracker = Tracker(width, height, framerate, log)

    frame_number = 0
    start_time = datetime.datetime.now()

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
        cv2.imshow('Traffic', result)

        # video_out.write(result)

        # if trackedObjectCount > 0:
        #     save_frame(IMAGE_FILENAME_FORMAT, frame_number, result, 'frame #%d')

        key = cv2.waitKey(WAIT_TIME)
        if key == ord('q') or key == 27:
            log.debug('ESC or q key, stopping...')
            break

    log.debug('Closing video source...')
    video.stop()

    # display fps
    end_time = datetime.datetime.now()       
    elapsed_time = (end_time - start_time).total_seconds()
    fps = frame_number / elapsed_time
    log.debug('fps: %3.4f (%d / %f)', fps, frame_number, elapsed_time)

    # video_out.release()
    cv2.destroyAllWindows()
    log.debug('Done.')

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--picamera', type=int, default=-1,
        help='whether or not the Raspberry Pi camera should be used')
    args = vars(ap.parse_args())
    usePiCamera = args['picamera'] > 0

    if usePiCamera:
        video_file = None
    else:
        video_file = 'video/testvideo2.mp4'

    log = Log(LOG_TO_FILE)
    log = log.getLog()

    if not os.path.exists(IMAGE_DIR):
        log.debug('Creating image directory `%s`...', IMAGE_DIR)
        os.makedirs(IMAGE_DIR)

    main()
