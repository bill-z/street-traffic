# Street Traffic Monitor #

A python and OpenCV application to track vehicle speeds using a Raspberry Pi and PiCamera.
The application is currently configured to observe vehicles traveling horizontally across the camera's view (from the side of the road). A photo of each passing vehicle is saved with the date, time and speed.

![Car driving from left to right with date and speed of 26.9 overlayed.](/doc/example_photo.png?raw=true "Example photo")

The speed calculation is based on distance and time. It appears to be reasonably accurate so far (based on drive-by calibrations), but it is definitely still a work in progress. 

Here are a couple of known issues / future todos:

1. Tracking can get confused when vehicles pass each other from opposite directions.
2. Detection and tracking are unreliable once the sun sets. 
    - Could investigate modifying the approach to work at night. 
    - Could detect lights, but... headlight beams, etc.
3. At dusk and when darkly cloudly, it sometimes has difficulty detecting (asphalt-)gray colored vehicles.
