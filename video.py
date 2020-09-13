import time
import cv2

from imutils.video import FileVideoStream

class VideoSource (object):
    def __init__ (self, video_file, log):
        self.filename = video_file
        self.log = log

    def start (self):
        if self.filename is not None:
            self.log.debug("Video file: %s ", self.filename)
            self.fvs = FileVideoStream(self.filename).start()
            self.stream = self.fvs.stream;
            time.sleep(1.0)
        else: 
            self.log.debug("Using camera")
            self.stream = cv2.VideoCapture(0)
            self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)

        self.width = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.fps = self.stream.get(cv2.CAP_PROP_FPS)

        return self.width, self.height, self.fps

    def stop (self):
        if self.filename:
            self.fvs.stop()
        else:
            self.stream.release()
        self._done = True

    def done(self):
        # check to see if video is still running
        running = (self.filename and self.fvs.running()) or True
        self._done = not running
        return self._done

    def read(self):
        if self.filename:
            frame = self.fvs.read()
        else:
            result, frame = self.stream.read()
        return frame

