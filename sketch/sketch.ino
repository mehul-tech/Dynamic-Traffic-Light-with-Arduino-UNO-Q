#include <Arduino_Modulino.h>
#include "Arduino_RouterBridge.h"

ModulinoPixels pixels;

const int LIGHT_RED = 0;
const int LIGHT_YELLOW = 1;
const int LIGHT_GREEN = 2;

const int BRIGHTNESS = 30;

ModulinoColor YELLOW_COLOR(255, 130, 0);

// Turn off the lights if Python disappears
const unsigned long HEARTBEAT_TIMEOUT_MS = 4000;

volatile unsigned long lastHeartbeatTime = 0;
volatile bool appIsActive = false;


void markAppActive() {
    lastHeartbeatTime = millis();
    appIsActive = true;
}


void turnEverythingOff() {
    for (int i = 0; i < 8; i++) {
        pixels.set(i, RED, 0);
    }
}


void turn_off_traffic_lights() {
    turnEverythingOff();
    pixels.show();
    appIsActive = false;
}


void traffic_heartbeat() {
    markAppActive();
}


void setOneRoad(
    int redPixel,
    int yellowPixel,
    int greenPixel,
    int lightState
) {
    if (lightState == LIGHT_RED) {
        pixels.set(
            redPixel,
            RED,
            BRIGHTNESS
        );
    }
    else if (lightState == LIGHT_YELLOW) {
        pixels.set(
            yellowPixel,
            YELLOW_COLOR,
            BRIGHTNESS
        );
    }
    else if (lightState == LIGHT_GREEN) {
        pixels.set(
            greenPixel,
            GREEN,
            BRIGHTNESS
        );
    }
}


void set_traffic_lights(
    int leftState,
    int rightState
) {
    turnEverythingOff();

    // Left road: pixels 0, 1 and 2
    setOneRoad(0, 1, 2, leftState);

    // Right road: pixels 4, 5 and 6
    setOneRoad(4, 5, 6, rightState);

    pixels.show();
    markAppActive();
}


void setup() {
    Modulino.begin();
    pixels.begin();

    // Initial safe state
    set_traffic_lights(
        LIGHT_RED,
        LIGHT_RED
    );

    Bridge.begin();

    Bridge.provide(
        "set_traffic_lights",
        set_traffic_lights
    );

    Bridge.provide(
        "traffic_heartbeat",
        traffic_heartbeat
    );

    Bridge.provide(
        "turn_off_traffic_lights",
        turn_off_traffic_lights
    );
}


void loop() {
    unsigned long currentTime = millis();

    if (
        appIsActive
        && currentTime - lastHeartbeatTime
            > HEARTBEAT_TIMEOUT_MS
    ) {
        turn_off_traffic_lights();
    }

    delay(50);
}
