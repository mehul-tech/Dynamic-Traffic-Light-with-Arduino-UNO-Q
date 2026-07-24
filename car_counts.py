import time
import cv2
from arduino_router_bridge import Bridge  # Bridge API to MCU
from edge_impulse_linux.image import ImageImpulseRunner

# Define Regions of Interest (ROIs) for 640x480 resolution
# Adjust these coordinates based on your camera angle and feed setup
LANE1_ROI = {"x_min": 0, "y_min": 0, "x_max": 320, "y_max": 480}  # Lane 1 (Left)
LANE2_ROI = {
    "x_min": 320,
    "y_min": 0,
    "x_max": 640,
    "y_max": 480,
}  # Lane 2 (Right)


def is_inside_roi(cx, cy, roi):
    """Check if object center (cx, cy) is within ROI boundaries."""
    return (
        roi["x_min"] <= cx <= roi["x_max"] and roi["y_min"] <= cy <= roi["y_max"]
    )


# Initialize Bridge API and Model
bridge = Bridge()
runner = ImageImpulseRunner("model.eim")  # Path to compiled model binary
runner.init()

cap = cv2.VideoCapture(0)  # Single USB Camera
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# State variable: 1 = Lane 1 Green, 2 = Lane 2 Green
current_green_lane = 1
last_switch_time = time.time()
MIN_GREEN_TIME = 5.0  # Minimum green time constraint in seconds

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run inference using Edge Impulse Runner
        features, _ = runner.get_features_from_image(frame)
        res = runner.classify(features)

        count_lane1 = 0
        count_lane2 = 0

        if "bounding_boxes" in res["result"]:
            for obj in res["result"]["bounding_boxes"]:
                if obj["label"] == "car" and obj["value"] >= 0.5:
                    # Calculate center coordinates of detected car
                    cx = int(obj["x"] + (obj["width"] / 2))
                    cy = int(obj["y"] + (obj["height"] / 2))

                    # Differentiate car location based on ROIs
                    if is_inside_roi(cx, cy, LANE1_ROI):
                        count_lane1 += 1
                        color = (255, 0, 0)  # Blue box for Lane 1
                    elif is_inside_roi(cx, cy, LANE2_ROI):
                        count_lane2 += 1
                        color = (0, 255, 255)  # Yellow box for Lane 2
                    else:
                        color = (128, 128, 128)

                    # Draw bounding box and centroid
                    cv2.rectangle(
                        frame,
                        (obj["x"], obj["y"]),
                        (obj["x"] + obj["width"], obj["y"] + obj["height"]),
                        color,
                        2,
                    )
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        # Print current per-lane car counts
        print(f"Lane 1 Cars: {count_lane1} | Lane 2 Cars: {count_lane2}")

        # Draw ROI divider line for visual feedback
        cv2.line(frame, (320, 0), (320, 480), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"L1: {count_lane1}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            2,
        )
        cv2.putText(
            frame,
            f"L2: {count_lane2}",
            (340, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
        )

        # Evaluate Dynamic Signal Switching Logic
        elapsed_time = time.time() - last_switch_time

        if elapsed_time >= MIN_GREEN_TIME:
            switch_required = False

            if current_green_lane == 1:
                # Switch if Lane 1 is empty OR Lane 2 has >= 5 more cars
                if count_lane1 == 0 or (count_lane2 - count_lane1 >= 5):
                    switch_required = True
                    new_lane = 2
            elif current_green_lane == 2:
                # Switch if Lane 2 is empty OR Lane 1 has >= 5 more cars
                if count_lane2 == 0 or (count_lane1 - count_lane2 >= 5):
                    switch_required = True
                    new_lane = 1

            if switch_required:
                print(f"--> Switching Signal Priority to Lane {new_lane}")
                bridge.send_command(
                    "SET_GREEN_LANE", new_lane
                )  # Notify MCU over Bridge
                current_green_lane = new_lane
                last_switch_time = time.time()

        cv2.imshow("Intersection Traffic Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    runner.stop()
    cap.release()
    cv2.destroyAllWindows()