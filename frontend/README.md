# Cashu Round Robin Auditor – Frontend

This is the frontend application for the **Cashu Round Robin Auditor**, built with [Vue.js](https://vuejs.org/) and the [Quasar Framework](https://quasar.dev/).

---

## 🚀 Getting Started

### 1. Configure Environment

Before running the app, copy the `.env.example` file and rename it to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your backend API URL so the frontend can communicate with it:

```
# URL to your backend API server
VUE_BASE_URL=https://api.domain.com
```

For production builds, you can create a separate `.env.production` file with the same structure.

---

### 2. Install Dependencies

Using Yarn:

```bash
yarn
```

Or using npm:

```bash
npm install
```

---

### 3. Run in Development Mode

Start the app with hot-reloading, error reporting, and live updates:

```bash
quasar dev
```

> ℹ️ This uses the `.env` file by default.

---

## 🏗 Build for Production

Ensure your `.env.production` file is correctly set up with the backend API URL.

```bash
quasar build -m spa --dotenv .env.production
```

Once built, deploy the contents of the `dist/spa` folder to your web server:

```bash
scp -r dist/spa user@yourserver:/path/to/deploy
```

---

## 🧹 Code Quality

### Lint the Code

```bash
yarn lint
# or
npm run lint
```

### Format the Code

```bash
yarn format
# or
npm run format
```

---

## 📁 Project Structure

- `src/` – Vue components and app logic
- `public/` – Static assets
- `dist/spa/` – Compiled production build

---
