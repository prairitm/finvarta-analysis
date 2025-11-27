# Finvarta Frontend

React UI for sending company analysis requests to the FastAPI backend.

## Prerequisites

- Node.js 18+ and npm
- FastAPI server running locally at `http://localhost:8000`

## Setup

```bash
cd frontend
npm install
```

## Run the Dev Server

```bash
npm run dev
```

Open the printed Vite URL (defaults to `http://localhost:5173`) in a browser.  
If you need to access the dev server from another device or via Docker, run `npm run dev -- --host 0.0.0.0` and forward port 5173.

## Run the Frontend via Docker

```bash
docker compose up --build frontend
```

This launches the Node-based Vite dev server inside the container with `npm run dev -- --host 0.0.0.0 --port 5173`. The compose file maps container port `5173` to the same port on your host, so you can open `http://localhost:5173` exactly as if you were running Vite locally. The container sets `VITE_API_URL=http://backend:8000`, allowing it to call the FastAPI service defined in the same compose stack.

## Usage

1. Ensure the FastAPI backend is running and exposes `POST /analyze`.
2. Enter a company name in the input field.
3. Click **Submit** to fetch the analysis. Results (raw JSON) render on the right panel.

Any errors returned by the API will be displayed below the form.
