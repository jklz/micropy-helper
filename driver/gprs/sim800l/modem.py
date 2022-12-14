from .errors import GenericATError
from .logger import ModemLoggerInterface, Sim800lModemDefaultLogger
from .response import ModemResponse
from .uart import ModemUART
import time


class Sim800lModem:
    uart: ModemUART | None = None

    # modem pins
    __tx_pin: int | None
    __rx_pin: int | None

    # logger
    __logger: ModemLoggerInterface | None = None

    # state
    __state_initialized: bool = False
    __state_modem_info = None
    __state_is_ssl_available = None
    __state_is_connected: bool = False

    def __init__(self, *, uart: ModemUART = None, tx_pin: int = None, rx_pin: int = None) -> None:
        self.uart = uart
        self.__tx_pin = tx_pin
        self.__rx_pin = rx_pin

    @property
    def logger(self) -> ModemLoggerInterface:
        if self.__logger is None:
            self.__logger = Sim800lModemDefaultLogger()
        return self.__logger

    @logger.setter
    def logger(self, logger: ModemLoggerInterface) -> None:
        self.__logger = logger

    @property
    def is_initialized(self):
        return self.__state_initialized

    @is_initialized.setter
    def is_initialized(self, value: bool) -> None:
        raise Exception('unable to set is_initialized')

    @property
    def is_connected(self) -> bool:
        return self.__state_is_connected

    @is_connected.setter
    def is_connected(self, value: bool) -> None:
        raise Exception('unable to set is_connected')

    @property
    def is_ssl_available(self) -> bool:
        return self.__state_is_ssl_available

    @is_ssl_available.setter
    def is_ssl_available(self, value: bool) -> None:
        raise Exception('unable to set is_ssl_available')

    @property
    def modem_info(self):
        return self.__state_modem_info

    @modem_info.setter
    def modem_info(self, value) -> None:
        raise Exception('unable to set modem_info')

    def initialize(self) -> None:
        self.logger.debug('Initializing modem...')

        if not self.uart:
            self.uart = ModemUART(rx_pin=self.__rx_pin, tx_pin=self.__tx_pin)

        # Test AT commands
        max_initialize_attempt: int = 3
        initialize_attempt_count: int = 0
        initialize_attempt_retry_delay_seconds: int = 3
        while True:
            try:
                self.__state_modem_info = self.uart.modem_info
            except:
                initialize_attempt_count += 1
                if initialize_attempt_count < max_initialize_attempt:
                    self.logger.debug('Error in getting modem info, retrying.. (#{})'.format(initialize_attempt_count))
                    time.sleep(initialize_attempt_retry_delay_seconds)
                else:
                    raise
            else:
                break

        self.logger.debug('Ok, modem "{}" is ready and accepting commands'.format(self.modem_info))

        # Set initialized flag and support vars
        self.__state_initialized = True

        # Check if SSL is supported
        self.__state_is_ssl_available = self.uart.execute_at_command('checkssl') == '+CIPSSL: (0-1)'

    def connect(self, apn, user='', pwd=''):
        if not self.is_initialized:
            raise Exception('Modem is not initialized, cannot connect')

        # Are we already connected?
        if self.is_connected:
            self.logger.debug('Modem is already connected, not reconnecting.')
            return

        # Closing bearer if left opened from a previous connect gone wrong:
        self.logger.debug('Trying to close the bearer in case it was left open somehow..')
        try:
            self.uart.execute_at_command('closebear')
        except GenericATError:
            pass

        # First, init gprs
        self.logger.debug('Connect step #1 (initgprs)')
        self.uart.execute_at_command('initgprs')

        # Second, set the APN
        self.logger.debug('Connect step #2 (setapn)')
        self.uart.execute_at_command('setapn', apn)
        self.uart.execute_at_command('setuser', user)
        self.uart.execute_at_command('setpwd', pwd)

        # Then, open the GPRS connection.
        self.logger.debug('Connect step #3 (opengprs)')
        self.uart.execute_at_command('opengprs')

        # Ok, now wait until we get a valid IP address
        retries = 0
        max_retries = 5
        while True:
            retries += 1
            ip_addr = self.uart.ip_addr
            if not ip_addr:
                retries += 1
                if retries > max_retries:
                    raise Exception('Cannot connect modem as could not get a valid IP address')
                self.logger.debug('No valid IP address yet, retrying... (#')
                time.sleep(1)
            else:
                break
        self.__state_is_connected = True

    def disconnect(self):

        # Close bearer
        try:
            self.uart.execute_at_command('closebear')
        except GenericATError:
            pass

        # Check that we are actually disconnected
        ip_addr = self.uart.ip_addr
        if ip_addr:
            raise Exception('Error, we should be disconnected but we still have an IP address ({})'.format(ip_addr))
        self.__state_is_connected = False

    def http_request(self, url, mode='GET', data=None, content_type='application/json'):

        # Protocol check.
        assert url.startswith('http'), 'Unable to handle communication protocol for URL "{}"'.format(url)

        # Are we  connected?
        if not self.is_connected:
            raise Exception('Error, modem is not connected')

        # Close the http context if left open somehow
        self.logger.debug('Close the http context if left open somehow...')
        try:
            self.uart.execute_at_command('closehttp')
        except GenericATError:
            pass

        # First, init and set http
        self.logger.debug('Http request step #1.1 (inithttp)')
        self.uart.execute_at_command('inithttp')
        self.logger.debug('Http request step #1.2 (sethttp)')
        self.uart.execute_at_command('sethttp')

        # Do we have to enable ssl as well?
        if self.is_ssl_available:
            if url.startswith('https://'):
                self.logger.debug('Http request step #1.3 (enablessl)')
                self.uart.execute_at_command('enablessl')
            elif url.startswith('http://'):
                self.logger.debug('Http request step #1.3 (disablessl)')
                self.uart.execute_at_command('disablessl')
        else:
            if url.startswith('https://'):
                raise NotImplementedError("SSL is only supported by firmware revisions >= R14.00")

        # Second, init and execute the request
        self.logger.debug('Http request step #2.1 (initurl)')
        self.uart.execute_at_command('initurl', data=url)

        if mode == 'GET':

            self.logger.debug('Http request step #2.2 (doget)')
            output = self.uart.execute_at_command('doget')
            response_status_code = output.split(',')[1]
            self.logger.debug('Response status code: "{}"'.format(response_status_code))

        elif mode == 'POST':

            self.logger.debug('Http request step #2.2 (setcontent)')
            self.uart.execute_at_command('setcontent', content_type)

            self.logger.debug('Http request step #2.3 (postlen)')
            self.uart.execute_at_command('postlen', len(data))

            self.logger.debug('Http request step #2.4 (dumpdata)')
            self.uart.execute_at_command('dumpdata', data)

            self.logger.debug('Http request step #2.5 (dopost)')
            output = self.uart.execute_at_command('dopost')
            response_status_code = output.split(',')[1]
            self.logger.debug('Response status code: "{}"'.format(response_status_code))

        else:
            raise Exception('Unknown mode "{}'.format(mode))

        # Third, get data
        self.logger.debug('Http request step #4 (getdata)')
        response_content = self.uart.execute_at_command('getdata', clean_output=False)

        self.logger.debug(response_content)

        # Then, close the http context
        self.logger.debug('Http request step #4 (closehttp)')
        self.uart.execute_at_command('closehttp')

        return ModemResponse(status_code=response_status_code, content=response_content)
