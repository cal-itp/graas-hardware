import sys

class Tee:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = None
        self.filename = None

    def redirect(self, filename = None):
        if self.log is not None:
            self.log.close()

        self.filename = filename

        if filename is None:
            self.log = None
        else:
            self.log = open(filename, 'w')

    def write(self, message):
        self.terminal.write(message)

        if self.log is not None:
            self.log.write(message)

    def flush(self):
        self.terminal.flush()
