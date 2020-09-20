import cv2

# =============================================================================
class Detector (object):
    def __init__(self, initial_bg, log):
        self.log = log
        # self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        #   history=1, varThreshold=3.0, detectShadows=False)
        self.bg_subtractor = cv2.createBackgroundSubtractorKNN(
                history=1, dist2Threshold=25.0, detectShadows=False)
        self.log.debug("Pre-training the background subtractor...")
        if initial_bg is not None and initial_bg.size:
            self.bg_subtractor.apply(initial_bg, None, 1.0)

    # -----------------------------------------------------------------------------
    def detect(self, frame):
        mask = self.process_mask(frame)
        matches = self.find_matches(mask)
        return matches, mask

    # -----------------------------------------------------------------------------
    def filter_mask (self, mask):
        # kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        # kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (16, 16))
        # kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 8))

        # Remove noise
        # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open, iterations = 1)
        mask = cv2.erode(mask, kernel_open, iterations = 1)

        # Close holes within contours
        # mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations = 2)
        mask = cv2.dilate(mask, kernel_close, iterations = 1)

        return mask

    # -----------------------------------------------------------------------------
    def process_mask(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = self.bg_subtractor.apply(gray)
        mask = self.filter_mask(mask)
        return mask

    # -----------------------------------------------------------------------------
    def find_matches (self, mask):
        # MIN_CONTOUR_WIDTH = 30
        # MIN_CONTOUR_HEIGHT = 20
        # MAX_CONTOUR_WIDTH = 540
        # MAX_CONTOUR_HEIGHT = 200
        MIN_CONTOUR_WIDTH = 18
        MIN_CONTOUR_HEIGHT = 10
        MAX_CONTOUR_WIDTH = 320
        MAX_CONTOUR_HEIGHT = 100

        # contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        matches = []

        # Hierarchy stuff:
        # https://stackoverflow.com/questions/11782147/python-opencv-contour-tree-hierarchy
        for (i, contour) in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            contour_valid = (w >= MIN_CONTOUR_WIDTH and
                h >= MIN_CONTOUR_HEIGHT and
                w <= MAX_CONTOUR_WIDTH and
                h <= MAX_CONTOUR_HEIGHT)

            if not contour_valid or not hierarchy[0,i,3] == -1:
                continue

            matches.append((x,y,w,h))

        return matches

    # -----------------------------------------------------------------------------
    def draw_matches(self, matches, mask):
        for (i, match) in enumerate(matches):
            x,y,w,h = match
            cv2.rectangle(mask, (x,y), (x+w-1, y+h-1), (128, 128, 128), 1)

        return mask
