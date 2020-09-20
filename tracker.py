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

PIXELS_PER_FOOT = 5 # wild guess
FEET_PER_MILE = 5280
PIXELS_PER_MILE = PIXELS_PER_FOOT * FEET_PER_MILE
SECONDS_PER_HOUR = 3600

MAX_UNSEEN_FRAMES = 10

class State(Enum):
    NEW = 'new'
    ACTIVE = 'active'
    DONE = 'done'

# =============================================================================
class Vehicle (object):
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
    def get_distance (a, b):
        dx = float(b[0] - a[0])
        dy = float(b[1] - a[1])
        return math.sqrt(dx**2 + dy**2)

    @staticmethod
    def is_valid_distance (distance):
        return distance <= 200

    @staticmethod
    def rects_overlap(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2 = ax + aw
        bx2 = bx + bw

        # # expand a on left and right
        # ax -= 100
        # ax2 += 100

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
        # self.log.debug("%d [%d]   (%d, %d, %d, %d) rect", frame_number, self.id, vx, vy, vw, vh)

        # extend rect in front of vehicle to catch returning from behind trees/posts
        EXTEND = 50
        x, y, w, h = vrect
        # self.log.debug('vrect:  (%d %d %d %d)', x, y, w, h)
        if self.direction > 0:
            w = w + EXTEND
        else:
            x = x - EXTEND   # TODO: clamp to 0?
            w = w + EXTEND
        vrect = (x, y, w, h)
        # self.log.debug('vrect+: (%d %d %d %d)', x, y, w, h)

        # for m in matches:
        #     x, y, w, h = m
        #     self.log.debug('     [%d] before: (%d %d %d %d)', self.id, x, y, w, h)

        # Find matches for this vehicle
        #   Create a union of all matches that overlap with the previous position
        for i, match in enumerate(matches):
            x, y, w, h = match

            if self.rects_overlap(vrect, match):
                if match_count == 0:
                    new = match
                else:
                    new = self.union(new, match)
                match_count += 1
                matched.append(i)

                # self.log.debug("     [%d] match[%d] (%d %d %d %d) ", self.id, i, x, y, w, h)
                # cv2.rectangle(image, (x, y), (x+w-1, y+h-1), MATCH_COLOR)
                
                # if (match_count > 1):
                #     x, y, w, h = new
                #     self.log.debug("     [%d]   (%d, %d) union", self.id, x, x+w)
                #     cv2.rectangle(image, (x, y), (x+w-1, y+h-1), UNION_COLOR)

        if len(matched) > 0:     
            # delete matched matches (from highest to lowest index, to keep indices valid)
            matched.reverse()
            for m in matched:
                # x, y, w, h = matches[m]
                # self.log.debug('     [%d] remove[%d]: (%d %d %d %d)', self.id, m, x, y, w, h)
                del matches[m]

            x, y, w, h = new
            self.add_position(new)

        else:
            # print('No matches found for vehicle %s' % vehicle.id)
            self.frames_since_seen += 1

        # for m in matches:
        #     x, y, w, h = m
        #     self.log.debug('     [%d] after: (%d %d %d %d)', self.id, x, y, w, h)
        return matches

    def calc_speed(self, frame_number, fps):
        if len(self.rects) < 2:
            self.mph = 0
            self.pixel_speed = 0
            return

        self.pixel_speed = self.get_distance(self.rects[-1], self.rects[-2])
        miles = self.pixel_speed / PIXELS_PER_FOOT / FEET_PER_MILE  #  5280 ft/mi)

        frames = (frame_number - self.start_frame)
        seconds = frames / fps
        hours = seconds / SECONDS_PER_MINUTE / MINUTES_PER_HOUR

        # MPH
        self.mph = 0 if hours == 0 else miles / hours

    def start_speed(self, frame_number):
        if self.state is not State.NEW:
            self.log.warning('start_speed: state is not new')
            return

        self.state = State.ACTIVE
        x, y = self.last_position
        self.speed_start_x = x
        self.speed_start_frame = frame_number
        self.speed_start_time = datetime.now()       
        r = self.rects[-1]
        rx1 = r[0]
        rx2 = rx1 + r[2]
        # self.log.debug('%d [%d] start %d (%d %d)', 
        #     frame_number, self.id, self.speed_start_x, rx1, rx2)

    def stop_speed(self, frame_number, fps):
        # distance
        x, y = self.last_position
        pixels = abs(x - self.speed_start_x)
        feet = pixels / PIXELS_PER_FOOT
        miles = pixels / PIXELS_PER_MILE

        # speed based on frame time
        frames = frame_number - self.speed_start_frame
        frame_secs = frames / fps
        frame_hours = frames / fps / SECONDS_PER_HOUR
        fmph = miles / frame_hours

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

        self.state = State.DONE
 
        self.log.debug('%d [%d] %c mph:%2.1f  p:%d (%d->%d), ft:%3.1f m:%1.4f fmph:%2.1f frames:%d fs:%3.2f s:%3.2f h:%1.6f', 
            frame_number,
            self.id, 
            '>' if self.direction > 0 else '<',
            cmph,
            pixels,
            self.speed_start_x,
            x,
            feet,
            miles,
            fmph,
            frames,
            frame_secs,
            clock_secs,
            clock_hours)

    def draw (self, output_image):
        path = []
        for rect in self.rects:
            point = (rect[0], rect[1])
            path.append(point) 
            cv2.circle(output_image, point, 2, self.color, -1)
        cv2.polylines(output_image, [np.int32(path)], False, self.color, 1)

        x, y = self.last_position
        cv2.putText(output_image, 
            ('[%d]' % self.id), (x, y-20), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
        cv2.putText(output_image, 
            ('%3.2f' % self.mph), (x, y+20), cv2.FONT_HERSHEY_PLAIN, 1.0, self.color, 1)

        # previous rect
        # if len(self.rects) > 1:
        #     x, y, w, h = self.rects[-2]
        #     cv2.rectangle(output_image, (x, y), (x+w-1, y+h-1), LAST_RECT_COLOR)

        # current rect
        x, y, w, h = self.rects[-1]
        cv2.rectangle(output_image, (x, y), (x+w-1, y+h-1),  NEW_RECT_COLOR)
           
    def write_log(self, frame_number):
        x, y, w, h = self.rects[-1]
        dir = ('<' if self.direction < 0 else '>')
        self.log.debug('%d [%d] %c (%d %d %d %d) mph: %3.2f start: %d since: %d', 
            frame_number,
            self.id, 
            dir,
            x, y, w, h,
            self.mph,
            self.start_frame,
            self.frames_since_seen)

    def track(self, matches, frame_number, fps, output_image):
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

        self.log.debug('Tracker left:%d right:%d minw:%d minh:%d', 
            self.left_edge, self.right_edge, self.min_vehicle_width, self.min_vehicle_height)
        
    def track (self, matches, frame_number, resolution, output_image=None):
        # Pair new matches with vehicles
        for vehicle in self.vehicles:
            matches = vehicle.track(matches, frame_number, self.fps, output_image)
            self.start_stop_speed(frame_number, vehicle);

        # draw start/stop edge lines
        if output_image is not None:
            cv2.line(output_image,
                (self.left_edge, 0), (self.left_edge, self.height), EDGE_LINE_COLOR, 1)
            cv2.line(output_image,
                (self.right_edge, 0), (self.right_edge, self.height), EDGE_LINE_COLOR, 1)

        self.remove_old_vehicles(frame_number)
        self.add_new_vehicles(matches, frame_number, output_image)

        if len(self.vehicles) > 0:
            return self.vehicles[-1].id
        else: 
            return 0

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
            dir = v.direction
            x, y, w, h = v.rects[-1]
            if (v.frames_since_seen >= MAX_UNSEEN_FRAMES):
                removed.append(v)
                x0, y0, w0, h0 = v.rects[0]
                if v.state is State.ACTIVE:
                    self.log.warning('%d [%d] (%d %d)-(%d %d) %d %d', 
                        frame_number, v.id, x0, x0+w0, x, x+w,
                        v.frames_since_seen, v.age(frame_number))

        # Remove vehicles that are done from vehicles list
        # removed = [v.id for v in self.vehicles if v.done]
        self.vehicles[:] = [v for v in self.vehicles if v not in removed]

    def add_new_vehicles(self, matches, frame_number, output_image):
        # Check remaining matches for new vehicles
        while len(matches) > 0:
            # self.log.debug('%d %d unused matches', frame_number, len(matches))
            match = matches[0]
            x, y, w, h = match

            if w > self.min_vehicle_width and h > self.min_vehicle_height:
                # only allow new vehicles near left and right edges of frame
                if x <= 0:
                    dir = 1
                elif x+w >= self.width:
                    dir = -1
                else:
                    del matches[0]
                    continue

                new_vehicle = Vehicle(self.next_vehicle_id, dir, match, frame_number, self.log)
                matches = new_vehicle.track(matches, frame_number, self.fps, output_image)
                    
                # self.log.debug('%d [%d] ADD %c (%d %d %d %d) %d', 
                #     frame_number,
                #     self.next_vehicle_id, 
                #     '>' if dir > 0 else '<',
                #     x, y, w, h, len(matches))
                
                # for m in matches:
                #     x, y, w, h = m
                #     self.log.debug('(%d %d %d %d)', x, y, w, h)

                self.next_vehicle_id += 1
                self.vehicles.append(new_vehicle)
            else:
                del matches[0]
