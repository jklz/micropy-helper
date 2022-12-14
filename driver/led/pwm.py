from machine import Pin, PWM


class PwmLed:
    __led_pwm: PWM
    __state_freq: int
    __state_brightness: int

    def __init__(self, gpio_pin: int, init_brightness: int = 0, init_freq_hz: int = 500,):
        self.__led_pwm = PWM(Pin(gpio_pin))
        self.freq = init_freq_hz
        self.brightness = init_brightness

    @property
    def freq(self) -> int:
        """
        get pwm freq in Hz
        """
        return self.__state_freq

    @freq.setter
    def freq(self, value_hz: int):
        """
        set pwm freq in Hz
        """
        self.__state_freq = value_hz
        self.__led_pwm.freq(self.__state_freq)

    @property
    def brightness(self) -> int:
        """
        get brightness percent
        """
        return self.__state_brightness

    @brightness.setter
    def brightness(self, value: int):
        """
        set brightness percent
        """
        # check value between 0 and 100
        if value < 0:
            # below min, so we will set to min
            value = 0
        elif value > 100:
            # above max, so we will set to max
            value = 100
        # set state to have new value
        self.__state_brightness = value
        # send brightness to pwm
        new_pwm_duty = (65535*self.__state_brightness)/1000
        self.__led_pwm.duty_u16(new_pwm_duty)

    def off(self) -> None:
        """
        set brightness to 0 to turn off
        """
        self.brightness = 0

    def on(self) -> None:
        """
        set brightness to max value
        """
        self.brightness = 100

    def decrease(self, value_step: int) -> int:
        """
        decrease brightness by percent
        returns updated brightness value
        """
        self.brightness = self.brightness - value_step
        return self.brightness

    def increase(self, value_step: int = 10) -> int:
        """
        increase brightness by percent
        returns updated brightness value
        """
        self.brightness = self.brightness + value_step
        return self.brightness

    def max(self) -> None:
        """
        set brightness to max value
        """
        self.brightness = 100

    def min(self) -> None:
        """
        set brightness to min value without being off
        """
        self.brightness = 1

