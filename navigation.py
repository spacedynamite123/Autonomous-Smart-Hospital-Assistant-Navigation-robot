import time
import threading
import math
from hardware import Robot
from utils import sound
from delivery import *
import detection

WHEEL_CIRCUMFERENCE = 3.14159 * 4.3
DEGREES_PER_CM      = 360.0 / WHEEL_CIRCUMFERENCE

SPEED      = 170
SPEED_TURN = 100

_turn_count = 0
side = "right"
count = 2

def _float_motors(robot: Robot):
    """
    puts both drive motors in float mode to allow manual movement
    inputs are the robot object
    no output
    """
    robot.left_wheel_motor.float_motor()
    robot.right_wheel_motor.float_motor()

def drive_forward(robot: Robot, 
    distance_cm: float,
    stop_flag: threading.Event, 
    bed_flag: threading.Event = None, 
    speed: int = SPEED):
    """
    drives the robot forward or backward a specific distance using a p-controller 
    inputs are the robot object, distance in centimeters, stop flag, 
        optional bed flag, and speed
    outputs arrived status or the color detected
    """

    # init
    target = abs(distance_cm) * DEGREES_PER_CM
    robot.left_wheel_motor.reset_encoder()
    robot.right_wheel_motor.reset_encoder()
    
    # -1 is forward 1 is backward
    sign = -1 if distance_cm > 0 else 1
    
    # for p-controller
    KP = 1.5  # Adjust until robot drives stably
    
    # get target_heading we want
    target_heading = robot.gyro_sensor.get_abs_measure()
    while target_heading is None:
        time.sleep(0.05)
        target_heading = robot.gyro_sensor.get_abs_measure()

    # start initial movement
    robot.left_wheel_motor.set_dps(sign * speed)
    robot.right_wheel_motor.set_dps(sign * speed)
    
    # driving loop
    while True:
        # cehck for background flags first
        if stop_flag.is_set():
            _float_motors(robot)
            return

        if bed_flag and bed_flag.is_set():
            _float_motors(robot)
            return robot.last_seen_color

        # calculat true distance traveled 
        left_enc = abs(robot.left_wheel_motor.get_encoder())
        right_enc = abs(robot.right_wheel_motor.get_encoder())
        avg_enc = (left_enc + right_enc) / 2.0
        
        # Break loop if we reached our target distance
        if avg_enc >= target:
            break

        # get current heading
        current_heading = robot.gyro_sensor.get_abs_measure()
        
        if current_heading is not None:
            # calculate error
            error = target_heading - current_heading
            
            # calculate adjustment 
            adjustment = int(error * KP * sign) # sign is important when for backing up
            
            # adjustment
            robot.left_wheel_motor.set_dps((sign * speed) + adjustment)
            robot.right_wheel_motor.set_dps((sign * speed) - adjustment)


        time.sleep(0.02)
        
    robot.left_wheel_motor.set_dps(0)
    robot.right_wheel_motor.set_dps(0)
    time.sleep(0.1)

    return "ARRIVED"

def turn_angle(
    robot: Robot, 
    angle_deg: float, 
    stop_flag: threading.Event, 
    bed_flag: threading.Event = None, 
    speed: int = SPEED_TURN
    ):
    """
    pivots the robot by a specific degree amount using gyro feedback 
        and deceleration zones
    inputs are the robot object, target angle, stop flag, optional bed flag, and speed
    no output
    """
    
    global _turn_count
    _turn_count += 1

    robot.left_wheel_motor.set_dps(0)
    robot.right_wheel_motor.set_dps(0)
    time.sleep(0.5)
    remaining = math.fabs(angle_deg)
    start_gyro = robot.gyro_sensor.get_abs_measure()
    while start_gyro is None:
        time.sleep(0.1)
        start_gyro = robot.gyro_sensor.get_abs_measure()


    sign = 1 if angle_deg > 0 else -1
    target = abs(angle_deg) - 2

    SLOW_ZONE = 30
    CRAWL_ZONE = 15
    TOLERANCE = 2
    SLOW_SPEED = speed * 0.3
    CRAWL_SPEED = speed * 0.12

    robot.left_wheel_motor.set_dps(sign * speed)
    robot.right_wheel_motor.set_dps(-sign * speed)

    start_time = time.time()
    while remaining > 0:
        if stop_flag.is_set():
            _float_motors(robot)
            return
        if time.time() - start_time > 8.0:
            print("TIMEOUT")
            break

        current = robot.gyro_sensor.get_abs_measure()
        if current is None:
            time.sleep(0.01)
            continue

        turned = abs(current - start_gyro)


        remaining = target - turned

        if remaining <= CRAWL_ZONE:
            robot.left_wheel_motor.set_dps(sign * CRAWL_SPEED)
            robot.right_wheel_motor.set_dps(-sign * CRAWL_SPEED)
        elif remaining <= SLOW_ZONE:
            robot.left_wheel_motor.set_dps(sign * SLOW_SPEED)
            robot.right_wheel_motor.set_dps(-sign * SLOW_SPEED)

        time.sleep(0.01)

    robot.left_wheel_motor.set_dps(0)
    robot.right_wheel_motor.set_dps(0)
    time.sleep(0.3)

    final = robot.gyro_sensor.get_abs_measure()


def pharmacy_pickup(robot: Robot, stop_flag: threading.Event, bed_flag):
    """
    moves the robot to collect medicine cubes and navigates to the start of the course
    inputs are the robot object, stop flag, and bed flag
    no output
    """
    drive_forward(robot, 18, stop_flag, bed_flag, speed=SPEED)
    # pick up function
    pickup_both(down_target=235, dps=1.7*130)
    drive_forward(robot, -13, stop_flag,bed_flag,speed=SPEED)
    turn_angle(robot, 91, stop_flag,bed_flag, speed=350)
    drive_forward(robot, 15, stop_flag,bed_flag, speed=SPEED)
    
def room_check(robot: Robot, stop_flag: threading.Event, bed_flag: threading.Event = None, entry_distance: float = 20,angle_set=[30, -60, 30]):
    """
    navigates into a room to scan for beds and performs delivery if target color is seen
    inputs are the robot object, stop flag, bed flag, entry distance, and scan angles
    no output
    """
    global side, count
    bed_detected = threading.Event()
    current_angle = 0
    total_advanced = 0
    STEP = 6

    def monitor_color():
        global side, count

        while not stop_flag.is_set() and not bed_detected.is_set():
            color = sensors.check_bed_color(robot)
            if color == "GREEN" or color == "RED":
                robot.last_seen_color = color
                bed_flag.set()
                bed_detected.set()
    
            time.sleep(0.01)

    color_thread = threading.Thread(target=monitor_color, daemon=True)
    color_thread.start()

    while total_advanced < entry_distance and not stop_flag.is_set():
        drive_forward(robot, STEP, stop_flag, bed_flag, speed=SPEED)
        total_advanced += abs(robot.left_wheel_motor.get_encoder()) / DEGREES_PER_CM
        if bed_flag and bed_flag.is_set():
            bed_detected.set()
            break
        for angle in angle_set:
            if stop_flag.is_set():
                break
            current_angle += angle
            turn_angle(robot, angle, stop_flag, bed_flag, speed=450)
            time.sleep(0.02)
            if bed_flag and bed_flag.is_set():
                bed_detected.set()
                break
        if bed_detected.is_set():
            break

    if bed_detected.is_set():
        color_thread.join(timeout=1)
        bed_flag.clear()
        print(current_angle)
        print(robot.last_seen_color)
        if robot.last_seen_color == "GREEN":

            # TUNE THIS ANGLE
            DROP_ANGLE = 15 
            
            # decide which way to turn based on which side is dropping
            turn_offset = DROP_ANGLE if side == "left" else -DROP_ANGLE
            
            turn_angle(robot, turn_offset, stop_flag, speed=250)
            time.sleep(0.1)
            
            drive_forward(robot, 5, stop_flag, speed=150)
            time.sleep(0.1)
            
            # drop the cube exactly on the spot
            drop_one(side, release_target=160, dps=1.7*130)
            count -= 1
            
            drive_forward(robot, -5, stop_flag, speed=150)
            time.sleep(0.1)
            
            # update the side variable for the next room
            if side == "left":
                side = "right"
            else:
                side = "left"
            time.sleep(0.05)
            
            # rotate back to realign
            turn_angle(robot, -turn_offset, stop_flag, speed=250)
            time.sleep(0.1)
            
            # exit
            if(current_angle != 0):
                time.sleep(0.02)
                turn_angle(robot, -current_angle, stop_flag, speed=350)
            time.sleep(0.02)
            drive_forward(robot, -total_advanced, stop_flag, speed=350)
        if robot.last_seen_color == "RED":
            # rotate back to realign
            # exit
            if(current_angle != 0):
                time.sleep(0.02)
                turn_angle(robot, -current_angle, stop_flag, speed=350)
    time.sleep(0.02)
    drive_forward(robot, -total_advanced, stop_flag, speed=350)


def room_check_one(robot: Robot, stop_flag: threading.Event, bed_flag: threading.Event = None, entry_distance: float = 20,angle_set=[-90, 180, -90]):
    """
    searches for a single target bed within a room and delivers a cube if found
    inputs are the robot object, stop flag, bed flag, entry distance, and scan angles
    no output
    """
    global side, count
    bed_detected = threading.Event()
    current_angle = 0
    total_advanced = 0
    STEP = 6

    def monitor_color():
        global side, count

        while not stop_flag.is_set() and not bed_detected.is_set():
            color = sensors.check_bed_color(robot)
            if color == "GREEN":
                robot.last_seen_color = color
                bed_flag.set()
                bed_detected.set()

            time.sleep(0.01)

    color_thread = threading.Thread(target=monitor_color, daemon=True)
    color_thread.start()

    while total_advanced < entry_distance and not stop_flag.is_set():
        drive_forward(robot, STEP, stop_flag, bed_flag, speed=SPEED)
        total_advanced += abs(robot.left_wheel_motor.get_encoder()) / DEGREES_PER_CM
        if bed_flag and bed_flag.is_set():
            bed_detected.set()
            break
        for angle in angle_set:
            if stop_flag.is_set():
                break
            current_angle += angle
            turn_angle(robot, angle, stop_flag, bed_flag, speed=150)
            time.sleep(0.02)
            if bed_flag and bed_flag.is_set():
                bed_detected.set()
                break
        if bed_detected.is_set():
            break

    if bed_detected.is_set():
        color_thread.join(timeout=1)
        bed_flag.clear()
        print(current_angle)
        print(robot.last_seen_color)
        if robot.last_seen_color == "GREEN":

            # TUNE THIS ANGLE
            DROP_ANGLE = 15 
            
            # Decide which way to turn based on which side is dropping.
            turn_offset = DROP_ANGLE if side == "left" else -DROP_ANGLE
            
            turn_angle(robot, turn_offset, stop_flag, speed=250)
            time.sleep(0.1) 
            
            drive_forward(robot, 5, stop_flag, speed=150)
            time.sleep(0.1)
            
            # drop cube on the green bed
            drop_one(side, release_target=160, dps=1.7*130)
            count -= 1
            
            drive_forward(robot, -5, stop_flag, speed=150)
            time.sleep(0.1)
            
            # change side
            if side == "left":
                side = "right"
            else:
                side = "left"
            time.sleep(0.05)
            
            # rotate back to realign
            turn_angle(robot, -turn_offset, stop_flag, speed=250)
            time.sleep(0.1)
            
            # exit sequence
            if(current_angle != 0):
                time.sleep(0.02)
                turn_angle(robot, -current_angle, stop_flag, speed=350)
            time.sleep(0.02)
            drive_forward(robot, -total_advanced, stop_flag, speed=350)
        else:
            bed_flag.clear()

def room_check_two(robot: Robot, stop_flag: threading.Event, bed_flag: threading.Event = None,
                   entry_distance: float = 20, angle_set=[-90, 180, -90]):
    """
    searches for up to two target beds within a room and manages deliveries for both
    inputs are the robot object, stop flag, bed flag, entry distance, and scan angles
    no output
    """

    global side, count
    bed_detected = threading.Event()
    current_angle = 0
    total_advanced = 0
    STEP = 6

    def monitor_color():
        while not stop_flag.is_set() and not bed_detected.is_set():
            color = sensors.check_bed_color(robot)
            if color == "GREEN":
                robot.last_seen_color = color
                bed_flag.set()
                bed_detected.set()
            time.sleep(0.01)

    color_thread = threading.Thread(target=monitor_color, daemon=True)
    color_thread.start()

    while total_advanced < entry_distance and not stop_flag.is_set():
        drive_forward(robot, STEP, stop_flag, bed_flag, speed=SPEED)
        total_advanced += abs(robot.left_wheel_motor.get_encoder()) / DEGREES_PER_CM
        if bed_flag and bed_flag.is_set():
            bed_detected.set()
            break
        for angle in angle_set:
            if stop_flag.is_set():
                break
            current_angle += angle
            turn_angle(robot, angle, stop_flag, bed_flag, speed=150)
            time.sleep(0.02)
            if bed_flag and bed_flag.is_set():
                bed_detected.set()
                break
        if bed_detected.is_set():
            break

    if not bed_detected.is_set():
        bed_flag.clear()
        if current_angle != 0:
            turn_angle(robot, -current_angle, stop_flag, speed=350)
        time.sleep(0.02)
        drive_forward(robot, -total_advanced, stop_flag, speed=350)
        return

    color_thread.join(timeout=1)
    bed_flag.clear()

    first_bed_side = side

    DROP_ANGLE = 15
    turn_offset = DROP_ANGLE if side == "left" else -DROP_ANGLE
    turn_angle(robot, turn_offset, stop_flag, speed=250)
    time.sleep(0.1)
    drive_forward(robot, 5, stop_flag, speed=150)
    time.sleep(0.1)
    drop_one(side, release_target=160, dps=1.7*130)
    count -= 1
    drive_forward(robot, -5, stop_flag, speed=150)
    time.sleep(0.1)
    side = "right" if side == "left" else "left"
    time.sleep(0.05)
    turn_angle(robot, -turn_offset, stop_flag, speed=250)
    time.sleep(0.1)

    if current_angle != 0:
        turn_angle(robot, -current_angle, stop_flag, speed=350)
    current_angle = 0
    time.sleep(0.05)

    if first_bed_side == "left":
        second_angle_set = [90, -90]
    else:
        second_angle_set = [-90, 90]

    bed_detected.clear()
    bed_flag.clear()
    robot.last_seen_color = None

    color_thread2 = threading.Thread(target=monitor_color, daemon=True)
    color_thread2.start()

    for angle in second_angle_set:
        if stop_flag.is_set():
            break
        current_angle += angle
        turn_angle(robot, angle, stop_flag, bed_flag, speed=450)
        time.sleep(0.02)
        if bed_flag and bed_flag.is_set():
            bed_detected.set()
            break

    if bed_detected.is_set() and robot.last_seen_color == "GREEN":
        color_thread2.join(timeout=1)
        bed_flag.clear()

        turn_offset = DROP_ANGLE if side == "left" else -DROP_ANGLE
        turn_angle(robot, turn_offset, stop_flag, speed=250)
        time.sleep(0.1)
        drive_forward(robot, 5, stop_flag, speed=150)
        time.sleep(0.1)
        drop_one(side, release_target=160, dps=1.7*130)
        count -= 1
        drive_forward(robot, -5, stop_flag, speed=150)
        time.sleep(0.1)
        side = "right" if side == "left" else "left"
        time.sleep(0.05)
        turn_angle(robot, -turn_offset, stop_flag, speed=250)
        time.sleep(0.1)

    bed_flag.clear()
    if current_angle != 0:
        turn_angle(robot, -current_angle, stop_flag, speed=350)
    time.sleep(0.02)
    drive_forward(robot, -total_advanced, stop_flag, speed=350)

def run_course(robot: Robot, stop_flag: threading.Event, bed_flag):
    """
    the main mission loop that coordinates movement between the pharmacy 
        and various rooms
    inputs are the robot object, stop flag, and bed flag
    no output
    """
    pharmacy_pickup(robot, stop_flag, bed_flag)
    time.sleep(0.02)
    drive_forward(robot, 45, stop_flag,bed_flag, speed=450)#35
    time.sleep(0.02)
    room_check(robot, stop_flag, bed_flag, 35, [-15, 12])
    time.sleep(0.02)
    turn_angle(robot, -91, stop_flag,bed_flag, speed=250)
    time.sleep(0.02)
    drive_forward(robot, 46, stop_flag,bed_flag, speed=450)
    time.sleep(0.02)
    turn_angle(robot, 91, stop_flag, bed_flag, speed=250)
    time.sleep(0.02)
    drive_forward(robot, 10, stop_flag, bed_flag, speed=450)
    time.sleep(0.02)
    room_check(robot, stop_flag, bed_flag, 35, [-20, 40,-25])
    time.sleep(0.02)
    if count == 0:
        turn_angle(robot, 91, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 43, stop_flag, bed_flag, speed=450)
        time.sleep(0.02)
        turn_angle(robot, 91, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 25, stop_flag, bed_flag, speed=450)
        time.sleep(0.2)
        tone1.play()
        tone1.wait_done()
        #Sound Playing
        return
    elif count == 1:
        turn_angle(robot, -91, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 45, stop_flag, bed_flag, speed=450)
        time.sleep(0.02)
        turn_angle(robot, -98, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 15, stop_flag, bed_flag, speed=450)
        room_check_one(robot, stop_flag, bed_flag, 35, [-90, 180, -90])
        turn_angle(robot, -91, stop_flag, bed_flag, speed=250)
        drive_forward(robot, 70, stop_flag, bed_flag, speed=450)
        turn_angle(robot, 91, stop_flag, bed_flag, speed=250)
        drive_forward(robot, 15, stop_flag, bed_flag, speed=450)
        time.sleep(0.2)
        tone1.play()
        tone1.wait_done()
    else:
        turn_angle(robot, -91, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 45, stop_flag, bed_flag, speed=450)
        time.sleep(0.02)
        turn_angle(robot, -98, stop_flag, bed_flag, speed=250)
        time.sleep(0.02)
        drive_forward(robot, 15, stop_flag, bed_flag, speed=450)
        room_check_two(robot, stop_flag, bed_flag, 35, [-90, 180, -90])
        turn_angle(robot, -91, stop_flag, bed_flag, speed=250)
        drive_forward(robot, 70, stop_flag, bed_flag, speed=450)
        turn_angle(robot, 91, stop_flag, bed_flag, speed=250)
        drive_forward(robot, 15, stop_flag, bed_flag, speed=450)
        time.sleep(0.2)
        tone1.play()
        tone1.wait_done()
    
    
    
    