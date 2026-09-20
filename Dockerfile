# One Railway service: build the complete React website, then run it beside Horizon AI/Discord.
FROM node:22-alpine AS website-build
WORKDIR /site
COPY website/package*.json ./
RUN npm install --no-audit --no-fund
COPY website/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
COPY --from=website-build /site/dist ./website_dist
EXPOSE 8080
CMD ["python", "bot.py"]
