from fx2lp import *


I2C_address = 0x63
register_address = 3

i2c = I2C()
i2c.as_400KHz = True
print(i2c.as_400KHz)
