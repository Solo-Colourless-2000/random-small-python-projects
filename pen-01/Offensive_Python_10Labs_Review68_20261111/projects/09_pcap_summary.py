"""Read bounded Ethernet/IPv4 TCP/UDP records from a classic PCAP file."""
import ipaddress
import struct
import sys
from pathlib import Path


def summarize_frame(frame):
    if len(frame) < 14 or frame[12:14] != b"\x08\x00":
        return "SKIP not Ethernet IPv4"
    ip = frame[14:]
    if len(ip) < 20 or ip[0] >> 4 != 4:
        return "SKIP invalid IPv4 header"
    header_length = (ip[0] & 15) * 4
    packet_length = int.from_bytes(ip[2:4], "big")
    if header_length < 20 or len(ip) < header_length or packet_length < header_length or len(ip) < packet_length:
        return "SKIP truncated IPv4 packet"
    if int.from_bytes(ip[6:8], "big") & 0x3fff:
        return "SKIP fragmented IPv4 packet"
    protocol = ip[9]
    if protocol not in (6, 17) or packet_length < header_length + 4:
        return "SKIP other or short transport"
    # A port pair alone is not a complete TCP or UDP header.
    transport_min = 20 if protocol == 6 else 8
    if packet_length < header_length + transport_min:
        return "SKIP short transport header"
    transport = ip[header_length:packet_length]
    if protocol == 6:
        tcp_header = (transport[12] >> 4) * 4
        if tcp_header < 20 or tcp_header > len(transport):
            return "SKIP invalid TCP data offset"
    else:
        udp_length = int.from_bytes(transport[4:6], "big")
        if udp_length < 8 or udp_length != len(transport):
            return "SKIP invalid UDP length"
    source, dest = struct.unpack("!HH", transport[:4])
    address_a = ipaddress.IPv4Address(ip[12:16])
    address_b = ipaddress.IPv4Address(ip[16:20])
    kind = "TCP" if protocol == 6 else "UDP"
    return f"{kind} {address_a}:{source} -> {address_b}:{dest}"


def parse_pcap(path):
    if path.stat().st_size > 200_000:
        raise ValueError("pcap exceeds 200000 bytes")
    data = path.read_bytes()
    if len(data) < 24:
        raise ValueError("truncated global header")
    magic = data[:4]
    if magic == b"\xd4\xc3\xb2\xa1":
        order = "<"
    elif magic == b"\xa1\xb2\xc3\xd4":
        order = ">"
    else:
        raise ValueError("only classic microsecond PCAP is supported")
    major, minor, _, _, snaplen, network = struct.unpack_from(order + "HHiIII", data, 4)
    if (major, minor) != (2, 4) or network != 1 or snaplen < 14 or snaplen > 65535:
        raise ValueError("expected PCAP 2.4 with Ethernet link type")
    offset = 24
    lines = []
    while offset < len(data):
        if len(data) - offset < 16:
            raise ValueError("truncated packet record")
        _, micros, caplen, original = struct.unpack_from(order + "IIII", data, offset)
        if micros >= 1_000_000:
            raise ValueError("invalid microsecond timestamp")
        offset += 16
        if caplen > snaplen or caplen > original or caplen > len(data) - offset:
            raise ValueError("invalid captured length")
        lines.append(summarize_frame(data[offset:offset + caplen]))
        offset += caplen
    return lines


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 09_pcap_summary.py sample.pcap")
        return 2
    try:
        lines = parse_pcap(Path(sys.argv[1]))
        for index, line in enumerate(lines, 1):
            print(f"Packet {index}: {line}")
        print(f"Records: {len(lines)}")
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
