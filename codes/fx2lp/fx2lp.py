# https://ez.analog.com/rf/f/discussions/75850/adf4350-and-adf4351-software-and-usb-microcontroller-firmware-source-codes#52311

from array import array

import usb
import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1

# from signal_generators.adf435x.fx2 import AnalogDevicesFX2LP
from utilities.adapters.peripherals import Bus


BMREQUEST_TYPE_VENDOR_CLASS_READ = 0xC0
BMREQUEST_TYPE_VENDOR_CLASS_WRITE = 0x40



class I2C(Bus):
    VR_RENUMERATE = 0xa3
    VR_I2C_WRITE = 0x22
    VR_I2C_READ = 0xa2
    VR_I2C_SPEED = 0xa4


    def __init__(self, as_400KHz = True, use_libusb0 = True):

        self.dev = usb.core.find(idVendor = 0X04B4, idProduct = 0X1004,
                                 backend = libusb0.get_backend() if use_libusb0 else libusb1.get_backend())

        if self.dev is not None:
            self.dev.set_configuration()

        super().__init__(self.dev)

        self.set_speed(as_400KHz)


    def init(self):
        pass


    def set_speed(self, as_400KHz = True):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_I2C_SPEED,
                                   wValue = int(bool(as_400KHz)))


    def re_numerate(self):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_RENUMERATE)


    def read_bytes(self, i2c_address, n_bytes):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                          bRequest = self.VR_I2C_READ,
                                          wValue = i2c_address,
                                          data_or_wLength = n_bytes)
        return array('B', [0] * n_bytes)


    def read_byte(self, i2c_address):
        return self.read_bytes(i2c_address = i2c_address, n_bytes = 1)[0]


    def write_bytes(self, i2c_address, bytes_array):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_I2C_WRITE,
                                   wValue = i2c_address,
                                   data_or_wLength = bytes_array)
            return len(bytes_array)


    def write_byte(self, i2c_address, value):
        return self.write_bytes(i2c_address = i2c_address, bytes_array = array('B', [value]))


    def read_addressed_bytes(self, i2c_address, reg_address, n_bytes):
        if not self.is_virtual_device:
            self.write_byte(i2c_address = i2c_address, value = reg_address)
            return self.read_bytes(i2c_address = i2c_address, n_bytes = n_bytes)


    def read_addressed_byte(self, i2c_address, reg_address):
        return self.read_addressed_bytes(i2c_address, reg_address, 1)[0]


    def write_addressed_bytes(self, i2c_address, reg_address, bytes_array):
        n_bytes = len(bytes_array)

        if not self.is_virtual_device:
            bytes_array.insert(0, reg_address)
            self.write_bytes(i2c_address = i2c_address, bytes_array = bytes_array)

        return n_bytes


    def write_addressed_byte(self, i2c_address, reg_address, value):
        return self.write_addressed_bytes(i2c_address, reg_address, bytes_array = array('B', [value]))

# class SPI(AnalogDevicesFX2LP):
#     pass
