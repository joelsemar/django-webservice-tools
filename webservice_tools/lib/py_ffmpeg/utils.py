class BitPaddedInt(int):
    def __new__(cls, value, bits=7, bigendian=True):
        "Strips 8-bits bits out of every byte"
        mask = (1<<(bits))-1
        if isinstance(value, (int, long)):
            bytes = []
            while value:
                bytes.append(value & ((1<<bits)-1))
                value = value >> 8
        if isinstance(value, str):
            bytes = [ord(byte) & mask for byte in value]
            if bigendian: bytes.reverse()
        numeric_value = 0
        for shift, byte in zip(range(0, len(bytes)*bits, bits), bytes):
            numeric_value += byte << shift
        if isinstance(numeric_value, long):
            self = long.__new__(BitPaddedLong, numeric_value)
        else:
            self = int.__new__(BitPaddedInt, numeric_value)
        self.bits = bits
        self.bigendian = bigendian
        return self

    def as_str(self,value, bits=7, bigendian=True, width=4):
        bits = getattr(value, 'bits', bits)
        bigendian = getattr(value, 'bigendian', bigendian)
        value = int(value)
        mask = (1<<bits)-1
        bytes = []
        while value:
            bytes.append(value & mask)
            value = value >> bits
        # PCNT and POPM use growing integers of at least 4 bytes as counters.
        if width == -1: width = max(4, len(bytes))
        if len(bytes) > width:
            raise ValueError, 'Value too wide (%d bytes)' % len(bytes)
        else: bytes.extend([0] * (width-len(bytes)))
        if bigendian: bytes.reverse()
        return ''.join(map(chr, bytes))
    to_str = staticmethod(as_str)
    

class BitPaddedLong(long):
    def as_str(value, bits=7, bigendian=True, width=4):
        return BitPaddedInt.to_str(value, bits, bigendian, width)
    to_str = staticmethod(as_str)