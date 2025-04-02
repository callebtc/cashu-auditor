# 🌀 Cashu Round Robin Auditor

_An autonomous auditor that perpetually circulates ecash donations between Cashu mints using Lightning payments. Sats go in circles—until they’re lost to fees or rugs. If a mint fails to pay a Lightning invoice, it’s flagged with a scary red label._



---

## 🧩 Project Structure

This project is split into two parts:

- **Backend** – Auditor logic, wallet management, and API server
- **Frontend** – Visual UI for tracking mint status (located in the [`frontend/`](frontend) folder)

---

## 🎨 Frontend Setup

For details on setting up and deploying the frontend, refer to the [frontend README](frontend/README.md).

---

## ⚙️ Backend Setup

The backend uses a [Nutshell](https://github.com/cashubtc/nutshell) Cashu wallet and exposes an API that publishes audit data in real-time.

### 🔧 1. Clone & Initialize

```bash
git clone <your-repo-url>
cd <project-directory>
git submodule update --init --recursive
```

---

### 📦 2. Install Dependencies

Make sure you have [Poetry](https://python-poetry.org/) installed. You can find install instructions on their [official site](https://python-poetry.org/docs/#installation) or in the [Nutshell README](https://github.com/cashubtc/nutshell).

Then, install the project:

```bash
poetry install
```

---

### 🚀 3. Run the Backend

```bash
poetry run uvicorn src.main:app
```

---

## 🔐 Wallet Configuration

### 1. Environment File

Copy the example env file to start:

```bash
cp .env.example .env
```

Then configure your Cashu wallet settings inside `.env`.

---

### 2. Enable Tor (Recommended)

To help the auditor stay private, it should run over Tor. To use the built-in Tor daemon, set the following in your `.env`:

```
# Use built-in Tor daemon (overrides proxy settings)
TOR=TRUE
```

Alternatively, to use an external Tor instance or proxy:

```
TOR=false
SOCKS_PROXY=socks5://localhost:9050
# or
HTTP_PROXY=http://localhost:8088
```

> ℹ️ Note: When `TOR=TRUE`, any proxy settings are ignored.

---

### 3. Wallet Database

The wallet stores its state—including its ecash and seed phrase—in a file called `wallet.sqlite3`. This is your **only backup**.

> 🔒 **Important:** Make a secure backup of this file, or at minimum, write down the seed phrase stored within.

---

