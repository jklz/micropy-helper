

class ModemResponse(object):
    def __init__(self, status_code, content):
        self.status_code = int(status_code)
        self.content = content


