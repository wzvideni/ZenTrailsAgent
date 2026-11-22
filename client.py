"""Minimal client for the Zen Trails agent bridge (line protocol over TCP)."""
import socket, sys

class Bridge:
    def __init__(self, host="127.0.0.1", port=5123, timeout=20.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.seq = 0
        self.buf = b""

    def cmd(self, name, *args):
        self.seq += 1
        seq = str(self.seq)
        line = "\t".join([seq, name] + [str(a) for a in args]) + "\n"
        self.sock.sendall(line.encode("utf-8"))
        return self._read_reply(seq)

    def _read_line(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("bridge closed")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8")

    def _read_reply(self, seq):
        while True:
            head = self._read_line().split("\t")
            if head[0] != "R":
                continue
            _, rseq, status, length = head
            need = int(length)
            while len(self.buf) < need:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("bridge closed mid-payload")
                self.buf += chunk
            body = self.buf[:need]
            self.buf = self.buf[need:]
            return status, body.decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    b = Bridge()
    if len(sys.argv) > 1:
        name, args = sys.argv[1], sys.argv[2:]
        st, out = b.cmd(name, *args)
        print(f"[{st}]")
        print(out)
    else:
        print(b.cmd("ping"))
    b.close()
