# Street Traffic Monitor #

A python and OpenCV application to track vehicle speeds using a Raspberry Pi and PiCamera.
The application is currently configured to observe vehicles traveling horizontally across the camera's view (from the side of the road). A photo of each passing vehicle is saved with the date, time and speed.

The speed calculation is simply based on distance and time. It appears to be fairly accurate so far (based on drive-by calibrations), but it is definitely still a work in progress. 

Here are a couple of known issues / future todos:

1) tracking can get confused when vehicles pass each other from opposite directions.
2) it is unreliable once the sun sets. 
*I have not yet investigated modifying the approach to work at night. 
*(could detect lights, but headlight beams, etc.)
3) At dusk and when darkly cloudly, it sometimes has difficulty tracking (asphalt-)gray colored vehicles.
