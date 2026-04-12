#!/usr/bin/env python3
"""Listen for X-Plane UDP broadcast packets (Data Output mode)."""

import socket
import struct
import time

def listen_for_broadcast(port=49000, duration_sec=5):
    """Capture raw UDP broadcast from X-Plane."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(1.0)
    
    print(f"Listening for X-Plane broadcast UDP on port {port} for {duration_sec} seconds...")
    print("(X-Plane Settings→Data Output must have 'Send network data output' enabled)\n")
    
    start_time = time.time()
    packet_count = 0
    
    try:
        while time.time() - start_time < duration_sec:
            try:
                data, (ip, src_port) = sock.recvfrom(4096)
                packet_count += 1
                
                # Try to parse the packet
                if len(data) >= 4:
                    header = data[:4]
                    print(f"✓ Packet {packet_count}: {len(data)} bytes from {ip}:{src_port}")
                    print(f"  Header: {header}")
                    
                    # X-Plane DATA packets start with "DATA"
                    if header == b"DATA":
                        print(f"  → This is X-Plane DATA format ✓")
                        if len(data) >= 9:
                            # Bytes 4-8 are little-endian index
                            index = struct.unpack("<I", data[4:8])[0]
                            print(f"  → Data index: {index}")
                    else:
                        print(f"  → Header: {header} (not DATA format)")
                    print()
                    
            except socket.timeout:
                continue
                
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
    
    print(f"\nResults: Received {packet_count} packets in {duration_sec} seconds")
    
    if packet_count == 0:
        print("❌ No packets received!")
        print("\nTroubleshooting:")
        print("  1. Verify Settings → Data Output → 'Send network data output' is CHECKED")
        print("  2. Verify port is set to 49000")
        print("  3. Verify IP is 127.0.0.1")
        print("  4. Make sure simulation is RUNNING and UNPAUSED (press Spacebar)")
        print("  5. Check Windows Firewall for UDP port 49000")
        return False
    else:
        print(f"✅ X-Plane broadcast confirmed! Receiving {packet_count / duration_sec:.1f} packets/sec")
        return True

if __name__ == "__main__":
    import sys
    connected = listen_for_broadcast(duration_sec=5)
    sys.exit(0 if connected else 1)
