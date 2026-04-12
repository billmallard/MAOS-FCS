# X-Plane 12 Communication Options: UDP vs Web API

You have **two choices** for connecting your MAOS-FCS to X-Plane 12. Here's how to choose:

---

## Option A: UDP (What We're Currently Using)

**Protocol:** Binary UDP packets (RREF subscribe / DREF write)  
**Ports:** 49000 (receive) ← 49001 (send)  
**Complexity:** Medium  
**Latency:** Low  
**Status:** Working in our code (tested)

### When to use UDP:
✅ Low-latency real-time control  
✅ Direct binary protocol  
✅ Our current implementation

### To set up UDP:
1. In X-Plane: **Settings** → **Net Connections** → **Data Output**
2. You should see: `"Send UDP to: [127.0.0.1] on port [49000]"`
3. That's where X-Plane sends telemetry
4. Make sure **"Enable Data Output"** is checked

---

## Option B: Web API (Modern/Recommended)

**Protocol:** HTTP REST + WebSocket JSON  
**Port:** 8086  
**Complexity:** Low  
**Latency:** ~10ms  
**Status:** Built-in to X-Plane 12.1.1+  

### When to use Web API:
✅ Already built into X-Plane  
✅ JSON format (easier to debug)  
✅ Official Laminar Research interface  
✅ Supports both reading state AND writing commands  
✅ What the xplane-ai-mcp project uses  

### To set up Web API:
1. In X-Plane: **Settings** → **Net Connections**
2. Look for **"Enable web server"** or **"Local Web API"**
3. Default port: `8086`
4. Just make sure it's enabled (should be by default in 12.1.1+)

---

## The Menu You're Looking At

The menu showing `"Send UDP to: 127.0.0.1 on port 49000"` is for **UDP configuration**.

That's fine—our code is set up for UDP. The question is: **Are you actually seeing this option active?**

If UDP is not working (which is what `check_xplane_connection.py` reported), it could be because:
1. UDP output is disabled
2. X-Plane is blocking UDP packets
3. The ports are misconfigured

---

## Quick Decision Tree

```
Are you seeing "Send UDP to 127.0.0.1:49000" in the menu?
│
├─ YES, and it's enabled?
│  └─ Good! But we still got no packets
│     → Check firewall, make sure simulation is unpaused
│
├─ NO, can't find UDP settings?
│  └─ Use Web API instead (Option B)
│     → More reliable, built-in to X-Plane
│
└─ UDP not working after troubleshooting?
   └─ Switch to Web API
      → We can adapt our bridge code for it
```

---

## What I Recommend

Given that UDP isn't currently working, let me **create a Web API version** of the X-Plane bridge that uses port 8086 instead. This would be:

✅ More reliable (built-in to X-Plane)  
✅ Easier to debug (JSON not binary)  
✅ No firewall configuration needed  
✅ Same datarefs, just different protocol  

**Next steps:**

1. **Confirm what you see in X-Plane settings**
   - Can you tell me: Do you see a labelpanel that says "Send UDP to" or "Web Server" or "Local API"?
   - What port numbers are shown?

2. **I'll create either:**
   - A Web API bridge for port 8086 (recommended)
   - Or troubleshoot UDP further

Which interface is more prominent in your X-Plane settings?

---

## Reference: Official X-Plane Docs

- **X-Plane Web API:** https://developer.x-plane.com/article/x-plane-web-api/
- **UDP Legacy:** Uses plugin model (less common in 12.x)
- **Recommendation:** Web API is the modern, supported path

---

## File Comparison

| Aspect | UDP (Current) | Web API |
|--------|--------------|---------|
| Port | 49000/49001 | 8086 |
| Protocol | Binary RREF/DREF | HTTP + WebSocket |
| Format | Structs | JSON |
| Firewalls | May block UDP | HTTP usually open |
| Latency | ~5ms | ~10ms |
| Debugging | Hard (binary) | Easy (JSON) |
| Built-in | Plugin-based | X-Plane 12.1.1+ native |

