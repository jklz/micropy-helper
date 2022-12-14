

class ModemLoggerInterface:

    def log(self, message: str) -> None:
        pass

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


class Sim800lModemDefaultLogger(ModemLoggerInterface):
    is_debug_enabled: bool = True
    is_output_print_enabled: bool = True

    def log(self, message: str) -> None:
        if self.is_output_print_enabled:
            print(message)

    def debug(self, message: str) -> None:
        if self.is_debug_enabled:
            self.log('DEBUG:' + message)

    def info(self, message: str) -> None:
        self.log('INFO:' + message)

    def warning(self, message: str) -> None:
        self.log('WARNING:' + message)

    def error(self, message: str) -> None:
        self.log('ERROR:' + message)

