import cv2

from vehicle import Vehicle

# inspired by: 
# https://stackoverflow.com/questions/36254452/counting-cars-opencv-python-issue/36274515#36274515

EDGE_LINE_COLOR = (255, 255, 255)

MAX_UNSEEN_FRAMES = 10

class Tracker (object):
    'Track moving vehicle objects as they travel through a sequence of video frames'

    def __init__(self, resolution, fps, log):
        self.width = resolution[0]
        self.height = resolution[1]
        self.fps = fps
        self.log = log

        self.vehicles = []
        self.next_vehicle_id = 0
        self.vehicle_count = 0

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
        'Associate moving image changes with vehicles'

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
        'Check if vehicle speed measurements should start or stop'

        x, y, w, h = vehicle.rects[-1]

        if vehicle.state is Vehicle.State.NEW:
            if vehicle.direction > 0:
                if x+w > self.left_edge:
                    vehicle.start_speed(frame_number)
            else:
                if x < self.right_edge:
                    vehicle.start_speed(frame_number)

        if vehicle.state is Vehicle.State.ACTIVE:
            if vehicle.direction > 0:
                if x+w > self.right_edge:
                    vehicle.stop_speed(frame_number, self.fps)
            else:
                if x < self.left_edge:
                    vehicle.stop_speed(frame_number, self.fps)

    def remove_old_vehicles(self, frame_number):
        'Remove vehicles that have exited or were false detections'
        # identify vehicles to remove
        removed = []
        for v in self.vehicles:
            x, y, w, h = v.rects[-1]
            if v.frames_since_seen >= MAX_UNSEEN_FRAMES:
                removed.append(v)
                x0, y0, w0, h0 = v.rects[0]
                if v.state is Vehicle.State.ACTIVE:
                    # An active vehicle left the frame without crossing the exit speed line.
                    # In author's use case, this happens when vehicle turns onto cross street. 
                    self.log.warning('%d Active vehicle[%d] exit.(%d %d)-(%d %d) %d %d',
                        frame_number, v.id, x0, x0+w0, x, x+w,
                        v.frames_since_seen, v.age(frame_number))

        self.vehicles[:] = [v for v in self.vehicles if v not in removed]

    def add_new_vehicles(self, matches, frame_number, output_image):
        'Add new vehicles entering the frame'

        # check remaining/unused matches for new vehicles
        while len(matches) > 0:
            match = matches[0]
            x, y, w, h = match

            if w > self.min_vehicle_width and h > self.min_vehicle_height:
                # only allow new vehicles at left and right edges of frame
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
        'Check for vehicle passing the center of the frame'
        if not vehicle.center_frame:
            x, _y, w, _h = vehicle.rects[-1]
            vehicle_center_x = x + (w / 2)
            if abs(vehicle_center_x - self.frame_center_x) < 30:
                # As vehicle crosses center, save the current frame number
                vehicle.center_frame = frame_number
