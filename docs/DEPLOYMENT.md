# AEGIS — 100% Free Live Cloud Hosting Guide

You can host AEGIS online for free so anyone (examiners, friends, faculty) can access it directly via a public URL like:
`https://aegis-mission-control.onrender.com`

---

## Method 1: Render.com (Recommended — Single Unified Deployment)

Render allows hosting both the Python FastAPI backend and the React Vite frontend together in a single **free web service**.

### Steps (Takes 2 minutes):
1. Go to **[https://render.com](https://render.com)** and sign up or log in using your GitHub account (`muneeb-sawez`).
2. Click **New +** &rarr; **Web Service**.
3. Select your repository: **`muneeb-sawez/aegis`**.
4. Configure the settings:
   - **Name:** `aegis` (or `aegis-mission-control`)
   - **Region:** Any (e.g., Singapore or Oregon)
   - **Branch:** `main`
   - **Runtime:** `Python`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && cd frontend && npm install && npm run build
     ```
   - **Start Command:**
     ```bash
     python -m uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** `Free`
5. Click **Create Web Service**.
6. Render will automatically build the React frontend, install Python dependencies, and launch the server.
7. You will get a permanent public link:
   👉 **`https://aegis-xxxx.onrender.com`**

---

## Method 2: Railway.app (Alternative 1-Click)

1. Go to **[https://railway.app](https://railway.app)** and log in with GitHub.
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select `muneeb-sawez/aegis`.
4. Railway will automatically detect the `Dockerfile` in the root, build the frontend and backend, and deploy it.
5. In project settings, click **Generate Domain**.

---

## Method 3: Instant Public Demo via LocalTunnel (Zero Setup)

If you just want your friend to see it right now from their phone without setting up cloud accounts:

1. On your PC, make sure both servers are running:
   - Backend: `python -m uvicorn backend.api.main:app --port 8000`
   - Frontend: `cd frontend && npm run dev`
2. Open a new terminal and run:
   ```bash
   npx localtunnel --port 5173
   ```
3. Copy the URL (e.g. `https://wild-tiger-55.loca.lt`) and send it to your friend!
