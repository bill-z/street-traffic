import cv2
import numpy as np

from datetime import datetime
from enum import Enum

PIXELS_PER_FOOT = 4.1
FEET_PER_MILE = 5280
PIXELS_PER_MILE = PIXELS_PER_FOOT * FEET_PER_MILE
SECONDS_PER_HOUR = 3600

MIN_FEET_OF_TRAVEL = 100

NEW_RECT_COLOR = (0, 255, 0)

class Vehicle ():
    'A vehicle being tracked as it moves through a video frame.'

    class State(Enum):
        'Current state of vehicle'
        NEW = 'new' # entered frame, but not crossed start line
        ACTIVE = 'active' # crossed start but not stop line
        DONE = 'done' # crossed stop line and has speed results

    def __init__ (self, vehicle_id, direction, rect, start_frame, log):
        self.id = vehicle_id
        self.direction = direction
        self.rects = [rect]
        self.start_frame = start_frame
        self.log = log

        self.state = Vehicle.State.NEW
        self.frames_since_seen = 0
        self.mph = 0
        self.pixel_speed = 0
        self.speed_start_x = None
        self.speed_start_frame = None
        self.speed_start_time = None
        self.center_frame = None
        self.done_frame = None
        self.photo = None

        # assign a random color for the car
        self.color = (np.random.randint(255), np.random.randint(255), np.random.randint(255))

    @property
    def last_position (self):
        'Most recent x,y postion'
        x, y, w, h = self.rects[-1]
        if self.direction > 0:
            return (x+w, y+h)
        else:
            return (x, y+h)

    def age (self, frame_number):
        'Vehicle age in frames'
        return frame_number - self.start_frame

    def add_position (self, new_rect):
        'Add current postion rectangle to position rectangle history'
        self.rects.append(new_rect)
        self.frames_since_seen = 0

    @staticmethod
    def rects_overlap_in_x(a, b):
        'True if two rects overlap in x'
        ax, _ay, aw, _ah = a
        bx, _by, bw, _bh = b
        ax2 = ax + aw
        bx2 = bx + bw

        # check for overlap in x
        return ax2 > bx and ax < bx2

    @staticmethod
    def union(a, b):
        'Returns the union of two rectangles'
        ax, ay, aw, ah = a
        ax2 = ax + aw
        ay2 = ay + ah

        bx, by, bw, bh = b
        bx2 = bx + bw
        by2 = by + bh

        x = min(ax, bx)
        y = min(ay, by)
        w = max(ax2, bx2) - x
        h = max(ay2, by2) - y

        return (x, y, w, h)

    def find_match (self, matches):
        'Based on position in last frame, identify new objects that appear to be same Vehicle'
        vrect = self.rects[-1]
        new = (0, 0, 0, 0)
        match_count = 0
        matched = []

        # extend rect in front of vehicle to catch returning from behind trees/posts
        EXTEND = 50
        x, y, w, h = vrect

        if self.direction > 0:
            w = w + EXTEND
        else:
            x = x - EXTEND   # TODO: clamp to 0?
            w = w + EXTEND
        vrect = (x, y, w, h)

        # Find matches for this vehicle
        # Create a union of all matches that overlap with the previous position
        for i, match in enumerate(matches):
            x, y, w, h = match

            if self.rects_overlap_in_x(vrect, match):
                if match_count == 0:
                    new = match
                else:
                    new = self.union(new, match)
                match_count += 1
                matched.append(i)

        if len(matched) > 0:
            # Delete matched matches from available matches list
            # (from highest to lowest index, to keep indices valid)
            matched.reverse()
            for m in matched:
                del matches[m]

            x, y, w, h = new
            self.add_position(new)

        else:
            self.frames_since_seen += 1

        return matches

    def start_speed(self, frame_number):
        'Start speed measurements'
        if self.state is not Vehicle.State.NEW:
            self.log.warning('start_speed: state is not new')
            return

        self.state = Vehicle.State.ACTIVE
        x, _y = self.last_position
        self.speed_start_x = x
        self.speed_start_frame = frame_number
        self.speed_start_time = datetime.now()       

    def stop_speed(self, frame_number, fps):
        'Stop and save speed measurements'

        # distance
        x, _y = self.last_position
        pixels = abs(x - self.speed_start_x)
        feet = pixels / PIXELS_PER_FOOT
        miles = pixels / PIXELS_PER_MILE

        # speed based on clock time
        dt = datetime.now() - self.speed_start_time
        clock_secs = dt.seconds + dt.microseconds / 1000000
        if clock_secs > 0:
            clock_hours = clock_secs / SECONDS_PER_HOUR
            cmph = miles / clock_hours
        else:
            self.log.debug('Vehicle.stop_speed: clock_secs = 0')
            clock_hours = 0
            cmph = 0

        if feet > MIN_FEET_OF_TRAVEL:
            self.mph = cmph

            self.log.debug('%d [%d] %c mph:%2.1f  p:%d (%d->%d), ft:%3.1f m:%1.4f s:%3.2f h:%1.6f',
                frame_number,
                self.id,
                '>' if self.direction > 0 else '<',
                cmph,
                pixels,
                self.speed_start_x,
                x,
                feet,
                miles,
                clock_secs,
                clock_hours)
        else:
            self.mph = 0

        self.state = Vehicle.State.DONE
        self.done_frame = frame_number
        
    def draw (self, output_image):
        'Draw vehicle tracking on image'

        path = []
        for rect in self.rects:
            point = (rect[0], rect[1]+rect[3])
            path.append(point)
            cv2.circle(output_image, point, 2, self.color, -1)
        cv2.polylines(output_image, [np.int32(path)], False, self.color, 1)

        x, y = self.last_position
        cv2.putText(output_image,
            ('[%d]' % self.id), (x, y-20), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
        cv2.putText(output_image,
            ('%3.2f' % self.mph), (x, y+20), cv2.FONT_HERSHEY_PLAIN, 1.0, self.color, 1)

        # current rect
        x, y, w, h = self.rects[-1]
        cv2.rectangle(output_image, (x, y), (x+w-1, y+h-1),  NEW_RECT_COLOR)

    def track(self, matches, _frame_number, _fps, output_image):
        'Track motion associated this vehicle'
        
        matches = self.find_match(matches)

        if output_image is not None:
            self.draw(output_image)

        return matches
