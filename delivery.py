import time
from utils import sound
from utils.brick import Motor, TouchSensor, wait_ready_sensors

# LEFT_ARM = Motor('D')
# RIGHT_ARM = Motor('A')
# TOUCH = TouchSensor(4)   
# wait_ready_sensors()

SPEED = 130
tone1 = sound.Sound(duration=3.0, pitch="E5", volume=100)

def stop_hold(arm=None):
    """
    sets motor dps to zero to lock arm position
    input is the arm string or none
    no output
    """
    if arm == 'left' or arm is None:
        LEFT_ARM.set_dps(0)
    if arm == 'right' or arm is None:
        RIGHT_ARM.set_dps(0)

def stop_float(arm=None):
    """
    releases arm into float mode to allow manual movement
    input is the arm string or none
    no output
    """
    if arm == 'left' or arm is None:
        LEFT_ARM.float_motor()
    if arm == 'right' or arm is None:
        RIGHT_ARM.float_motor()

def emergency_stop():
    """
    checks touch sensor and floats arms if pressed
    no input
    outputs true if stopped
    """
    if TOUCH.is_pressed():
        stop_float()
        print("EMERGENCY STOP")
        return True
    return False

def move_both(target, dps, print_encoder=True, hold_at_end=False):
    """
    drives both arms to target degree
    inputs are target, speed, print flag, and hold flag
    outputs true if finished
    """
    LEFT_ARM.reset_encoder()
    RIGHT_ARM.reset_encoder()
    LEFT_ARM.set_dps(dps)
    RIGHT_ARM.set_dps(dps)
    while abs(LEFT_ARM.get_encoder()) < target and abs(RIGHT_ARM.get_encoder()) < target:
        if emergency_stop():
            return False
        if print_encoder:
            print("Left:", LEFT_ARM.get_encoder(), "| Right:", RIGHT_ARM.get_encoder())
        time.sleep(0.02)
    if hold_at_end:
        stop_hold()
    else:
        stop_float()
    print("Final Left:", LEFT_ARM.get_encoder(), "| Final Right:", RIGHT_ARM.get_encoder())
    return True

def move_one(arm, target, dps, print_encoder=True, hold_at_end=False):
    """
    drives specific arm to target degree
    inputs are arm string, target, speed, print flag, and hold flag
    outputs true if finished
    """
    motor = LEFT_ARM if arm == 'left' else RIGHT_ARM
    motor.reset_encoder()
    motor.set_dps(dps)
    while abs(motor.get_encoder()) < target:
        if emergency_stop():
            return False
        if print_encoder:
            print(f"{arm.capitalize()} Encoder:", motor.get_encoder())
        time.sleep(0.02)
    if hold_at_end:
        stop_hold(arm)
    else:
        stop_float(arm)
    print(f"Final {arm.capitalize()}:", motor.get_encoder())
    return True

def pickup_both(down_target=235, dps=1.7*130):
    """
    triggers dual arm lowering to grab cubes
    inputs are down target and speed
    outputs true if successful
    """
    print("BOTH ARMS GOING DOWN TO GRAB")
    if not move_both(down_target, dps, hold_at_end=True):
        return False
    time.sleep(0.3)
    print("Both cubes should now be held")
    return True

def drop_one(arm, release_target=160, dps=1.7*130):
    """
    releases specific arm and plays tone
    inputs are arm string, release target, and speed
    outputs true if successful
    """
    print(f"DROPPING {arm.upper()} ARM")
    if not move_one(arm, release_target, -dps, hold_at_end=False):
        return False
    
    time.sleep(0.2)
    tone1.play()
    tone1.wait_done()
    stop_float(arm)
    time.sleep(0.3)
    print(f"{arm.capitalize()} arm released")
    return True
