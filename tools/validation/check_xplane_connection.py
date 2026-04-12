#!/usr/bin/env python3
"""Quick test to verify X-Plane UDP connectivity."""

import socket
import struct
import time

def listen_for_xplane_packets(port=49000, duration_sec=5):
    """Listen for RREF packets from X-Plane."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(1.0)
    
    print(f"Listening for X-Plane packets on UDP:{port} for {duration_sec} seconds...")
    print("(X-Plane must be running and sending RREF packets)\n")
    
    start_time = time.time()
    packet_count = 0
    
    try:
        while time.time() - start_time < duration_sec:
            try:
                data, (ip, port_src) = sock.recvfrom(4096)
                packet_count += 1
                
                # Parse RREF packet
                if data[:4] == b"RREF":
                    print(f"✓ Packet {packet_count}: RREF from {ip}:{port_src}")
                    # Parse some values if present
                    if len(data) >= 13:
                        payload = data[5:]
                        offset = 0
                        while offset + 8 <= len(payload):
                            index, value = struct.unpack_from("<If", payload, offset)
                            offset += 8
                            
                            labels = {
                                0: "Airspeed (KIAS)",
                                1: "Bank (deg)",
                                2: "Pitch (deg)",
                                3: "Angle of Attack (deg)"
                            }
                            if index in labels:
                                print(f"    [{index}] {labels[index]}: {value:.1f}")
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
        print("  1. Is X-Plane running?")
        print("  2. Is an aircraft loaded?")
        print("  3. Is simulation UNPAUSED? (Press Spacebar)")
        print("  4. Are you running this on the same machine as X-Plane?")
        print("  5. Is port 49000 blocked by firewall?")
        return False
    else:
        print(f"✅ X-Plane connection confirmed! Getting {packet_count / duration_sec:.1f} packets/sec")
        return True

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "sim")
    
    connected = listen_for_xplane_packets(duration_sec=5)
    sys.exit(0 if connected else 1)
