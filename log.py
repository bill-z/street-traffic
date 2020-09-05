import logging
import logging.handlers
import sys

LOG_LEVEL = logging.DEBUG

class Log (object):
    def __init__ (self, logToFileEnabled):    
        self.main_logger = logging.getLogger()
        self.logToFileEnabled = logToFileEnabled

        formatter = logging.Formatter(
            fmt='%(asctime)s.%(msecs)03d %(levelname)-8s [%(name)s] %(message)s'
            , datefmt='%Y-%m-%d %H:%M:%S')

        handler_stream = logging.StreamHandler(sys.stdout)
        handler_stream.setFormatter(formatter)
        self.main_logger.addHandler(handler_stream)

        if self.logToFileEnabled:
            handler_file = logging.handlers.RotatingFileHandler("debug.log"
                , maxBytes = 2**24
                , backupCount = 10)
            handler_file.setFormatter(formatter)
            self.main_logger.addHandler(handler_file)

        self.main_logger.setLevel(LOG_LEVEL)

    def getLog (self):
        return self.main_logger
