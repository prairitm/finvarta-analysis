FROM node:20-alpine

WORKDIR /app/frontend

# Install dependencies first for better caching
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the source
COPY frontend/. .

# Ensure Vite can talk to the backend container by default
ENV VITE_API_URL=http://backend:8000

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
