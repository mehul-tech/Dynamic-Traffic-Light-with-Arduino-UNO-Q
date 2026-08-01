# Dynamic Traffic Light with Arduino UNO Q

An AI-based adaptive traffic signal system built using the Arduino UNO Q, Edge Impulse, a USB webcam, and Modulino Pixels.

## Project Description

This project demonstrates a smart traffic signal for a miniature two-road intersection.

A USB webcam watches both roads. An object-detection model trained with Edge Impulse detects the miniature cars and counts how many cars are present on the left and right roads.

The system uses the number of cars to decide how long each road should receive a green light. A road with fewer cars receives a shorter green time, while a road with more cars receives a longer green time.

A Modulino Pixels RGB module represents the physical red, yellow, and green traffic lights. A WebUI page displays the live camera, car counts, current signal colors, and signal timers.

## Main Features

- Live car detection using a USB webcam
- Custom Edge Impulse object-detection model
- Separate car counts for two roads
- Adaptive green-light duration
- Red, yellow, and green physical traffic signals
- Live browser-based monitoring dashboard
- Traffic-light timers
- Automatic alternating between roads
- Safe LED shutdown using a Bridge heartbeat
- Wireless access to the UNO Q over the local network

## Hardware Requirements

- Arduino UNO Q
- Modulino Pixels
- Qwiic cable
- USB webcam
- Powered USB-C hub
- USB-C power supply
- Computer running Arduino App Lab
- Miniature cars
- Miniature two-road intersection
- Wi-Fi network

## Software Requirements

- Arduino App Lab
- Edge Impulse Studio account
- Custom car-detection Edge Impulse project
- Video Object Detection Brick
- WebUI HTML Brick
- Arduino Modulino sketch library
- Modern web browser

## Hardware Connections

### Modulino Pixels

Connect the Modulino Pixels to the Qwiic connector on the Arduino UNO Q using a Qwiic cable.

### USB Webcam

1. Connect the webcam to a USB data port on the powered hub.
2. Connect the USB-C power supply to the hub’s PD or Power port.
3. Connect the hub’s host USB-C cable to the Arduino UNO Q.
4. Wait for the UNO Q Linux system to boot.

## Modulino Pixels Arrangement

The Modulino Pixels contains eight individually controllable RGB LEDs.

| Pixel | Function |
|---:|---|
| 0 | Left road red |
| 1 | Left road yellow |
| 2 | Left road green |
| 3 | Unused |
| 4 | Right road red |
| 5 | Right road yellow |
| 6 | Right road green |
| 7 | Unused |

## How Car Detection Works

The webcam captures a 640 × 480 image.

The image is divided vertically into two sections:

- Left half: left road
- Right half: right road

For every detected car, the program calculates the center of its bounding box.

If the center is located before the middle of the image, the car is counted on the left road. Otherwise, it is counted on the right road.

```text
Camera image
┌──────────────────┬──────────────────┐
│                  │                  │
│    Left road     │    Right road    │
│                  │                  │
└──────────────────┴──────────────────┘
                  x = 320
```

## Adaptive Green-Light Timing

The green-light duration is calculated when a road’s green turn begins.

| Cars detected | Green time |
|---:|---:|
| 0 | 2 seconds |
| 1 | 4 seconds |
| 2 | 6 seconds |
| 3 | 8 seconds |
| 4 or more | 10 seconds |

The yellow light remains active for 2 seconds.

The duration is fixed for the current green turn. This prevents the timer from changing suddenly when the AI count changes during an active signal.

## Traffic-Signal Sequence

The first green road is selected using the initial car counts:

- More cars on the left: left road starts green
- More cars on the right: right road starts green
- Equal counts: left road starts green

After the first selection, the two roads alternate:

```text
Left green
     ↓
Left yellow
     ↓
Right green
     ↓
Right yellow
     ↓
Left green
```

When both roads have the same number of cars, the signal does not freeze. The roads continue alternating normally.

## WebUI Dashboard

The browser dashboard displays:

- Live webcam feed
- Detection bounding boxes
- Left-road car count
- Right-road car count
- Total car count
- Left-road traffic signal
- Right-road traffic signal
- Time spent in the current signal color
- Connection status

The webpage is normally available at:

```text
http://UNO_Q_IP_ADDRESS:7000
```

For example:

```text
http://192.168.1.225:7000
```

The UNO Q IP address may change when connecting to a different network.

## Repository Structure

```text
Dynamic-Traffic-Light-with-Arduino-UNO-Q/
├── assets/
│   └── index.html
├── python/
│   ├── main.py
│   └── requirements.txt
├── sketch/
│   ├── sketch.ino
│   └── sketch.yaml
├── app.yaml
└── README.md
```

### File Purposes

- `python/main.py`: Processes detections, counts cars, controls timing, updates the WebUI, and communicates with the Arduino sketch.
- `sketch/sketch.ino`: Controls the physical Modulino Pixels traffic lights.
- `sketch/sketch.yaml`: Contains sketch configuration information.
- `assets/index.html`: Provides the live WebUI dashboard.
- `python/requirements.txt`: Contains additional Python dependencies when required.
- `app.yaml`: Contains the Arduino App Lab application configuration.

## Running the Project

1. Open Arduino App Lab.
2. Connect to the Arduino UNO Q.
3. Open the car-detection application.
4. Confirm that the Video Object Detection Brick is added.
5. Confirm that the WebUI HTML Brick is added.
6. Confirm that the custom Edge Impulse car-detection model is selected.
7. Confirm that the Arduino Modulino library is added under Sketch Libraries.
8. Connect the webcam and Modulino Pixels.
9. Press **Run**.
10. Wait for the application to start.

The console should show messages similar to:

```text
Successfully started USB Webcam
WebSocket connection established
App started
```

Open the WebUI using the network URL shown in the App Lab console.

## Bridge Communication

The Python program runs on the Linux processor of the Arduino UNO Q. The Arduino sketch runs on the microcontroller.

They communicate using Arduino Bridge.

Python sends traffic-light commands such as:

```python
Bridge.call(
    "set_traffic_lights",
    left_light_code,
    right_light_code
)
```

The Arduino sketch receives the command and updates the Modulino Pixels.

## Automatic Light Shutdown

Python sends a heartbeat to the Arduino sketch every second.

If the heartbeat stops, the sketch assumes that the application has stopped. It turns off all Modulino Pixels automatically after approximately four seconds.

This prevents the LEDs from remaining on after pressing **Stop** in Arduino App Lab.

## Expected Output

When the left road has more cars initially:

```text
Left road: Green
Right road: Red
```

After the left road’s calculated green time:

```text
Left road: Yellow
Right road: Red
```

After the yellow transition:

```text
Left road: Red
Right road: Green
```

The physical Modulino Pixels and the WebUI traffic signals should show the same colors.

## Current Limitations

- Detection speed depends on the Edge Impulse model’s inference time.
- Detection accuracy depends on lighting and camera position.
- Cars placed too close together may be detected as one object.
- The model must be trained using images similar to the miniature cars and road.
- The computer and UNO Q must be connected to the same local network to access the WebUI.
- The system currently supports two road regions separated vertically in the camera image.

## Possible Future Improvements

- Use separate regions instead of equal image halves
- Add pedestrian crossing support
- Add emergency-vehicle priority
- Store traffic data in a database
- Create traffic-count graphs
- Add manual traffic-light controls
- Improve model speed using a smaller Edge Impulse input size
- Add more roads and traffic signals
- Add a remaining-time countdown
- Add vehicle tracking to avoid duplicate counts

## Team Members

- Jungwoo(Max) Moon
- Mehul Goel
- Aryan Makwana

## Project Goal

The goal of this project is to demonstrate how artificial intelligence, computer vision, and embedded hardware can work together to create a smarter traffic-management system.
