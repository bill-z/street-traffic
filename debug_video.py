import cv2

class DebugVideo (object):
    def __init__(self, filename, width, height, fps, log):
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        log.debug("w: %d h: %d fps: %d", width, height, fps)
        self.video_out = cv2.VideoWriter(filename, fourcc, round(fps), (round(width), round(height)), isColor=True)
        # self.video_out.open(filename, fourcc, fps, (width, height), isColor=True)
        if not self.video_out.isOpened():
            log.debug("video_out.open() failed")

    def write(self, image):
        self.video_out.write(image)

    def release(self):
        log.debug('Closing video output...')
        self.video_out.release()

