# 🔍 LLM Proxyman (Linux Edition)

A lightweight, robust, and real-time HTTP/HTTPS proxy tailored specifically for intercepting, inspecting, and visualizing Large Language Model (LLM) API requests (OpenAI, Anthropic, Gemini, etc.) on Linux. 

Think of it as a specialized [Proxyman](https://proxyman.io/) or Charles Proxy, but specifically designed to handle **Server-Sent Events (SSE) streaming** out-of-the-box, giving you a live view of tokens as they are generated.

## ✨ Features

- **True HTTPS Interception**: Powered by `mitmproxy` under the hood. Capable of inspecting SSL/TLS encrypted traffic to `api.openai.com`, `api.anthropic.com`, etc.
- **Real-Time Streaming Support**: Flawlessly intercepts and visualizes Server-Sent Events (SSE) streaming tokens in real-time. No more waiting for the full response to finish before seeing the payload!
- **Live Web Dashboard**: A built-in WebSocket UI built with FastAPI that pushes requests, responses, and stream chunks directly to your browser.
- **Developer Friendly**: Zero bloated electron apps. Just pure Python, async performance, and a fast browser UI.

---

## 🏗️ Architecture

The application runs two main asynchronous components concurrently on the same event loop:
1. **Proxy Server (Port 10080)**: A programmatic `mitmproxy` instance with a custom addon that hooks into `request`, `response`, and `responseheaders` lifecycle events.
2. **Dashboard Server (Port 10011)**: A `FastAPI` + `Uvicorn` server that serves the UI and manages WebSocket connections to broadcast intercepted traffic in real-time.

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Linux (Ubuntu/Debian, Arch, Fedora, etc.) or macOS

### Setup

1. **Clone the repository** (or copy the files):
   ```bash
   git clone <your-repo-url>
   cd linux_proxyman
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirement.txt
   ```

---

## 💻 Usage

### 1. Start the Server
Run the main script to start both the Proxy and the Web UI:
```bash
python main.py
```
*You should see output indicating the UI is running on `:10011` and the proxy on `:10080`.*

### 2. Open the Dashboard
Open your favorite web browser and navigate to:
👉 **[http://127.0.0.1:10011](http://127.0.0.1:10011)**

### 3. Configure Your LLM Client
Point your LLM client/application to use the proxy at `http://127.0.0.1:10080`. 

For example, using `curl`:
```bash
export http_proxy=http://127.0.0.1:10080
export https_proxy=http://127.0.0.1:10080
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

Or in Python (`requests`):
```python
import requests

proxies = {
   'http': 'http://127.0.0.1:10080',
   'https': 'http://127.0.0.1:10080',
}
response = requests.get('https://api.openai.com/v1/models', proxies=proxies, verify=False)
```

---

## 🔐 Handling HTTPS & Certificates (Important!)

Because LLM APIs use HTTPS (SSL/TLS), the proxy needs to decrypt the traffic. To do this without your client throwing `CERTIFICATE_VERIFY_FAILED` errors, you must trust the `mitmproxy` CA certificate.

1. **Start the proxy at least once** so it generates the certificates.
2. The certificates are generated in your home directory: `~/.mitmproxy/mitmproxy-ca-cert.pem`.

### How to trust the certificate:

**For Python (Requests/OpenAI SDK)**:
Set the `REQUESTS_CA_BUNDLE` environment variable:
```bash
export REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
python your_llm_script.py
```

**For Node.js / TypeScript**:
```bash
export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem
node your_llm_app.js
```

**For cURL**:
```bash
curl --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem -x http://127.0.0.1:10080 https://api.openai.com/...
```

**System-wide Trust (Ubuntu/Debian)**:
```bash
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

---

## 🛠️ Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/)
- [mitmproxy](https://mitmproxy.org/)
- WebSockets
- Asyncio

## 📜 License
MIT License
