import cv2

# =============================================================================
class Detector (object):
    def __init__(self, initial_bg, log):
        self.log = log;
        self.bg_subtractor = cv2.createBackgroundSubtractorKNN(history=10, dist2Threshold=100.0, detectShadows=False)
        # bg_subtractor = cv2.createBackgroundSubtractorMOG2()
        self.log.debug("Pre-training the background subtractor...")
        if initial_bg is not None and initial_bg.size:
            self.bg_subtractor.apply(initial_bg, None, 1.0)

    # -----------------------------------------------------------------------------
    def detect(self, frame):
        mask = self.process_mask(frame, self.bg_subtractor)
        matches = self.find_matches(mask)
        return matches, mask

    # -----------------------------------------------------------------------------
    def filter_mask (self, mask):
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
    def process_mask(self, frame, bg_subtractor):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        mask = self.bg_subtractor.apply(gray)
        mask = self.filter_mask(mask)

        return mask

    # -----------------------------------------------------------------------------
    def find_matches (self, mask):
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
