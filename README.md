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

## Usage

1. Ensure the FastAPI backend is running and exposes `POST /analyze`.
2. Enter a company name in the input field.
3. Click **Submit** to fetch the analysis. Results (raw JSON) render on the right panel.

Any errors returned by the API will be displayed below the form.

## Run via Docker

To build the static frontend inside Docker and serve it with Nginx:

```bash
# Optional: choose the backend base URL the frontend should call
export VITE_API_URL=http://localhost:8000

docker compose up --build frontend
```

The container runs `npm run build` during the image build and serves the compiled assets through Nginx on port `4173` (mapped from container port `80`). Open `http://localhost:4173` in your browser.

If the backend is reachable via a different host/IP (for example, a Raspberry Pi on your LAN), point `VITE_API_URL` at that address before running `docker compose up`:

```bash
export VITE_API_URL=http://192.168.1.192:8000
docker compose up --build frontend
```
