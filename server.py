import socket
import threading
from conf import Conf
from time import sleep
from packet import Packet
from random import randint

connected_tcp_conn = []
rcv_buffer = []
conn_lock = threading.Lock()


drop_list = [30, 30, 30]
# drop_list = []


class UDP:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((Conf.SERVER_CONf.UDP_IP, Conf.SERVER_CONf.UDP_PORT))

    def send(self, packet, address):
        self.sock.sendto(packet, address)

    def recv(self):
        return self.sock.recvfrom(1024)


class TCP:
    def __init__(self, udp_addr):
        self.addr = udp_addr
        self.listener_port = None
        self.port = None
        self.seq_no = 0
        self.state = Conf.SRV_TCP.LISTEN

        self.in_Q = []
        self.out_Q = []
        self.in_lock = threading.Lock()
        self.out_lock = threading.Lock()
        self.rcv_thread = threading.Thread(target=self.rcv_service)
        self.snd_thread = threading.Thread(target=self.snd_service)

        self.rwnd = TCP.Rwnd()

        self.rcv_thread.setDaemon(True)
        self.snd_thread.setDaemon(True)
        self.rcv_thread.start()
        self.snd_thread.start()

    def new_data(self, msg):
        self.in_lock.acquire()
        self.in_Q.append(msg)
        self.in_lock.release()

    def enq_out(self, msg):
        self.out_lock.acquire()
        self.out_Q.append(msg)
        self.out_lock.release()

    def snd_service(self):
        while True:
            while len(self.out_Q) == 0:
                sleep(.001)

            self.out_lock.acquire()
            pkt = self.out_Q[0]
            msg = pkt.pack()
            self.out_Q.pop(0)
            self.out_lock.release()

            udp.send(msg, (Conf.CLIENT_CONF.UDP_IP, Conf.CLIENT_CONF.UDP_PORT))

    def rcv_service(self):
        while True:
            if self.state == Conf.SRV_TCP.CLOSE_WAIT:
                new_pkt = Packet(self.port, self.listener_port, self.seq_no, 0, fin=1)
                self.state = Conf.SRV_TCP.LAST_ACK
                self.enq_out(new_pkt)

            while len(self.in_Q) == 0:
                sleep(.0003)

            pkt, ok = Packet.unpack(self.in_Q[0])


            print "received packet", pkt.seq_no

            self.in_lock.acquire()
            self.in_Q.pop(0)
            self.in_lock.release()
            if not ok:
                continue

            if self.state == Conf.SRV_TCP.LISTEN:
                if pkt.syn != 1:
                    continue
                self.port = pkt.dst_prt
                self.state = Conf.SRV_TCP.SYN_RCVD
                self.listener_port = pkt.src_prt
                # self.seq_no = randint(0, 2 ** 32 - 1)
                self.seq_no = 0
                new_pkt = Packet(pkt.dst_prt, pkt.src_prt, self.seq_no, (pkt.seq_no + 1) % (2 ** 32), syn=1)
                self.rwnd.expected = pkt.seq_no + 1
                self.enq_out(new_pkt)

            elif self.state == Conf.SRV_TCP.SYN_RCVD:
                if pkt.ack != 1 or pkt.ack_no != self.seq_no + 1:
                    continue
                self.seq_no += 1
                self.state = Conf.SRV_TCP.ESTAB
                print "Client", str(self.addr[0]) + ":" + str(self.listener_port), "connected."

            elif self.state == Conf.SRV_TCP.ESTAB and pkt.fin == 1:
                self.state = Conf.SRV_TCP.CLOSE_WAIT
                new_pkt = Packet(pkt.src_prt, pkt.dst_prt, self.seq_no, (pkt.seq_no + 1) % (2 ** 32))
                self.enq_out(new_pkt)

            elif self.state == Conf.SRV_TCP.LAST_ACK:
                if pkt.ack != 1 or pkt.ack_no != self.seq_no + 1:
                    continue
                conn_lock.acquire()
                connected_tcp_conn.remove(self)
                conn_lock.release()
                print("Client ", self.addr[0], ":", self.listener_port, " disconnected.")
                break

            else:
                if pkt.seq_no in drop_list:
                    drop_list.remove(pkt.seq_no)
                    continue
                expected = self.rwnd.new(pkt.seq_no)
                print "packet", expected, "acked"
                self.enq_out(Packet(self.port, self.listener_port, 0, expected))

    class Rwnd:
        def __init__(self):
            self.expected = None
            self.future_pkt = []

        def new(self, seq_no):
            if self.expected == seq_no:
                self.expected += 1
                self.future_pkt.sort()
                for _ in range(len(self.future_pkt)):
                    if self.future_pkt[0] == self.expected:
                        self.expected += 1
                        self.future_pkt.pop(0)
            else:
                self.future_pkt.append(seq_no)
            return self.expected


if __name__ == "__main__":
    udp = UDP()

    while True:
        data, addr = udp.recv()

        tcp = None
        for conn in connected_tcp_conn:
            if conn.addr == addr:
                tcp = conn
                break
        if tcp is None:
            conn_lock.acquire()
            tcp = TCP(addr)
            connected_tcp_conn.append(tcp)
            conn_lock.release()

        tcp.new_data(data)
