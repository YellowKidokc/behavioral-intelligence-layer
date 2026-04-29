import urllib.request, json

# Test 1: Send clipboard event
data = json.dumps({"text": "The Master Equation chi equals the product of all ten variables integrated over spacetime", "app": "claude_test"}).encode()
req = urllib.request.Request("http://localhost:8420/bil/clipboard", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=5)
print("Clipboard POST:", resp.read().decode())

# Test 2: Send another
data2 = json.dumps({"text": "Law 7 is Quantum Mechanics mapped to Faith", "app": "obsidian"}).encode()
req2 = urllib.request.Request("http://localhost:8420/bil/clipboard", data=data2, headers={"Content-Type": "application/json"})
resp2 = urllib.request.urlopen(req2, timeout=5)
print("Clipboard POST 2:", resp2.read().decode())

# Test 3: Send a used/paste event
data3 = json.dumps({"text": "The Master Equation chi equals the product of all ten variables integrated over spacetime", "app": "claude_test", "used": True}).encode()
req3 = urllib.request.Request("http://localhost:8420/bil/clipboard", data=data3, headers={"Content-Type": "application/json"})
resp3 = urllib.request.urlopen(req3, timeout=5)
print("Paste event:", resp3.read().decode())

# Test 4: Get predictions
resp4 = urllib.request.urlopen("http://localhost:8420/bil/clipboard/predict?limit=5", timeout=5)
print("Predictions:", resp4.read().decode())

# Test 5: Status
resp5 = urllib.request.urlopen("http://localhost:8420/bil/status", timeout=5)
print("Status:", resp5.read().decode())
