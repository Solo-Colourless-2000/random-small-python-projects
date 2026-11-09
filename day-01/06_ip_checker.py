"""Check whether an IP address belongs to a CIDR network."""
import ipaddress
import sys


def main():
    if len(sys.argv) !=3:
        print("Usage: python3 06_ip_checker.py <ip_address> <network/CIDR>")
        return 2

    try:
        address = ipaddress.ip_address(sys.argv[1])
        network = ipaddress.ip_network(sys.argv[2], strict=True)
    except ValueError as error:
        print(f"Error: Invalid IP address or network: {error}")
        return 2

    if address.version != network.version:
        print("Error: IPv4 and IPv6 cannot be mixed.")
        return 2

    print(f"IP: {address}")
    print(f"Network: {network}")
    print("Result: MATCH" if address in network else "Result: NO MATCH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
