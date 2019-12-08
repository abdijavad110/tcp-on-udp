import socket
import threading
from conf import Conf
from packet import Packet
from time import time, sleep
from random import randint


class UDP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((Conf.CLIENT_CONF.UDP_IP, Conf.CLIENT_CONF.UDP_PORT))

    def send(self, packet, addr):
        self.sock.sendto(packet, addr)

    def recv(self):
        return self.sock.recvfrom(1024)


class TCP:
    def __init__(self):
        self.addr = (Conf.CLIENT_CONF.UDP_IP, Conf.CLIENT_CONF.UDP_PORT)
        self.listener_port = Conf.SERVER_CONf.TCP_PORT
        self.port = Conf.CLIENT_CONF.TCP_PORT
        # self.seq_no = randint(0, 2 ** 32 - 1)
        self.seq_no = 0
        self.state = Conf.CLT_TCP.CLOSED

        self.in_Q = []
        self.out_Q = []
        self.in_lock = threading.Lock()
        self.out_lock = threading.Lock()

        self.wnd = []
        self.wnd_size = 1
        self.time_out = 4
        self.snd_base = self.seq_no
        self.wnd_lock = threading.Lock()

        self.timer = TCP.Timer(self)

        self.__create_conn()

        self.snd_thread = threading.Thread(target=self.snd_service)
        self.rcv_thread = threading.Thread(target=self.rcv_service)
        self.inp_thread = threading.Thread(target=self.enq_in)
        self.snd_thread.setDaemon(True)
        self.rcv_thread.setDaemon(True)
        self.inp_thread.setDaemon(True)
        self.snd_thread.start()
        self.rcv_thread.start()
        self.inp_thread.start()

    def __create_conn(self):
        pkt = Packet(self.port, self.listener_port, self.seq_no, 0, syn=1, ack=0)
        self.seq_no += 1
        self.enq_out(pkt)
        self.state = Conf.CLT_TCP.SYN_SENT

    def enq_out(self, msg, high_priority=False):
        self.out_lock.acquire()
        if high_priority:
            self.out_Q.insert(0, msg)
        else:
            self.out_Q.append(msg)
        self.out_lock.release()

    def enq_in(self):
        while True:
            msg, _ = udp.recv()
            self.in_lock.acquire()
            self.in_Q.append(msg)
            self.in_lock.release()

    def rcv_service(self):
        while True:
            if self.state == Conf.CLT_TCP.TIMED_WAIT:
                # fixme timed wait
                self.state = Conf.CLT_TCP.CLOSED
                print("connection closed.")
                break

            while len(self.in_Q) == 0:
                sleep(.0003)
            pkt, ok = Packet.unpack(self.in_Q[0])
            self.in_lock.acquire()
            self.in_Q.pop(0)
            self.in_lock.release()
            if not ok:
                continue

            if self.state == Conf.CLT_TCP.SYN_SENT:
                if pkt.syn != 1 or pkt.ack != 1 or pkt.ack_no != self.seq_no:
                    continue
                self.state = Conf.CLT_TCP.ESTAB
                self.snd_base = self.seq_no
                self.enq_out(Packet(self.port, self.listener_port, 0, pkt.seq_no + 1))
                print("connection established.")

            elif self.state == Conf.CLT_TCP.FIN_WAIT_1:
                if pkt.ack != 1 or pkt.ack_no != self.seq_no:
                    continue
                self.state = Conf.CLT_TCP.FIN_WAIT_2

            elif self.state == Conf.CLT_TCP.FIN_WAIT_2:
                if pkt.fin != 1:
                    continue
                self.enq_out(Packet(self.port, self.listener_port, 0, pkt.seq_no + 1))
                self.state = Conf.CLT_TCP.TIMED_WAIT

            else:
                print "++++ packet", pkt.ack_no, "ack received"
                if pkt.ack_no >= self.snd_base:
                    self.snd_base = pkt.ack_no
                    self.wnd_lock.acquire()
                    try:
                        idx = self.wnd.index(self.snd_base - 1)
                    except ValueError:
                        self.wnd_lock.release()
                        continue

                    self.wnd = self.wnd[idx + 1:]

                    # for all received packets
                    # self.wnd_size = self.wnd_size + idx + 1 if self.wnd_size + idx + 1 <= 20 else 20
                    # for just ack
                    self.wnd_size = self.wnd_size + 1 if self.wnd_size < 20 else 20

                    if len(self.wnd) != 0:
                        self.timer.restart()
                        pass
                    else:
                        self.timer.cancel()
                        pass
                    self.wnd_lock.release()

    def close_conn(self):
        self.enq_out(Packet(self.port, self.listener_port, self.seq_no, 0, ack=0, fin=1))
        self.state = Conf.CLT_TCP.FIN_WAIT_1
        self.seq_no += 1

    def snd_service(self):
        while True:
            while len(self.out_Q) == 0:
                sleep(.0003)

            self.out_lock.acquire()
            pkt = self.out_Q.pop(0)
            msg = pkt.pack()


            print "....sending", pkt.seq_no, "WS:", self.wnd_size

            udp.send(msg, (Conf.SERVER_CONf.UDP_IP, Conf.SERVER_CONf.UDP_PORT))
            self.out_lock.release()

    class Timer:
        def __init__(self, sup_tcp):
            self.tcp = sup_tcp
            self.timer = None

        def is_alive(self):
            return self.timer is not None and self.timer.is_alive()

        def start(self):
            if self.timer is None or not self.timer.is_alive():
                self.timer = threading.Timer(self.tcp.time_out, self.tcp.time_out_func)
                self.timer.start()

        def cancel(self):
            self.timer.cancel()
            self.timer = None

        def restart(self):
            if self.timer is not None:
                self.cancel()
            self.start()

    def time_out_func(self):
        print "%%%% timed out", "wnd:", self.wnd
        self.wnd_lock.acquire()
        if len(self.wnd) == 0:
            self.wnd_lock.release()
            return
        not_yet_acked = self.wnd[0]
        self.enq_out(Packet(self.port, self.listener_port, not_yet_acked, 0, ack=0), high_priority=True)
        self.timer.restart()
        self.wnd_size = self.wnd_size // 2 if self.wnd_size > 1 else 1
        self.wnd_lock.release()

    def send_test_data(self):
        start = time()
        while time() - start < Conf.CLIENT_CONF.DATA_TRANSMISSION_TIME:
            while True:
                self.wnd_lock.acquire()
                if len(self.wnd) < self.wnd_size:
                    break
                self.wnd_lock.release()
                sleep(0.02)

            self.wnd.append(self.seq_no)
            self.enq_out(Packet(self.port, self.listener_port, self.seq_no, 0, ack=0))

            self.seq_no += 1
            self.timer.start()
            self.wnd_lock.release()
            sleep(0.1)


if __name__ == "__main__":
        udp = UDP()

        # initiate TCP
        tcp = TCP()

        # send data
        sleep(5)
        tcp.send_test_data()

        # close TCP
        sleep(3)  # delete later
        tcp.close_conn()
        tcp.rcv_thread.join()
        tcp.snd_base
