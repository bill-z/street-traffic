import cv2

class DebugVideo (object):
    def __init__(self, width, height, fps, log):
        self.log = log
        filename = 'output.mov'
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        log.debug("output w: %d h: %d fps: %d", width, height, fps)

        self.video_out = cv2.VideoWriter(filename, fourcc, round(fps), (round(width), round(height)), isColor=True)
        # self.video_out.open(filename, fourcc, fps, (width, height), isColor=True)
        if not self.video_out.isOpened():
            log.debug("video_out.open() failed")

    def write(self, image):
        self.video_out.write(image)

    def release(self):
        self.log.debug('Closing video output...')
        self.video_out.release()

