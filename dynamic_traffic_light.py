# MPU Logic (main.py) snippet
import time

THRESHOLD_DIFF = 5       # Car count difference threshold
MIN_GREEN = 5.0          # Minimum green duration in seconds
MAX_GREEN = 30.0         # Maximum green duration in seconds

active_lane = 'A'
green_start_time = time.time()

def evaluate_traffic(count_A, count_B):
    global active_lane, green_start_time
    elapsed = time.time() - green_start_time
    
    # Calculate car difference between lanes
    diff = count_B - count_A if active_lane == 'A' else count_A - count_B
    curr_count = count_A if active_lane == 'A' else count_B
    
    # Check if we should switch lanes
    should_switch = False
    
    # 1. Immediate switch if current lane is empty (and MIN_GREEN elapsed)
    if curr_count == 0 and elapsed >= MIN_GREEN:
        should_switch = True
        
    # 2. Switch if differential threshold met (and MIN_GREEN elapsed)
    elif diff >= THRESHOLD_DIFF and elapsed >= MIN_GREEN:
        should_switch = True
        
    # 3. Force-off if MAX_GREEN reached
    elif elapsed >= MAX_GREEN:
        should_switch = True

    if should_switch:
        # Trigger safe switch (MCU handles Green -> Yellow -> Red transition)
        active_lane = 'B' if active_lane == 'A' else 'A'
        bridge.send_switch_signal(active_lane)
        green_start_time = time.time()