from fx2lp import I2C


I2C_address = 0x60
register_address = 3

i2c = I2C()
i2c.write_byte(I2C_address, register_address, 0xff)
print(i2c.read_byte(I2C_address, register_address))
