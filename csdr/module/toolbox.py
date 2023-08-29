from pycsdr.modules import ExecModule
from pycsdr.types import Format
from csdr.module import PopenModule
from owrx.config import Config


class Rtl433Module(PopenModule):
    def __init__(self, sampleRate: int = 250000, jsonOutput: bool = False):
        self.sampleRate = sampleRate
        self.jsonOutput = jsonOutput
        super().__init__()

    def getCommand(self):
        return [
            "rtl_433", "-r", "cs16:-", "-s", str(self.sampleRate),
            "-M", "time:utc", "-F", "json" if self.jsonOutput else "kv",
            "-A",
        ]

    def getInputFormat(self) -> Format:
        return Format.COMPLEX_SHORT

    def getOutputFormat(self) -> Format:
        return Format.CHAR


class MultimonModule(PopenModule):
    def __init__(self, decoders: list[str]):
        self.decoders = decoders
        super().__init__()

    def getCommand(self):
        cmd = ["multimon-ng", "-", "-v0", "-c"]
        for x in self.decoders:
            cmd += ["-a", x]
        return cmd

    def getInputFormat(self) -> Format:
        return Format.SHORT

    def getOutputFormat(self) -> Format:
        return Format.CHAR


class DumpHfdlModule(PopenModule):
    def __init__(self, sampleRate: int = 12000, jsonOutput: bool = False):
        self.sampleRate = sampleRate
        self.jsonOutput = jsonOutput
        super().__init__()

    def getCommand(self):
        return [
            "dumphfdl", "--iq-file", "-", "--sample-format", "CF32",
            "--sample-rate", str(self.sampleRate), "--output",
            "decoded:%s:file:path=-" % ("json" if self.jsonOutput else "text"),
            "--utc", "--centerfreq", "0", "0"
        ]

    def getInputFormat(self) -> Format:
        return Format.COMPLEX_FLOAT

    def getOutputFormat(self) -> Format:
        return Format.CHAR


class DumpVdl2Module(PopenModule):
    def __init__(self, sampleRate: int = 105000, jsonOutput: bool = False):
        self.sampleRate = sampleRate
        self.jsonOutput = jsonOutput
        super().__init__()

    def getCommand(self):
        return [
            "dumpvdl2", "--iq-file", "-", "--sample-format", "S16_LE",
            "--oversample", str(self.sampleRate // 105000), "--output",
            "decoded:%s:file:path=-" % ("json" if self.jsonOutput else "text"),
            "--decode-fragments", "--utc"
        ]

    def getInputFormat(self) -> Format:
        return Format.COMPLEX_SHORT

    def getOutputFormat(self) -> Format:
        return Format.CHAR


class Dump1090Module(ExecModule):
    def __init__(self, rawOutput: bool = False):
        pm  = Config.get()
        lat = pm["receiver_gps"]["lat"]
        lon = pm["receiver_gps"]["lon"]
        cmd = [
            "dump1090-mutability", "--ifile", "-", "--iformat", "SC16",
            "--lat", str(lat), "--lon", str(lon),
            "--metric"
        ]
        if rawOutput:
            cmd += [ "--raw" ]
        super().__init__(Format.COMPLEX_SHORT, Format.CHAR, cmd)
