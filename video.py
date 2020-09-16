import time
import cv2

from imutils.video import FileVideoStream, VideoStream

class VideoSource (object):
    def __init__ (self, video_file, log, usePiCamera = True, resolution=(320, 200), framerate = 30):
        self.filename = video_file
        self.log = log
        self.usePiCamera = usePiCamera
        self.resolution = resolution
        self.framerate = framerate

    def start (self):
        if self.filename is not None:
            self.log.debug('Video file: %s', self.filename)
            self.fvs = FileVideoStream(self.filename).start()
            self.stream = self.fvs.stream;
            time.sleep(1.0)
        else: 
            if self.usePiCamera:
                self.log.debug('Pi Camera (%d %d)', self.resolution[0], self.resolution[1])
                self.stream = VideoStream(src=0, usePiCamera=True, resolution=self.resolution, framerate=self.framerate).start()
                self.stream.camera.rotation = 180
                # night = True
                # if night:
                #     self.stream.camera.exposure_mode = 'sports'
                #     self.stream.camera.shutter_speed = 33333
                # self.stream.camera.zoom = (0, 200, 1080, 300)
                time.sleep(1.0)
            else:
                self.log.debug('Web Camera')
                self.stream = cv2.VideoCapture(0)
                self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                self.resolution = (self.stream.get(cv2.CAP_PROP_FRAME_WIDTH), self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.framerate = self.stream.get(cv2.CAP_PROP_FPS)

        return self.resolution, self.framerate

    def read(self):
        if self.filename:
            frame = self.fvs.read()
        else:
            frame = self.stream.read()
        return frame

    def stop (self):
        if self.filename:
            self.fvs.stop()
        else:
            self.stream.stop()
        self._done = True

    def done(self):
        # check to see if video is still running
        running = (self.filename and self.fvs.running()) or True
        self._done = not running
        return self._done
