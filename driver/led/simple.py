from machine import Pin


class SimpleLed:
    __led_pin: Pin
    __led_state: bool

    def __init__(self, gpio_pin: int, init_state: bool = False):
        self.__led_pin = Pin(gpio_pin)
        self.state = init_state

    def __read_pin_state(self) -> None:
        self.__led_state = bool(self.__led_pin.value())

    @property
    def state(self) -> bool:
        return self.__led_state

    @state.setter
    def state(self, value: bool):
        self.__led_state = value
        self.__led_pin.value(int(self.__led_state))

    def toggle(self) -> None:
        self.state = not self.state

    def on(self) -> None:
        self.state = True

    def off(self) -> None:
        self.state = False
