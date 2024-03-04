from owrx.toolbox import TextParser
from owrx.color import ColorCache
import json

import logging

logger = logging.getLogger(__name__)


class DscParser(TextParser):
    def __init__(self, service: bool = False):
        # Colors will be assigned via this cache
        self.colors = ColorCache()
        # No frequency yet
        self.frequency = 0
        # Construct parent object
        super().__init__(filePrefix="DSC", service=service)

    def setDialFrequency(self, frequency: int) -> None:
        self.frequency = frequency

    def parse(self, msg: bytes):
        # Do not parse in service mode
        if self.service:
            return None
        # Expect JSON data in text form
        out = json.loads(msg)
        # Add mode name, time stamp, frequency, and color to identify sender
        out["mode"]      = "DSC"
        out["timestamp"] = self.getUtcTime()
        if self.frequency != 0:
            out["frequency"] = self.frequency
        if "src" in out:
            out["color"] = self.colors.getColor(out["src"])
        logger.debug("{0}".format(out))
        return out
