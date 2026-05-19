import math

GREEN_REF = [0.3278, 0.6212, 0.0509] # THESE ALL MIGHT BE CHANGED LATER 
RED_REF = [0.8241, 0.1261, 0.0498] # BUT LEAVE FOR NOW (IT SHOULD WORK)
COLOR_MATCH_THRESHOLD = 0.10


def check_bed_color(robot):
    # takes a single reading with the color sensor
    live_rgb = robot.color_sensor.get_rgb()
    
    if live_rgb != [None, None, None]:
        # find the brightest single color channel
        highest_value = sum(live_rgb)
        
        
        total = sum(live_rgb)
        norm_r = live_rgb[0] / total
        norm_g = live_rgb[1] / total
        norm_b = live_rgb[2] / total
        
        if norm_b < 0.07:
            
            
            dist_green = math.sqrt((norm_r - GREEN_REF[0])**2 + 
                                    (norm_g - GREEN_REF[1])**2 + 
                                    (norm_b - GREEN_REF[2])**2)
                                   
            dist_red = math.sqrt((norm_r - RED_REF[0])**2 + 
                                    (norm_g - RED_REF[1])**2 + 
                                    (norm_b - RED_REF[2])**2)
            
            if dist_green <= COLOR_MATCH_THRESHOLD:
                return "GREEN"
            elif dist_red <= COLOR_MATCH_THRESHOLD:
                return "RED"
                
    return "UNKNOWN"
