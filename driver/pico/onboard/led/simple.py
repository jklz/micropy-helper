from driver.led import SimpleLed
from driver.pico.onboard.config import PICO_ONBOARD_LED_GPIO_PIN


class PicoSimpleLed(SimpleLed):
    def __init__(self):
        super().__init__(PICO_ONBOARD_LED_GPIO_PIN)

