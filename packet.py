import struct


class Packet(object):
    def __init__(self, src_prt, dst_prt, seq_no, ack_no, checksum=0, ack=1, syn=0, fin=0, _psh=0, _rst=0,
                 _window=2 ** 16 - 1, _head_len=5, _reserved=0, _urg=0, _urg_ptr=0):
        self.src_prt = src_prt
        self.dst_prt = dst_prt
        self.seq_no = seq_no
        self.ack_no = ack_no
        self.checksum = checksum
        self.ack = ack
        self.syn = syn
        self.fin = fin
        self._psh = _psh
        self._rst = _rst
        self._window = _window
        self._head_len = _head_len
        self._reserved = _reserved
        self._urg = _urg
        self._urg_ptr = _urg_ptr
        self.__fmt = "HHIIHHHH"

    def pack(self):
        # fixme create checksum
        return struct.pack(self.__fmt, self.src_prt, self.dst_prt, self.seq_no, self.ack_no,
                           _s(self._head_len, 12) + _s(self._reserved, 6) + _s(self._urg, 5) + _s(self.ack, 4) + _s(
                               self._psh, 3) + _s(self._rst, 2) + _s(self.syn, 1) + self.fin, self._window,
                           self.checksum, self._urg_ptr)

    @classmethod
    def unpack(cls, arr):
        cls.__fmt = "HHIIHHHH"
        cls.src_prt, cls.dst_prt, cls.seq_no, cls.ack_no, cpx, cls._window, cls.checksum, \
        cls._urg_ptr = struct.unpack(cls.__fmt, arr)
        cls._head_len = _r(cpx, 12, 4)
        cls._reserved = _r(cpx, 6, 6)
        cls._urg = _r(cpx, 5)
        cls.ack = _r(cpx, 4)
        cls._psh = _r(cpx, 3)
        cls._rst = _r(cpx, 2)
        cls.syn = _r(cpx, 1)
        cls.fin = _r(cpx, 0)
        # fixme check checksum
        return cls, True

    def __str__(self):
        return "from " + str(self.src_prt) + " to " + str(self.dst_prt) + " seq: " + str(self.seq_no) + " ack: " + str(
            self.ack_no)


def _s(value, shift):
    return value * 2 ** shift


def _r(value, right, length=1):
    return (value // 2 ** right) % (2 ** length)
