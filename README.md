# Finvarta Analysis

Financial analysis tool using OpenAI to analyze company fundamentals from Screener.in data.

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

## Quick Start with Docker

1. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

2. **Start all services:**
   ```bash
   docker compose up --build
   ```

3. **Access the application:**
   - Frontend: http://localhost:4173
   - Backend API: http://localhost:8000
   - Health check: http://localhost:8000/health

That's it! The application is now running.

## Local Development (Without Docker)

### Backend Setup

```bash
pip install -r requirements.txt
python analysis.py
```

The backend will start on `http://localhost:8000`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open the printed Vite URL (defaults to `http://localhost:5173`) in a browser.

## Usage

1. Ensure the FastAPI backend is running and exposes `POST /analyze`.
2. Enter a company name in the input field.
3. Click **Submit** to fetch the analysis. Results (raw JSON) render on the right panel.

Any errors returned by the API will be displayed below the form.

## Docker Configuration

### Environment Variables

The `.env` file supports the following variables:

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `VITE_API_URL` - Backend API URL for the frontend (default: `http://localhost:8000`)

### Running Individual Services

To run only the backend:
```bash
docker compose up --build backend
```

To run only the frontend:
```bash
docker compose up --build frontend
```

### Custom Backend URL

If the backend is reachable via a different host/IP (for example, a Raspberry Pi on your LAN), update `VITE_API_URL` in your `.env` file:

```
VITE_API_URL=http://192.168.1.192:8000
```

Then rebuild the frontend:
```bash
docker compose up --build frontend
```

## Troubleshooting

### Docker Issues

- **Port already in use**: Make sure ports 8000 and 4173 are not already in use
- **API key not working**: Verify your `OPENAI_API_KEY` in `.env` is correct and has no extra spaces
- **Frontend can't reach backend**: Check that `VITE_API_URL` in `.env` matches your backend URL

### Backend Issues

- **Missing API key error**: Ensure `.env` file exists and contains `OPENAI_API_KEY`
- **Connection errors**: Check that the backend container is running: `docker compose ps`

### Frontend Issues

- **Build errors**: Try rebuilding with `docker compose up --build frontend`
- **API calls failing**: Verify `VITE_API_URL` is correct and backend is accessible
