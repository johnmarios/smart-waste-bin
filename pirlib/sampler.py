from gpiozero import DigitalInputDevice

class PirSampler:
    # A simple wrapper around gpiozero's DigitalInputDevice to read a PIR sensor
    def __init__(self, pin: int):
        self.pin = pin
        # Use DigitalInputDevice to read the PIR sensor's output
        self.dev = DigitalInputDevice(pin) 

    def read(self) -> bool:
        # True = HIGH, False = LOW
        return bool(self.dev.value)