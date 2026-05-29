FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 3000

# Runs in development mode to avoid alpine musl-arm64 native compilation errors of Tailwind oxide compiler
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
