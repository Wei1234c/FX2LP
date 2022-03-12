from fx2lp import *


release_usb_device()
gpio = GPIO()
p0 = gpio.Pin(0, mode = Pin.OUT, value = 0)
p1 = gpio.Pin(1, mode = Pin.OUT, value = 0)

import time


p = p0

for i in range(3):
    p.low()
    time.sleep(0.2)
    p.high()
    time.sleep(0.2)
