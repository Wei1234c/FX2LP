from fx2lp import I2C


I2C_address = 0x60
register_address = 3

i2c = I2C()
print(i2c.set_speed(as_400KHz = True))
