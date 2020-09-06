import math

import cv2
import numpy as np

# https://stackoverflow.com/questions/36254452/counting-cars-opencv-python-issue/36274515#36274515

# =============================================================================
class Vehicle (object):
    def __init__ (self, carid, position, start_frame):
        self.id = carid
        
        self.positions = [position]
        self.frames_since_seen = 0
        self.counted = False
        self.start_frame = start_frame
        self.speed = 0

        # if (position[0] <= 100):
        # 	self.direction = 1
        # elif (position[0] >= 980):
        # 	self.direction = -1
        # else:
        # 	self.direction = 0

        # assign a random color for the car
        self.color = (np.random.randint(255), np.random.randint(255), np.random.randint(255))

    @property
    def last_position (self):
        return self.positions[-1]
    
    def add_position (self, new_position):
        self.positions.append(new_position)
        self.frames_since_seen = 0

    @staticmethod
    def get_distance (a, b):
        dx = float(b[0] - a[0])
        dy = float(b[1] - a[1])
        return math.sqrt(dx**2 + dy**2)

    def calc_speed(self, frame_number, fps):
        pixels = self.get_distance(self.last_position, self.positions[0])
        miles = pixels / 10 / 5280  # wild guess of 10px/ft, 5280 ft/mi)

        frames = (frame_number - self.start_frame)
        seconds = frames / fps
        # Convert to hours
        hours = seconds / 60 / 60

        # MPH
        self.speed = 0 if hours == 0 else miles / hours

    def draw (self, output_image):
        for point in self.positions:
            cv2.circle(output_image, point, 2, self.color, -1)
            cv2.polylines(output_image, [np.int32(self.positions)], False, self.color, 1)

        x, y = self.last_position
        cv2.putText(output_image, ("[%d]" % self.id), (x, y-20), cv2.FONT_HERSHEY_PLAIN, 1.0, self.color, 1)
        cv2.putText(output_image, ("%3.2f" % self.speed), (x, y+20), cv2.FONT_HERSHEY_PLAIN, 1.0, self.color, 1)
            
    def log(self, log, frame_number):
        log.debug("%04d [%d] pos: %d %d speed: %3.2f start: %d since: %d", 
            frame_number,
            self.id, 
            self.last_position[0],
            self.last_position[1],
            self.speed,
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
        self.max_unseen_frames = 30

    @staticmethod
    def is_valid_distance (distance):
        return distance <= 300

    def find_match_for_vehicle (self, vehicle, matches):
        # Find if any of the matches fits this vehicle
        for i, match in enumerate(matches):
            x, y, w, h = match
            position = (x+w//2, y+h)
            distance = vehicle.get_distance(vehicle.last_position, position)
            if self.is_valid_distance(distance):
                vehicle.add_position(position)
                return i

        # No matches fit
        # print('No matches found for vehicle %s' % vehicle.id)
        vehicle.frames_since_seen += 1

        return None

    def track (self, matches, frame_number, output_image=None):

        # Pair new matches with vehicles
        for vehicle in self.vehicles:
            i = self.find_match_for_vehicle(vehicle, matches)
            if i is not None:
                del matches[i]

            vehicle.calc_speed(frame_number, self.fps)
            vehicle.log(self.log, frame_number)

            if output_image is not None:
                vehicle.draw(output_image)

        # Remove vehicles that have not been seen in a while
        removed = [v.id for v in self.vehicles
            if v.frames_since_seen >= self.max_unseen_frames
                or v.last_position[0] < 100
                or v.last_position[0] > 980
                or v.speed < 0.1]

        self.vehicles[:] = [v for v in self.vehicles
            if not (v.frames_since_seen >= self.max_unseen_frames
                or v.last_position[0] < 100
                or v.last_position[0] > 980
                or v.speed < 0.1)]
    
        for carid in removed:
            self.log.debug('Removed vehicle %d', carid)

        # Check remaining matches for new vehicles
        for match in matches:	
            x, y, w, h = match
            position = (x+w// 2, y+h)		

            if position[0] < 100 or position[0] > 980: 
                new_vehicle = Vehicle(self.next_vehicle_id, position, frame_number)
                self.log.debug('Added vehicle %d', self.next_vehicle_id)
                self.next_vehicle_id += 1
                self.vehicles.append(new_vehicle)

        return len(self.vehicles)
