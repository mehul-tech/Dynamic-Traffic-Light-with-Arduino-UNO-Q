import atexit
import threading
import time

from arduino.app_utils import App, Bridge
from arduino.app_bricks.web_ui import WebUI
from arduino.app_bricks.video_objectdetection import (
    VideoObjectDetection
)
from arduino.app_peripherals.camera import Camera


# =================================
# Camera settings
# =================================

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
MIDDLE_X = FRAME_WIDTH / 2

# Change to True if left and right
# appear reversed.
SWAP_LEFT_RIGHT = False


# =================================
# Adaptive traffic-light timing
# =================================

# Green time when a road has no cars.
ZERO_CAR_GREEN_TIME = 2.0

# Green time when a road has one car.
MIN_GREEN_TIME = 4.0

# Maximum green time.
MAX_GREEN_TIME = 10.0

# Additional time for each car after
# the first car.
SECONDS_PER_EXTRA_CAR = 2.0

# Yellow-light duration.
YELLOW_TIME = 2.0

# Wait for the first AI result.
STARTUP_WAIT = 4.0

# Clear old counts if detections stop.
NO_DETECTION_TIMEOUT = 7.0


# =================================
# Create App Lab components
# =================================

ui = WebUI()

camera = Camera(
    "usb:0",
    resolution=(FRAME_WIDTH, FRAME_HEIGHT),
    fps=3
)

detector = VideoObjectDetection(
    camera=camera,
    confidence=0.30,
    debounce_sec=0.0
)


# =================================
# Shared system information
# =================================

current_time = time.monotonic()

system_state = {
    "left": 0,
    "right": 0,
    "total": 0,
    "last_detection": current_time,

    "left_light": "red",
    "right_light": "red",

    "left_light_started": current_time,
    "right_light_started": current_time,

    "phase": "all_red",
    "active_green": None,
    "phase_started": current_time,

    # Current road's allocated green time.
    "green_duration": ZERO_CAR_GREEN_TIME
}

state_lock = threading.Lock()
bridge_lock = threading.Lock()


# =================================
# Calculate adaptive green time
# =================================

def calculate_green_time(car_count):
    """
    0 cars      = 2 seconds
    1 car       = 4 seconds
    2 cars      = 6 seconds
    3 cars      = 8 seconds
    4+ cars     = 10 seconds
    """

    if car_count <= 0:
        return ZERO_CAR_GREEN_TIME

    extra_cars = car_count - 1

    calculated_time = (
        MIN_GREEN_TIME
        + extra_cars * SECONDS_PER_EXTRA_CAR
    )

    return min(
        MAX_GREEN_TIME,
        calculated_time
    )


# =================================
# Send information to WebUI
# =================================

def publish_state(room=None):
    with state_lock:
        now = time.monotonic()

        message = {
            "left": system_state["left"],
            "right": system_state["right"],
            "total": system_state["total"],

            "left_light": (
                system_state["left_light"]
            ),

            "right_light": (
                system_state["right_light"]
            ),

            "left_light_seconds": int(
                max(
                    0,
                    now
                    - system_state[
                        "left_light_started"
                    ]
                )
            ),

            "right_light_seconds": int(
                max(
                    0,
                    now
                    - system_state[
                        "right_light_started"
                    ]
                )
            ),

            "green_duration": (
                system_state["green_duration"]
            )
        }

    ui.send_message(
        "car_count",
        message,
        room=room
    )


# =================================
# Physical traffic-light control
# =================================

LIGHT_CODES = {
    "red": 0,
    "yellow": 1,
    "green": 2
}


def set_traffic_lights(
    left_light,
    right_light,
    phase,
    active_green,
    green_duration=None
):
    try:
        with bridge_lock:
            Bridge.call(
                "set_traffic_lights",
                LIGHT_CODES[left_light],
                LIGHT_CODES[right_light]
            )

    except Exception as error:
        print(
            f"Traffic-light Bridge error: {error}",
            flush=True
        )
        return False

    with state_lock:
        now = time.monotonic()

        # Reset a road's timer only when
        # that road changes color.
        if (
            system_state["left_light"]
            != left_light
        ):
            system_state["left_light_started"] = (
                now
            )

        if (
            system_state["right_light"]
            != right_light
        ):
            system_state["right_light_started"] = (
                now
            )

        system_state["left_light"] = left_light
        system_state["right_light"] = right_light

        system_state["phase"] = phase
        system_state["active_green"] = (
            active_green
        )
        system_state["phase_started"] = now

        if green_duration is not None:
            system_state["green_duration"] = (
                green_duration
            )

    publish_state()
    return True


# =================================
# Process camera detections
# =================================

def handle_detections(detections: dict):
    left_count = 0
    right_count = 0

    for label, boxes in detections.items():
        for car in boxes:
            bounding_box = car.get(
                "bounding_box_xyxy"
            )

            if (
                bounding_box is None
                or len(bounding_box) != 4
            ):
                continue

            x1, y1, x2, y2 = bounding_box

            car_center_x = (x1 + x2) / 2

            if car_center_x < MIDDLE_X:
                left_count += 1
            else:
                right_count += 1

    if SWAP_LEFT_RIGHT:
        left_count, right_count = (
            right_count,
            left_count
        )

    with state_lock:
        system_state["left"] = left_count
        system_state["right"] = right_count
        system_state["total"] = (
            left_count + right_count
        )
        system_state["last_detection"] = (
            time.monotonic()
        )

    publish_state()


# =================================
# Choose the first green road
# =================================

def choose_first_green(
    left_count,
    right_count
):
    # The busier road starts first.
    if right_count > left_count:
        return "right"

    # Left starts when it has more cars
    # or when the counts are equal.
    return "left"


def opposite_road(current_road):
    if current_road == "left":
        return "right"

    return "left"


def get_road_count(road):
    with state_lock:
        if road == "left":
            return system_state["left"]

        return system_state["right"]


# =================================
# Start a road's green light
# =================================

def start_green_for_road(road):
    car_count = get_road_count(road)

    green_time = calculate_green_time(
        car_count
    )

    if road == "left":
        return set_traffic_lights(
            left_light="green",
            right_light="red",
            phase="green",
            active_green="left",
            green_duration=green_time
        )

    return set_traffic_lights(
        left_light="red",
        right_light="green",
        phase="green",
        active_green="right",
        green_duration=green_time
    )


# =================================
# Start a road's yellow light
# =================================

def start_yellow_for_road(road):
    with state_lock:
        current_green_duration = (
            system_state["green_duration"]
        )

    if road == "left":
        return set_traffic_lights(
            left_light="yellow",
            right_light="red",
            phase="yellow",
            active_green="left",
            green_duration=current_green_duration
        )

    return set_traffic_lights(
        left_light="red",
        right_light="yellow",
        phase="yellow",
        active_green="right",
        green_duration=current_green_duration
    )


# =================================
# Adaptive alternating controller
# =================================

def traffic_controller():
    # Wait for Bridge and the first
    # camera result.
    time.sleep(STARTUP_WAIT)

    while True:
        time.sleep(0.2)

        with state_lock:
            left_count = system_state["left"]
            right_count = system_state["right"]

            phase = system_state["phase"]

            active_green = (
                system_state["active_green"]
            )

            phase_started = (
                system_state["phase_started"]
            )

            green_duration = (
                system_state["green_duration"]
            )

        elapsed = (
            time.monotonic() - phase_started
        )

        # -------------------------
        # Select the first road
        # -------------------------

        if phase == "all_red":
            first_green = choose_first_green(
                left_count,
                right_count
            )

            start_green_for_road(
                first_green
            )

        # -------------------------
        # Adaptive green finished
        # -------------------------

        elif (
            phase == "green"
            and elapsed >= green_duration
        ):
            start_yellow_for_road(
                active_green
            )

        # -------------------------
        # Yellow transition finished
        # -------------------------

        elif (
            phase == "yellow"
            and elapsed >= YELLOW_TIME
        ):
            next_green = opposite_road(
                active_green
            )

            start_green_for_road(
                next_green
            )


# =================================
# Clear outdated detections
# =================================

def clear_old_counts():
    while True:
        time.sleep(0.5)

        should_clear = False

        with state_lock:
            elapsed = (
                time.monotonic()
                - system_state["last_detection"]
            )

            if (
                system_state["total"] > 0
                and elapsed
                > NO_DETECTION_TIMEOUT
            ):
                system_state["left"] = 0
                system_state["right"] = 0
                system_state["total"] = 0

                should_clear = True

        if should_clear:
            publish_state()


# =================================
# Heartbeat for sketch watchdog
# =================================

def traffic_heartbeat():
    time.sleep(2)

    while True:
        try:
            with bridge_lock:
                Bridge.call(
                    "traffic_heartbeat"
                )

        except Exception:
            pass

        time.sleep(1)


# =================================
# Turn lights off when stopping
# =================================

def turn_lights_off_at_exit():
    try:
        with bridge_lock:
            Bridge.call(
                "turn_off_traffic_lights"
            )

    except Exception:
        # The watchdog in sketch.ino
        # provides backup shutdown.
        pass


atexit.register(turn_lights_off_at_exit)


# =================================
# Browser connection
# =================================

def handle_browser_connection(client_id):
    publish_state(room=client_id)


ui.on_connect(handle_browser_connection)

detector.on_detect_all(
    handle_detections
)


# =================================
# Start background tasks
# =================================

threading.Thread(
    target=traffic_controller,
    daemon=True
).start()

threading.Thread(
    target=clear_old_counts,
    daemon=True
).start()

threading.Thread(
    target=traffic_heartbeat,
    daemon=True
).start()


App.run()
