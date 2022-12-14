from driver.led import PwmLed
from driver.pico.onboard.config import PICO_ONBOARD_LED_GPIO_PIN


class PicoPwmLed(PwmLed):
    def __init__(self, init_brightness: int = 0, init_freq_hz: int = 500,):
        super().__init__(PICO_ONBOARD_LED_GPIO_PIN, init_brightness, init_freq_hz)

