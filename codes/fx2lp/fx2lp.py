# https://ez.analog.com/rf/f/discussions/75850/adf4350-and-adf4351-software-and-usb-microcontroller-firmware-source-codes#52311

from array import array

import usb
import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1


_fx2lp = None

_BMREQUEST_TYPE_VENDOR_CLASS_READ = 0xC0
_BMREQUEST_TYPE_VENDOR_CLASS_WRITE = 0x40



# VR_GPIO = 0x23
# VR_GPIO_OE = 0x24
# VR_GPIO_IO = 0x25
# VR_I2C_IO = 0x22
# VR_I2C_SPEED = 0xa4
# VR_SPI_IO = 0x21
# VR_SPI_SPEED = 0xa5

def _get_usb_device(idVendor = 0X04B4, idProduct = 0X1004, use_libusb0 = False):
    global _fx2lp

    _fx2lp = usb.core.find(idVendor = idVendor, idProduct = idProduct,
                           backend = libusb0.get_backend() if use_libusb0 else libusb1.get_backend())
    if _fx2lp is not None:
        _fx2lp.set_configuration()

    return _fx2lp



def release_usb_device():
    global _fx2lp
    _fx2lp = None



class FX2LP:
    VR_RENUMERATE = 0xa3


    def __init__(self, use_libusb0 = False):

        self._bus = self.dev = _get_usb_device(use_libusb0 = use_libusb0)

        if self.is_virtual_device:
            print('\n****** Virtual device. Data may not be real ! ******\n')


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__del__()


    def __del__(self):
        self._bus = self.dev = None


    @property
    def is_virtual_device(self):
        return self._bus is None


    def re_numerate(self):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_RENUMERATE)



class Pin:
    IN = 1
    OUT = 3

    LOW = 0
    HIGH = 1


    def __init__(self, gpio, id, port = 'A', mode = IN, value = LOW, invert = False):

        self._gpio = gpio
        self._port = port
        self._id = id
        self._mode = mode
        self._invert = invert

        self._init(mode, value, invert)


    def __del__(self):
        self._gpio = None


    def _init(self, mode = None, value = LOW, invert = False):
        self._invert = invert
        self.mode = mode
        if self.mode == self.OUT:
            self.value(self.LOW if value is None else value)
        return self


    @property
    def pin_id(self):
        return self._id


    def value(self, value = None):
        if value is None:
            return self._gpio.get_pin_value(pin_idx = self._id, port = self._port)
        else:
            self._gpio.set_pin_value(pin_idx = self._id, level = value, port = self._port)


    def high(self):
        self.value(self.HIGH)


    def low(self):
        self.value(self.LOW)


    def on(self):
        self.low() if self._invert else self.high()


    def off(self):
        self.high() if self._invert else self.low()


    def toggle(self):
        self.value(not self.value())


    @property
    def mode(self):
        return self._mode


    @mode.setter
    def mode(self, mode):
        assert mode in (self.IN, self.OUT), 'Only Pin.IN, Pin.OUT supported.'
        self._mode = mode
        self._gpio.set_pin_direction(pin_idx = self._id, port = self._port, output = self._mode == self.OUT)



class GPIO(FX2LP):
    VR_GPIO = 0x23
    VR_GPIO_OE = 0x24
    VR_GPIO_IO = 0x25

    PORTS = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}


    def _validate(self, port, pin_idx):
        valids = self.PORTS.keys()
        assert port in valids, 'valid port: {}'.format(valids)

        valids = list(range(8))
        assert pin_idx in valids, 'pin_idx port: {}'.format(valids)


    def set_IO(self, value, port = 'A', as_direction = False):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_GPIO,
                                   wValue = self.VR_GPIO_OE if as_direction else self.VR_GPIO_IO,
                                   wIndex = self.PORTS[port],
                                   data_or_wLength = array('B', [value]))


    def get_IO(self, port = 'A', as_direction = False):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                          bRequest = self.VR_GPIO,
                                          wValue = self.VR_GPIO_OE if as_direction else self.VR_GPIO_IO,
                                          wIndex = self.PORTS[port],
                                          data_or_wLength = 1)[0]
        return 0


    def Pin(self, id, port = 'A', mode = Pin.IN, value = None, invert = False):
        return Pin(gpio = self, port = port, id = id, mode = mode, value = value, invert = invert)


    def set_pin_direction(self, pin_idx, port = 'A', output = False):
        self._validate(port, pin_idx)

        direction = self.get_IO(port, as_direction = True)
        clear_mask = ~(1 << pin_idx)
        value = direction & clear_mask | (int(output) << pin_idx)
        self.set_IO(value = value, port = port, as_direction = True)


    def get_pin_value(self, pin_idx, port = 'A'):
        self._validate(port, pin_idx)

        value = self.get_IO(port) & (1 << pin_idx)
        return 1 if value else 0


    def set_pin_value(self, pin_idx, level = 0, port = 'A'):
        self._validate(port, pin_idx)

        level = 1 if level else 0
        status = self.get_IO(port)
        clear_mask = ~(1 << pin_idx)
        value = status & clear_mask | (level << pin_idx)
        self.set_IO(value = value, port = port)



class I2C(FX2LP):
    VR_I2C_IO = 0x22
    VR_I2C_SPEED = 0xa4


    def __init__(self, as_400KHz = True, use_libusb0 = False):

        super().__init__(use_libusb0 = use_libusb0)

        self.as_400KHz = as_400KHz


    # read ==========================================

    def read_bytes(self, i2c_address, n_bytes):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                          bRequest = self.VR_I2C_IO,
                                          wValue = i2c_address,
                                          data_or_wLength = n_bytes)
        return array('B', [0] * n_bytes)


    def read_byte(self, i2c_address):
        return self.read_bytes(i2c_address = i2c_address, n_bytes = 1)[0]


    def read_addressed_bytes(self, i2c_address, sub_address, n_bytes):
        if not self.is_virtual_device:
            self.write_byte(i2c_address = i2c_address, value = sub_address)
            return self.read_bytes(i2c_address = i2c_address, n_bytes = n_bytes)

        return array('B', [0] * n_bytes)


    def read_addressed_byte(self, i2c_address, sub_address):
        return self.read_addressed_bytes(i2c_address, sub_address, 1)[0]


    # write ==========================================

    def write_bytes(self, i2c_address, bytes_array):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                          bRequest = self.VR_I2C_IO,
                                          wValue = i2c_address,
                                          data_or_wLength = bytes_array)


    def write_byte(self, i2c_address, value):
        return self.write_bytes(i2c_address = i2c_address, bytes_array = array('B', [value]))


    def write_addressed_bytes(self, i2c_address, sub_address, bytes_array):
        n_bytes = len(bytes_array)

        if not self.is_virtual_device:
            bytes_array.insert(0, sub_address)
            self.write_bytes(i2c_address = i2c_address, bytes_array = bytes_array)

        return n_bytes


    def write_addressed_byte(self, i2c_address, sub_address, value):
        return self.write_addressed_bytes(i2c_address, sub_address, bytes_array = array('B', [value]))


    # speed ==========================================

    @property
    def as_400KHz(self):
        if not self.is_virtual_device:
            return bool(self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                               bRequest = self.VR_I2C_SPEED,
                                               data_or_wLength = 1)[0])


    @as_400KHz.setter
    def as_400KHz(self, value):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_I2C_SPEED,
                                   wValue = bool(value))



class SPI(FX2LP):
    VR_SPI_IO = 0x21
    VR_SPI_SPEED = 0xa5


    def __init__(self, speed_Mbps = 10, use_libusb0 = False):

        super().__init__(use_libusb0 = use_libusb0)

        self.speed_Mbps = speed_Mbps


    @property
    def speed_Mbps(self):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                          bRequest = self.VR_SPI_SPEED,
                                          data_or_wLength = 1)[0]


    @speed_Mbps.setter
    def speed_Mbps(self, value):
        if not self.is_virtual_device:
            self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                   bRequest = self.VR_SPI_SPEED,
                                   wValue = value)


    def exchange(self, bytes_array):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                          bRequest = self.VR_SPI_IO,
                                          data_or_wLength = bytes_array)


    def read_bytes(self, n_bytes):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_READ,
                                          bRequest = self.VR_SPI_IO,
                                          data_or_wLength = n_bytes)
        return array('B', [0] * n_bytes)


    def read_byte(self):
        return self.read_bytes(n_bytes = 1)[0]


    def write_bytes(self, bytes_array):
        if not self.is_virtual_device:
            return self.dev.ctrl_transfer(bmRequestType = _BMREQUEST_TYPE_VENDOR_CLASS_WRITE,
                                          bRequest = self.VR_SPI_IO,
                                          data_or_wLength = bytes_array)


    def write_byte(self, value):
        return self.write_bytes(bytes_array = array('B', [value]))
