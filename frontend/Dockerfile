FROM node:20-bookworm-slim

WORKDIR /app

COPY package*.json ./

RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 3000

# Runs in development mode and uses a glibc-based image so Tailwind oxide optional bindings load correctly.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
