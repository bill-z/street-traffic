import math

import cv2
import numpy as np

# https://stackoverflow.com/questions/36254452/counting-cars-opencv-python-issue/36274515#36274515

MATCH_COLOR = (255, 0, 0)
UNION_COLOR = (255, 0, 255)
NEW_RECT_COLOR = (0, 255, 0)
LAST_RECT_COLOR = (0, 0, 255)

# =============================================================================
class Vehicle (object):
    def __init__ (self, id, rect, start_frame, log):
        self.id = id
        x, y, w, h = rect
        position = (x+w//2, y+h)
        self.positions = [position]
        self.rects = [rect]
        self.frames_since_seen = 0
        self.start_frame = start_frame
        self.log = log
        self.mph = 0
        self.pixel_speed = 0

        if (position[0] <= 100):
        	self.direction = 1
        elif (position[0] >= 980):
        	self.direction = -1
        else:
        	self.direction = 0

        # assign a random color for the car
        self.color = (np.random.randint(255), np.random.randint(255), np.random.randint(255))

    @property
    def last_position (self):
        return self.positions[-1]

    def age (self, frame_number):
        return frame_number - self.start_frame

    def add_position (self, new_position, new_rect):
        self.positions.append(new_position)
        self.rects.append(new_rect)
        self.frames_since_seen = 0

    @staticmethod
    def get_distance (a, b):
        dx = float(b[0] - a[0])
        dy = float(b[1] - a[1])
        return math.sqrt(dx**2 + dy**2)

    @staticmethod
    def is_valid_distance (distance):
        return distance <= 300

    @staticmethod
    def rects_overlap(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        ax2 = ax + aw
        bx2 = bx + bw

        # expand a on left and right
        ax -= 200
        ax2 += 200

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

    def find_match (self, matches, frame_number, image):
        vrect = self.rects[-1]
        vx, vy, vw, vh = vrect
        new = (0, 0, 0, 0)
        match_count = 0
        matched = []
        self.log.debug("%04d [%d]   (%d, %d, %d, %d) rect", frame_number, self.id, vx, vy, vw, vh)

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

                self.log.debug("     [%d]   (%d, %d) match", self.id, x, x+w)
                cv2.rectangle(image, (x, y), (x+w-1, y+h-1), MATCH_COLOR)
                
                if (match_count > 1):
                    x, y, w, h = new
                    self.log.debug("     [%d]   (%d, %d) union", self.id, x, x+w)
                    cv2.rectangle(image, (x, y), (x+w-1, y+h-1), UNION_COLOR)

        if match_count > 0:     
            # delete matched matches (from highest to lowest index, to keep indices valid)
            matched.reverse()
            for m in matched:
                del matches[m]

            x, y, w, h = new
            self.add_position((x, y+h), new)

            # # update vehicle position/rect
            # nx, ny, nw, nh = new
            # if nw < vw:
            #     # width shouldn't shrink, so vehicle must be behind something

            #     # which end is hidden?
            #     # lock in to the edge moving closest to previous speed
            #     dl = abs(vx - nx)
            #     dleft = abs(dl - self.pixel_speed)
            #     dr = abs((vx+vw) - (nx+nw))
            #     dright = abs(dr - self.pixel_speed)

            #     self.log.debug("     [%d]   vx %d vy %d vw %d vh %d", self.id, vx, vy, vw, vh)
            #     self.log.debug("     [%d]   nx %d ny %d nw %d nh %d", self.id, nx, ny, nw, nh)
            #     self.log.debug("     [%d]   dl %d dr %d sp %d", self.id, dl, dr, self.pixel_speed)

            #     if dleft < dright:
            #         nx = nx
            #     else:
            #         nx = nx + nw - vw
            #         if nx < 0:
            #             nx = 0

            #     nw = vw
            #     # TODO check > 1080

            # # use leading/front edge as position    
            # if (self.direction > 0):
            #     xpos = nx + nw
            # else:
            #     xpos = nx
            # self.add_position((xpos, ny+nh), (nx, ny, nw, nh))

        else:
            # print('No matches found for vehicle %s' % vehicle.id)
            self.frames_since_seen += 1

        return matches

    def calc_speed(self, frame_number, fps):
        if len(self.positions) < 2:
            self.mph = 0
            self.pixel_speed = 0
            return

        self.pixel_speed = self.get_distance(self.positions[-1], self.positions[-2])
        miles = self.pixel_speed / 10 / 5280  # wild guess of 10px/ft, 5280 ft/mi)

        frames = (frame_number - self.start_frame)
        seconds = frames / fps
        # Convert to bz

        hours = seconds / 60 / 60

        # MPH
        self.mph = 0 if hours == 0 else miles / hours

    def draw (self, output_image):
        for point in self.positions:
            cv2.circle(output_image, point, 2, self.color, -1)
            cv2.polylines(output_image, [np.int32(self.positions)], False, self.color, 1)

        x, y = self.last_position
        cv2.putText(output_image, ("[%d]" % self.id), (x, y-20), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
        cv2.putText(output_image, ("%3.2f" % self.mph), (x, y+20), cv2.FONT_HERSHEY_PLAIN, 1.0, self.color, 1)

        # previous rect
        if len(self.rects) > 1:
            x, y, w, h = self.rects[-2]
            cv2.rectangle(output_image, (x, y), (x+w-1, y+h-1), LAST_RECT_COLOR)

        # current rect
        x, y, w, h = self.rects[-1]
        cv2.rectangle(output_image, (x, y), (x+w-1, y+h-1),  NEW_RECT_COLOR)
            
    def write_log(self, frame_number):
        x, y, w, h = self.rects[-1]
        dir = ('<' if self.direction < 0 else '>')
        self.log.debug("%04d [%d] %c (%d %d %d %d) mph: %3.2f start: %d since: %d", 
            frame_number,
            self.id, 
            dir,
            x, y, w, h,
            self.mph,
            self.start_frame,
            self.frames_since_seen)


# =============================================================================
class Tracker (object):
    def __init__(self, width, height, fps, log):
        self.width = width
        self.height = height
        self.fps = fps
        self.log = log

        self.vehicles = []
        self.next_vehicle_id = 0
        self.vehicle_count = 0
        self.max_unseen_frames = 10


    def track (self, matches, frame_number, output_image=None):
        # Pair new matches with vehicles
        for vehicle in self.vehicles:
            matches = vehicle.find_match(matches, frame_number, output_image)

            vehicle.calc_speed(frame_number, self.fps)
            vehicle.write_log(frame_number)

            if output_image is not None:
                vehicle.draw(output_image)

        # Remove vehicles that have not been seen in a while
        removed = [v.id for v in self.vehicles
            if (v.frames_since_seen >= self.max_unseen_frames
                or (v.direction < 0 and v.last_position[0] <= 0) 
                or (v.direction > 0 and v.last_position[0] >= 1080)
            )]

        self.vehicles[:] = [v for v in self.vehicles
            if not (v.frames_since_seen >= self.max_unseen_frames
                or (v.direction < 0 and v.last_position[0] <= 0)
                or (v.direction > 0 and v.last_position[0] >= 1080)
            )]
    
        for id in removed:
            self.log.debug("%04d [%d] REMOVE", frame_number, id)

        # Check remaining matches for new vehicles
        MIN_VEHICLE_WIDTH = 80
        MIN_VEHICLE_HEIGHT = 40
        for match in matches:	
            x, y, w, h = match		

            if w > MIN_VEHICLE_WIDTH and h > MIN_VEHICLE_HEIGHT:
                # only allow new vehicles near left and right edges of frame
                if x < 100 or x > 980: 
                    new_vehicle = Vehicle(self.next_vehicle_id, match, frame_number, self.log)
                    self.log.debug("%04d [%d] ADD %d %d %d %d", 
                        frame_number,
                        self.next_vehicle_id, 
                        x, y, w, h)
                    self.next_vehicle_id += 1
                    self.vehicles.append(new_vehicle)

        return len(self.vehicles)
