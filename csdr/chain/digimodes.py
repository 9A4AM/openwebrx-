from csdr.chain.demodulator import ServiceDemodulator, SecondaryDemodulator, DialFrequencyReceiver, SecondarySelectorChain
from csdr.module.msk144 import Msk144Module, ParserAdapter
from owrx.audio.chopper import AudioChopper, AudioChopperParser
from owrx.aprs.kiss import KissDeframer
from owrx.aprs import Ax25Parser, AprsParser
from pycsdr.modules import Convert, FmDemod, Agc, TimingRecovery, DBPskDecoder, VaricodeDecoder, JKRttyDecoder, BaudotDecoder, Lowpass, RttyDecoder, CwDecoder, SstvDecoder, FaxDecoder, Shift
from pycsdr.types import Format
from owrx.aprs.direwolf import DirewolfModule
from owrx.sstv import SstvParser
from owrx.fax import FaxParser
from owrx.config import Config

class AudioChopperDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, mode: str, parser: AudioChopperParser):
        self.chopper = AudioChopper(mode, parser)
        workers = [Convert(Format.FLOAT, Format.SHORT), self.chopper]
        super().__init__(workers)

    def getFixedAudioRate(self):
        return 12000

    def setDialFrequency(self, frequency: int) -> None:
        self.chopper.setDialFrequency(frequency)


class Msk144Demodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self):
        self.parser = ParserAdapter()
        workers = [
            Convert(Format.FLOAT, Format.SHORT),
            Msk144Module(),
            self.parser,
        ]
        super().__init__(workers)

    def getFixedAudioRate(self) -> int:
        return 12000

    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)


class PacketDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, service: bool = False, ais: bool = False):
        self.parser = AprsParser()
        workers = [
            FmDemod(),
            Convert(Format.FLOAT, Format.SHORT),
            DirewolfModule(service=service, ais=ais),
            KissDeframer(),
            Ax25Parser(),
            self.parser,
        ]
        super().__init__(workers)

    def supportsSquelch(self) -> bool:
        return False

    def getFixedAudioRate(self) -> int:
        return 48000

    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)


class PskDemodulator(SecondaryDemodulator, SecondarySelectorChain):
    def __init__(self, baudRate: float):
        self.baudRate = baudRate
        # this is an assumption, we will adjust in setSampleRate
        self.sampleRate = 12000
        secondary_samples_per_bits = int(round(self.sampleRate / self.baudRate)) & ~3
        workers = [
            Agc(Format.COMPLEX_FLOAT),
            TimingRecovery(Format.COMPLEX_FLOAT, secondary_samples_per_bits, 0.5, 2),
            DBPskDecoder(),
            VaricodeDecoder(),
        ]
        super().__init__(workers)

    def getBandwidth(self):
        return self.baudRate

    def setSampleRate(self, sampleRate: int) -> None:
        if sampleRate == self.sampleRate:
            return
        self.sampleRate = sampleRate
        secondary_samples_per_bits = int(round(self.sampleRate / self.baudRate)) & ~3
        self.replace(1, TimingRecovery(Format.COMPLEX_FLOAT, secondary_samples_per_bits, 0.5, 2))


class JKRttyDemodulator(SecondaryDemodulator, SecondarySelectorChain):
    def __init__(self, baudRate, bandWidth, invert=False):
        self.baudRate = baudRate
        self.bandWidth = bandWidth
        self.invert = invert
        # this is an assumption, we will adjust in setSampleRate
        self.sampleRate = 12000
        secondary_samples_per_bit = int(round(self.sampleRate / self.baudRate))
        cutoff = self.baudRate / self.sampleRate
        loop_gain = self.sampleRate / self.getBandwidth() / 5
        workers = [
            Agc(Format.COMPLEX_FLOAT),
            FmDemod(),
            Lowpass(Format.FLOAT, cutoff),
            TimingRecovery(Format.FLOAT, secondary_samples_per_bit, loop_gain, 10),
            JKRttyDecoder(invert),
            BaudotDecoder(),
        ]
        super().__init__(workers)

    def getBandwidth(self) -> float:
        return self.bandWidth

    def setSampleRate(self, sampleRate: int) -> None:
        if sampleRate == self.sampleRate:
            return
        self.sampleRate = sampleRate
        secondary_samples_per_bit = int(round(self.sampleRate / self.baudRate))
        cutoff = self.baudRate / self.sampleRate
        loop_gain = self.sampleRate / self.getBandwidth() / 5
        self.replace(2, Lowpass(Format.FLOAT, cutoff))
        self.replace(3, TimingRecovery(Format.FLOAT, secondary_samples_per_bit, loop_gain, 10))


class CwDemodulator(SecondaryDemodulator, SecondarySelectorChain):
    def __init__(self, baudRate: float):
        self.sampleRate = 12000
        self.offset = 800
        self.baudRate = baudRate
        workers = [
            Shift(float(self.offset) / self.sampleRate),
            Agc(Format.COMPLEX_FLOAT),
            CwDecoder(self.sampleRate, self.offset, int(self.baudRate)),
        ]
        super().__init__(workers)

    def getBandwidth(self):
        return self.baudRate

    def setSampleRate(self, sampleRate: int) -> None:
        if sampleRate == self.sampleRate:
            return
        self.sampleRate = sampleRate
        self.replace(0, Shift(float(self.offset) / sampleRate))
        self.replace(2, CwDecoder(sampleRate, self.offset, int(self.baudRate)))


class RttyDemodulator(SecondaryDemodulator, SecondarySelectorChain):
    def __init__(self, targetWidth: float, baudRate: float, reverse: bool):
        self.sampleRate = 12000
        self.offset = 550
        self.targetWidth = targetWidth
        self.baudRate = baudRate
        self.reverse = reverse
        workers = [
            Shift((self.targetWidth/2 + self.offset) / self.sampleRate),
            Agc(Format.COMPLEX_FLOAT),
            RttyDecoder(self.sampleRate, self.offset, int(self.targetWidth), self.baudRate, self.reverse),
        ]
        super().__init__(workers)

    def getBandwidth(self):
        return self.targetWidth + 100.0

    def setSampleRate(self, sampleRate: int) -> None:
        if sampleRate == self.sampleRate:
            return
        self.sampleRate = sampleRate
        self.replace(0, Shift((self.targetWidth/2 + self.offset) / sampleRate))
        self.replace(2, RttyDecoder(sampleRate, self.offset, int(self.targetWidth), self.baudRate, self.reverse))


class SstvDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, service: bool = False):
        self.parser = SstvParser(service=service)
        self.sampleRate = 24000
        self.dbgTime = 300000
        workers = [
            SstvDecoder(self.sampleRate, self.dbgTime),
            self.parser
        ]
        super().__init__(workers)

    def getFixedAudioRate(self) -> int:
        return self.sampleRate

    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)


class FaxDemodulator(ServiceDemodulator, DialFrequencyReceiver):
    def __init__(self, service: bool = False):
        pm = Config.get()
        self.parser      = FaxParser(service=service)
        self.sampleRate  = 12000
        self.lpm         = 120
        self.dbgTime     = 300000
        self.postProcess = pm["fax_postprocess"]
        self.color       = pm["fax_color"]
        self.am          = pm["fax_am"]
        workers = [
            FaxDecoder(
                self.sampleRate,
                self.lpm,
                self.dbgTime,
                postProcess = self.postProcess,
                color = self.color,
                am = self.am
            ),
            self.parser
        ]
        super().__init__(workers)

    def getFixedAudioRate(self) -> int:
        return self.sampleRate

    def setDialFrequency(self, frequency: int) -> None:
        self.parser.setDialFrequency(frequency)

