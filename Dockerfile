# Log Horizon — combined Railway deployment
# Stage 1: build the React/Vite website.
FROM node:22-bookworm-slim AS website-build
WORKDIR /site

COPY website/package.json ./package.json
RUN npm install --no-audit --no-fund

COPY website/ ./
RUN npm run build

# Stage 2: run Horizon AI + the aiohttp website/dashboard together.
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . ./
COPY --from=website-build /site/dist ./website/dist

# Railway supplies the runtime PORT dynamically. dashboard.py binds to it.
CMD ["python", "bot.py"]
