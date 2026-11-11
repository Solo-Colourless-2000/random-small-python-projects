"""Probe TCP services on loopback only; demo server stays local."""
import socket
import sys
import threading

HOST = "127.0.0.1"


def probe(port):
    try:
        with socket.create_connection((HOST, port), timeout=0.5) as client:
            client.settimeout(0.5)
            try:
                reply = client.recv(64)
                banner = reply.decode("ascii", errors="replace").strip() if reply else "(peer closed without banner)"
            except socket.timeout:
                banner = "(no banner within timeout)"
            except OSError:
                # The TCP handshake already succeeded; receiving the banner failed.
                banner = "(banner read failed)"
            return "OPEN", banner
    except OSError:
        return "CLOSED/UNREACHABLE", ""


def demo():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve_once():
            client, _ = server.accept()
            with client:
                client.sendall(b"LAB SERVICE\n")

        thread = threading.Thread(target=serve_once, daemon=True)
        thread.start()
        status, banner = probe(port)
        thread.join(timeout=2)
        print(f"Local demo port: {port}")
        print(f"Status: {status}")
        print(f"Banner: {banner}")
        return 0 if status == "OPEN" and banner == "LAB SERVICE" else 1


def main():
    if sys.argv[1:] == ["demo"]:
        try:
            return demo()
        except OSError as exc:
            print(f"Demo unavailable: {exc}")
            return 1
    if len(sys.argv) != 3 or sys.argv[1] != "check":
        print("Usage: python3 03_loopback_probe.py demo|check PORT")
        return 2
    try:
        if len(sys.argv[2]) > 8 or not sys.argv[2].isascii() or not sys.argv[2].isdecimal():
            raise ValueError
        port = int(sys.argv[2])
        if port < 1 or port > 65535:
            raise ValueError
    except ValueError:
        print("Error: port must be between 1 and 65535")
        return 2
    status, banner = probe(port)
    print(f"127.0.0.1:{port}: {status}")
    if banner:
        print(f"Banner: {banner}")
    # A TCP check succeeds on connection, whether or not a banner was sent.
    return 0 if status == "OPEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
