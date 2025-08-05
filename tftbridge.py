#
# BigTreeTech TFT35 bridge
#
# Author: K. Hui
#
import serial
import threading


class TftBridge:
    def __init__(self, config):
        self.printer = config.get_printer()
        #
        # get config
        #
        self.tft_device = config.get("tft_device")
        self.tft_baud = config.getint("tft_baud")
        self.tft_timeout = config.getint("tft_timeout")
        self.klipper_device = config.get("klipper_device")
        self.klipper_baud = config.getint("klipper_baud")
        self.klipper_timeout = config.getint("klipper_timeout")
        #
        # connections to TFT35 and Klipper serial ports
        #
        self.tft_serial = None
        self.klipper_serial = None
        #
        # event to signal stopping threads
        #
        self.stop_event = threading.Event()
        #
        # register event handlers
        #
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)

    #
    # open serial port to device
    #
    def open_device(self, device, baud, timeout):
        if timeout == 0:
            serial_port = serial.Serial(device, baud)
        else:
            serial_port = serial.Serial(device, baud, timeout=timeout)
        return serial_port

    #
    # event handler when printer is ready
    #
    def handle_ready(self):
        #
        # create connections to devices if needed
        #
        if self.tft_serial is None:
            try:
                self.tft_serial = self.open_device(
                    self.tft_device, self.tft_baud, self.tft_timeout
                )
            except Exception as e:
                print(f"Failed to establish tft connection: {e}")
                self.tft_serial = None

        if self.klipper_serial is None:
            try:
                self.klipper_serial = self.open_device(
                    self.klipper_device, self.klipper_baud, self.klipper_timeout
                )
            except Exception as e:
                print(f"Failed to establish klipper connection: {e}")
                self.klipper_serial = None
        #
        # create and start threads
        #
        self.stop_event.clear()
        threading.Thread(target=self.tft2klipper).start()
        threading.Thread(target=self.klipper2tft).start()

    #
    # forward data from TFT35 to Klipper
    #
    def tft2klipper(self):
        while True:
            #
            # if stopping thread event is set
            #
            if self.stop_event.is_set():
                if self.tft_serial is not None:
                    self.tft_serial.close()  # close connection to TFT35
                self.tft_serial = None  # clear property
                break
            #
            # otherwise read from TFT35 and forward to Klipper
            #
            if self.tft_serial is not None and self.klipper_serial is not None:
                try:
                    line = self.tft_serial.readline()
                except Exception as e:
                    print(f"Failed to read from tft {e}")
                    line = ""
                if line != "":  # if readline timeout, it returns an empty str
                    try:
                        self.klipper_serial.write(line)
                    except Exception as e:
                        print(f"Failed to write to klipper {e}")

    #
    # forward data from Klipper to TFT35
    #
    def klipper2tft(self):
        while True:
            #
            # if stopping thread event is set
            #
            if self.stop_event.is_set():
                if self.klipper_serial is not None:
                    self.klipper_serial.close()  # close connection to Klipper
                self.klipper_serial = None  # clear property
                break
            #
            # otherwise read from Klipper and forward to TFT35
            #
            if self.tft_serial is not None and self.klipper_serial is not None:
                try:
                    line = self.klipper_serial.readline()
                except Exception as e:
                    print(f"Failed to read from klipper {e}")
                    line = ""
                if line != "":  # if readline timeout, it returns an empty str
                    try:
                        self.tft_serial.write(line)
                    except Exception as e:
                        print(f"Failed to write to tft {e}")

    #
    # event handler when printer is disconnected
    #

    def handle_disconnect(self):
        self.stop_event.set()  # signal threads to stop


#
# config loading function of add-on
#


def load_config(config):
    return TftBridge(config)
