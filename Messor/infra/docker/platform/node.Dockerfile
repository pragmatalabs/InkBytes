FROM node:22-alpine

WORKDIR /var/www/html

CMD ["sh", "-lc", "npm install --legacy-peer-deps && npm run dev -- --host 0.0.0.0 --port 5173"]
