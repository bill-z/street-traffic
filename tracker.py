import math

import cv2
import numpy as np
from datetime import datetime
from enum import Enum

# https://stackoverflow.com/questions/36254452/counting-cars-opencv-python-issue/36274515#36274515

MATCH_COLOR = (255, 0, 0)
UNION_COLOR = (255, 0, 255)
NEW_RECT_COLOR = (0, 255, 0)
LAST_RECT_COLOR = (0, 0, 255)
EDGE_LINE_COLOR = (255, 255, 255)

PIXELS_PER_FOOT = 4.1
FEET_PER_MILE = 5280
PIXELS_PER_MILE = PIXELS_PER_FOOT * FEET_PER_MILE
SECONDS_PER_HOUR = 3600

MIN_FEET_OF_TRAVEL = 100

MAX_UNSEEN_FRAMES = 10

class State(Enum):
    NEW = 'new'
    ACTIVE = 'active'
    DONE = 'done'

# =============================================================================
class Vehicle ():
    def __init__ (self, vehicle_id, direction, rect, start_frame, log):
        self.id = vehicle_id
        self.direction = direction
        self.rects = [rect]
        self.start_frame = start_frame
        self.log = log
        self.state = State.NEW

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
        x, y, w, h = self.rects[-1]
        if self.direction > 0:
            return (x+w, y+h)
        else:
            return (x, y+h)

    def age (self, frame_number):
        return frame_number - self.start_frame

    def add_position (self, new_rect):
        self.rects.append(new_rect)
        self.frames_since_seen = 0

    @staticmethod
    def rects_overlap_in_x(a, b):
        ax, _ay, aw, _ah = a
        bx, _by, bw, _bh = b
        ax2 = ax + aw
        bx2 = bx + bw

        # check for overlap in x
        return ax2 > bx and ax < bx2

    @staticmethod
    def union(a, b):
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
        #   Create a union of all matches that overlap with the previous position
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
            # delete matched matches (from highest to lowest index, to keep indices valid)
            matched.reverse()
            for m in matched:
                del matches[m]

            x, y, w, h = new
            self.add_position(new)

        else:
            self.frames_since_seen += 1

        return matches

    def start_speed(self, frame_number):
        if self.state is not State.NEW:
            self.log.warning('start_speed: state is not new')
            return

        self.state = State.ACTIVE
        x, _y = self.last_position
        self.speed_start_x = x
        self.speed_start_frame = frame_number
        self.speed_start_time = datetime.now()       

    def stop_speed(self, frame_number, fps):
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

        self.state = State.DONE
        self.done_frame = frame_number
        
    def draw (self, output_image):
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
        matches = self.find_match(matches)

        if output_image is not None:
            self.draw(output_image)

        return matches

# =============================================================================
class Tracker (object):
    def __init__(self, resolution, fps, log):
        self.width = resolution[0]
        self.height = resolution[1]
        self.fps = fps
        self.log = log

        self.vehicles = []
        self.next_vehicle_id = 0
        self.vehicle_count = 0
        self.max_unseen_frames = 10

        edge_size = int(self.width * 0.10)
        self.left_edge = 0 + edge_size
        self.right_edge = self.width - edge_size

        self.min_vehicle_width = int(self.width * 0.075)
        self.min_vehicle_height = int(self.height * 0.05)

        fudge_factor = 10  # adjust center to improve output photos
        self.frame_center_x = self.width / 2 - fudge_factor

        self.log.debug('Tracker left:%d right:%d minw:%d minh:%d',
            self.left_edge, self.right_edge, self.min_vehicle_width, self.min_vehicle_height)
     
    def track (self, matches, frame_number, _resolution, output_image=None):
        # pair new matches with vehicles
        for vehicle in self.vehicles:
            matches = vehicle.track(matches, frame_number, self.fps, output_image)
            self.start_stop_speed(frame_number, vehicle)
            self.check_for_midpoint(frame_number, vehicle)

        # draw start/stop edge lines
        if output_image is not None:
            cv2.line(output_image,
                (self.left_edge, 0), (self.left_edge, self.height), EDGE_LINE_COLOR, 1)
            cv2.line(output_image,
                (self.right_edge, 0), (self.right_edge, self.height), EDGE_LINE_COLOR, 1)

        self.remove_old_vehicles(frame_number)
        self.add_new_vehicles(matches, frame_number, output_image)

        return self.vehicles

    def start_stop_speed(self, frame_number, vehicle):
        x, y, w, h = vehicle.rects[-1]

        if vehicle.state is State.NEW:
            if vehicle.direction > 0:
                if x+w > self.left_edge:
                    vehicle.start_speed(frame_number)
            else:
                if x < self.right_edge:
                    vehicle.start_speed(frame_number)

        if vehicle.state is State.ACTIVE:
            if vehicle.direction > 0:
                if x+w > self.right_edge:
                    vehicle.stop_speed(frame_number, self.fps)
            else:
                if x < self.left_edge:
                    vehicle.stop_speed(frame_number, self.fps)

    def remove_old_vehicles(self, frame_number):
        # identify vehicles to remove
        removed = []
        for v in self.vehicles:
            x, y, w, h = v.rects[-1]
            if v.frames_since_seen >= MAX_UNSEEN_FRAMES:
                removed.append(v)
                x0, y0, w0, h0 = v.rects[0]
                if v.state is State.ACTIVE:
                    self.log.warning('%d [%d] (%d %d)-(%d %d) %d %d',
                        frame_number, v.id, x0, x0+w0, x, x+w,
                        v.frames_since_seen, v.age(frame_number))

        self.vehicles[:] = [v for v in self.vehicles if v not in removed]

    def add_new_vehicles(self, matches, frame_number, output_image):
        # check remaining matches for new vehicles
        while len(matches) > 0:
            # self.log.debug('%d %d unused matches', frame_number, len(matches))
            match = matches[0]
            x, y, w, h = match

            if w > self.min_vehicle_width and h > self.min_vehicle_height:
                # only allow new vehicles near left and right edges of frame
                if x <= 0:
                    direction = 1
                elif x+w >= self.width:
                    direction = -1
                else:
                    del matches[0]
                    continue

                new_vehicle = Vehicle(
                    self.next_vehicle_id, direction, match, frame_number, self.log)
                    
                matches = new_vehicle.track(matches, frame_number, self.fps, output_image)

                self.next_vehicle_id += 1
                self.vehicles.append(new_vehicle)
            else:
                del matches[0]

    def check_for_midpoint(self, frame_number, vehicle):
        if not vehicle.center_frame:
            x, _y, w, _h = vehicle.rects[-1]
            vehicle_center_x = x + (w / 2)
            if abs(vehicle_center_x - self.frame_center_x) < 30:
                vehicle.center_frame = frame_number
                self.log.debug('center frame %d vehicle %d [%d %d] f#%d'
                    % (self.frame_center_x, vehicle_center_x, x, x+w, frame_number))