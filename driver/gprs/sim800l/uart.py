# Imports
from .logger import ModemLoggerInterface, Sim800lModemDefaultLogger
from .errors import GenericATError
import time
import json
from machine import UART


class ModemUART(UART):
    __rx_pin: int
    __tx_pin: int

    # logger
    __logger: ModemLoggerInterface | None = None

    def __init__(self, rx_pin: int, tx_pin: int):
        self.__rx_pin = rx_pin
        self.__tx_pin = tx_pin
        super().__init__(1, 9600, timeout=1000, rx=self.__rx_pin, tx=self.__tx_pin)

    @property
    def logger(self) -> ModemLoggerInterface:
        if self.__logger == None:
            self.__logger = Sim800lModemDefaultLogger()
        return self.__logger

    @logger.setter
    def logger(self, logger: ModemLoggerInterface) -> None:
        self.__logger = logger

    # ----------------------
    # Execute AT commands
    # ----------------------
    def execute_at_command(self, command: str, data=None, clean_output=True):

        # Commands dictionary. Not the best approach ever, but works nicely.
        commands = {
            'modeminfo': {'string': 'ATI', 'timeout': 3, 'end': 'OK'},
            'fwrevision': {'string': 'AT+CGMR', 'timeout': 3, 'end': 'OK'},
            'battery': {'string': 'AT+CBC', 'timeout': 3, 'end': 'OK'},
            'scan': {'string': 'AT+COPS=?', 'timeout': 60, 'end': 'OK'},
            'network': {'string': 'AT+COPS?', 'timeout': 3, 'end': 'OK'},
            'signal': {'string': 'AT+CSQ', 'timeout': 3, 'end': 'OK'},
            'checkreg': {'string': 'AT+CREG?', 'timeout': 3, 'end': None},
            'setapn': {'string': 'AT+SAPBR=3,1,"APN","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'setuser': {'string': 'AT+SAPBR=3,1,"USER","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'setpwd': {'string': 'AT+SAPBR=3,1,"PWD","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'initgprs': {'string': 'AT+SAPBR=3,1,"Contype","GPRS"', 'timeout': 3, 'end': 'OK'},
            # Appeared on hologram net here or below
            'opengprs': {'string': 'AT+SAPBR=1,1', 'timeout': 3, 'end': 'OK'},
            'getbear': {'string': 'AT+SAPBR=2,1', 'timeout': 3, 'end': 'OK'},
            'inithttp': {'string': 'AT+HTTPINIT', 'timeout': 3, 'end': 'OK'},
            'sethttp': {'string': 'AT+HTTPPARA="CID",1', 'timeout': 3, 'end': 'OK'},
            'checkssl': {'string': 'AT+CIPSSL=?', 'timeout': 3, 'end': 'OK'},
            'enablessl': {'string': 'AT+HTTPSSL=1', 'timeout': 3, 'end': 'OK'},
            'disablessl': {'string': 'AT+HTTPSSL=0', 'timeout': 3, 'end': 'OK'},
            'initurl': {'string': 'AT+HTTPPARA="URL","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'doget': {'string': 'AT+HTTPACTION=0', 'timeout': 3, 'end': '+HTTPACTION'},
            'setcontent': {'string': 'AT+HTTPPARA="CONTENT","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'postlen': {'string': 'AT+HTTPDATA={},5000'.format(data), 'timeout': 3, 'end': 'DOWNLOAD'},
            # "data" is data_lenght in this context, while 5000 is the timeout
            'dumpdata': {'string': data, 'timeout': 1, 'end': 'OK'},
            'dopost': {'string': 'AT+HTTPACTION=1', 'timeout': 3, 'end': '+HTTPACTION'},
            'getdata': {'string': 'AT+HTTPREAD', 'timeout': 3, 'end': 'OK'},
            'closehttp': {'string': 'AT+HTTPTERM', 'timeout': 3, 'end': 'OK'},
            'closebear': {'string': 'AT+SAPBR=0,1', 'timeout': 3, 'end': 'OK'}
        }

        # References:
        # https://github.com/olablt/micropython-sim800/blob/4d181f0c5d678143801d191fdd8a60996211ef03/app_sim.py
        # https://arduino.stackexchange.com/questions/23878/what-is-the-proper-way-to-send-data-through-http-using-sim908
        # https://stackoverflow.com/questions/35781962/post-api-rest-with-at-commands-sim800
        # https://arduino.stackexchange.com/questions/34901/http-post-request-in-json-format-using-sim900-module (full post example)

        # Sanity checks
        if command not in commands:
            raise Exception('Unknown command "{}"'.format(command))

        # Support vars
        command_string: str = commands[command]['string']
        excpected_end: str | None = commands[command]['end']
        timeout: int = commands[command]['timeout']
        processed_lines = 0

        # Execute the AT command
        command_string_for_at = "{}\r\n".format(command_string)
        self.logger.debug('Writing AT command "{}"'.format(command_string_for_at.encode('utf-8')))
        self.write(command_string_for_at)

        # Support vars
        pre_end = True
        output = ''
        empty_reads = 0

        while True:

            line = self.readline()
            if not line:
                time.sleep(1)
                empty_reads += 1
                if empty_reads > timeout:
                    raise Exception('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    # logger.warning('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    # break
            else:
                if line == None:
                    line = ''

                self.logger.debug('Read "{}"'.format(line))

                # Convert line to string

                line_str: str = line.encode('utf-8')

                # Do we have an error?
                if line_str == 'ERROR\r\n':
                    raise GenericATError('Got generic AT error')

                # If we had a pre-end, do we have the expected end?
                if line_str == '{}\r\n'.format(excpected_end):
                    self.logger.debug('Detected exact end')
                    break
                if pre_end and line_str.startswith('{}'.format(excpected_end)):
                    self.logger.debug('Detected startwith end (and adding this line to the output too)')
                    output += line_str
                    break

                # Do we have a pre-end?
                if line_str == '\r\n':
                    pre_end = True
                    self.logger.debug('Detected pre-end')
                else:
                    pre_end = False

                # Keep track of processed lines and stop if exceeded
                processed_lines += 1

                # Save this line unless in particular conditions
                if command == 'getdata' and line_str.startswith('+HTTPREAD:'):
                    pass
                else:
                    output += line_str

        # Remove the command string from the output
        output = output.replace(command_string + '\r\r\n', '')

        # ...and remove the last \r\n added by the AT protocol
        if output.endswith('\r\n'):
            output = output[:-2]

        # Also, clean output if needed
        if clean_output:
            output = output.replace('\r', '')
            output = output.replace('\n\n', '')
            if output.startswith('\n'):
                output = output[1:]
            if output.endswith('\n'):
                output = output[:-1]

        self.logger.debug('Returning "{}"'.format(output.encode('utf8')))

        # Return
        return output

    # ----------------------
    #  Function commands
    # ----------------------

    @property
    def modem_info(self):
        return self.execute_at_command('modeminfo')

    @modem_info.setter
    def modem_info(self, value):
        raise Exception('unable to set modem_info')

    @property
    def battery(self):
        return self.execute_at_command('battery')

    @battery.setter
    def battery(self, value):
        raise Exception('unable to set battery')

    @property
    def networks(self):
        networks = []
        output = self.execute_at_command('scan')
        pieces = output.split('(', 1)[1].split(')')
        for piece in pieces:
            piece = piece.replace(',(', '')
            subpieces = piece.split(',')
            if len(subpieces) != 4:
                continue
            networks.append({'name': json.loads(subpieces[1]), 'shortname': json.loads(subpieces[2]),
                             'id': json.loads(subpieces[3])})
        return networks

    @networks.setter
    def networks(self, value):
        raise Exception('unable to set networks')

    @property
    def network(self):
        output = self.execute_at_command('network')
        network = output.split(',')[-1]
        if network.startswith('"'):
            network = network[1:]
        if network.endswith('"'):
            network = network[:-1]
        # If after filtering we did not filter anything: there was no network
        if network.startswith('+COPS'):
            return None
        return network

    @network.setter
    def network(self, value):
        raise Exception('unable to set network')

    @property
    def signal(self):
        # See more at https://m2msupport.net/m2msupport/atcsq-signal-quality/
        output = self.execute_at_command('signal')
        signal = int(output.split(':')[1].split(',')[0])
        signal_ratio = float(signal) / float(30)  # 30 is the maximum value (2 is the minimum)
        return signal_ratio

    @signal.setter
    def signal(self, value):
        raise Exception('unable to set signal')

    @property
    def ip_addr(self):
        output = self.execute_at_command('getbear')
        output = output.split('+')[-1]  # Remove potential leftovers in the buffer before the "+SAPBR:" response
        pieces = output.split(',')
        if len(pieces) != 3:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        ip_addr = pieces[2].replace('"', '')
        if len(ip_addr.split('.')) != 4:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        if ip_addr == '0.0.0.0':
            return None
        return ip_addr

    @ip_addr.setter
    def ip_addr(self, value):
        raise Exception('unable to set ip_addr')
