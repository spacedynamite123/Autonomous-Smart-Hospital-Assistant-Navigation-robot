import threading
import time
from hardware import Robot
import sensors

def monitor_touch(robot, stop_flag):
    while not stop_flag.is_set():
        if robot.emergency_button.is_pressed():
            print("\n*** EMERGENCY STOP TRIGGERED - ENDING TEST ***")
            stop_flag.set()
        time.sleep(0.01)

def main():
    print("Initializing robot hardware for color test")
    robot = Robot()
    
    stop_flag = threading.Event()

    # Start the emergency monitor thread
    monitor = threading.Thread(target=monitor_touch, args=(robot, stop_flag), daemon=True)
    monitor.start()

    print("1. Place a RED or GREEN sticker under the sensor.")
    print("2. The script will print the detected color.")
    print("3. Press the Touch Sensor to quit the test.\n")

    try:
        while not stop_flag.is_set():
            detected_color = sensors.scan_for_bed(robot, stop_flag)
            
            if stop_flag.is_set() or detected_color == "UNKNOWN":
                break
                
            print(f">>> Bed Detected: {detected_color} <<<")
            
            # Pause for 3 seconds to let you remove/swap the sticker before scanning again
            print("Remove the sticker (Scanning again in 3s)\n")
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\nTest interrupted manually via keyboard.")

    robot.stop_all()

if __name__ == "__main__":
    main()
