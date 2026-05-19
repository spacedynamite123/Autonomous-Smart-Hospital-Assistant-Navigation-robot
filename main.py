import threading
import time
from hardware import Robot
import navigation

print("Initializing robot")
robot = Robot()

# flag for emergency stop and bed detection
bed_flag = threading.Event()
stop_flag = threading.Event()

def monitor_touch():
    # for emergency stop thread
    while not stop_flag.is_set():
        # Using the robot object's touch sensor instead of a standalone one
        if robot.emergency_button.is_pressed():
            print("\n*** EMERGENCY STOP TRIGGERED ***")
            robot.stop_all() # Hard stop all motors
            stop_flag.set()  # Signal navigation functions to break their loops
        time.sleep(0.01)


def main():
    # start the emergency stop thread
    monitor = threading.Thread(target=monitor_touch, daemon=True)
    monitor.start()

    print("Starting in 2 seconds")
    time.sleep(2)

    navigation.run_course(robot, stop_flag, bed_flag)

    print("shutting down")

    robot.stop_all()

if __name__ == "__main__":
    main()
