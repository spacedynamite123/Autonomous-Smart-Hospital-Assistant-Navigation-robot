from brick import TouchSensor, EV3ColorSensor, EV3GyroSensor, Motor, BP, wait_ready_sensors
from utils.sound import Sound, Song

class Robot:
    """represents the physical robot and its connected hardware"""

    def __init__(self):
        """assigns ports to sensors and motors then waits for stabilization"""
        
        print("Initializing sensors and motors")
        
        # sensors
        self.emergency_button = TouchSensor(4)
        self.color_sensor = EV3ColorSensor(2)
        self.gyro_sensor = EV3GyroSensor(1)
        # motors
        self.left_wheel_motor = Motor('B')
        self.right_wheel_motor = Motor('C')
        self.left_grabber_motor = Motor('A')
        self.right_grabber_motor = Motor('D')
        
        print("Waiting for sensors to stabilize...")
        wait_ready_sensors()
        print("Hardware initialization complete!")
        
        # mission tracking
        self.last_seen_color = "UNKNOWN"

    def stop_all(self):
        """immediately cuts power to every motor to perform an emergency halt"""
        self.left_wheel_motor.set_power(0)
        self.right_wheel_motor.set_power(0)
        self.left_grabber_motor.set_power(0)
        self.right_grabber_motor.set_power(0)

