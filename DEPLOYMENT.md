# Deploying ChronoNote: Vercel (Frontend) + Railway (Backend)

ChronoNote is architected for high-performance split deployment:
- **Frontend (Vue 3 SPA + Heatmap)**: Hosted on **Vercel** with global edge CDN and instant caching.
- **Backend (FastAPI + WebSockets + PostgreSQL)**: Hosted on **Railway** with persistent WebSocket collaboration (`/ws/*`), task cascading engine, and PostgreSQL 16 database.

---

## 1. Deploy the Backend to Railway (First)

1. Open [Railway.app](https://railway.app/) and click **New Project → Deploy from GitHub repo**.
2. Select your `ChronoNote` repository.
3. In Railway, click **Add Service → Database → Add PostgreSQL**.
4. In the FastAPI service settings, Railway will automatically detect [`railway.json`](railway.json) and [`Dockerfile`](Dockerfile).
5. Set your environment variables in Railway:
   - `DATABASE_URL`: Automatically provided by Railway's Postgres plugin (`${{Postgres.DATABASE_URL}}`).
   - `ALLOWED_GOOGLE_EMAILS`: `your.email@gmail.com` (optional, restricts access).
   - `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID (optional).
6. Under **Networking**, click **Generate Domain** (e.g. `https://chrononote-backend.up.railway.app`).

---

## 2. Deploy the Frontend to Vercel (Second)

1. Open [Vercel.com](https://vercel.com/) and click **Add New... → Project**.
2. Select your `ChronoNote` repository.
3. In the project setup screen:
   - **Framework Preset**: Vite
   - **Root Directory**: Click *Edit* and select `frontend`
4. Expand **Environment Variables** and add:
   - `VITE_API_BASE`: `https://chrononote-backend.up.railway.app/api` (use your Railway URL from Step 1)
   - `VITE_GOOGLE_CLIENT_ID`: Your Google OAuth Client ID (optional)
5. Click **Deploy**. Vercel will build the Vue 3 app and deploy it to `https://chrononote.vercel.app`.

---

## 3. Alternative: Single Full-Stack Service (Render or Railway Docker)

If you ever prefer running both Frontend + Backend in a single URL:
- Render Blueprint: [`render.yaml`](render.yaml) builds the Vue frontend and starts the FastAPI server on a single HTTPS URL.
- Railway Dockerfile: [`Dockerfile`](Dockerfile) builds the SPA and serves both `/api/*` and static assets.

---

## 4. Installing ChronoNote on Your Phone (PWA)

Once deployed over HTTPS on Vercel:
- **iOS (Safari)**: Open your Vercel URL, tap **Share**, and select **Add to Home Screen**.
- **Android (Chrome)**: Open your Vercel URL, tap the menu (**⋮**), and select **Add to Home screen / Install app**.
- Tap any date on the **Calendar Timeline** to write your daily journal, log habits, or review your 52-week **Habit Heatmap**.
