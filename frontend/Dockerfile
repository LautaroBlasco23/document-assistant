FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

EXPOSE 3500

CMD ["sh", "-c", "npx vite preview --port ${FRONTEND_PORT:-3500} --host 0.0.0.0 --strictPort"]
