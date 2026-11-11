FROM node:20-alpine
WORKDIR /app

# Build arg pour injecter l'URL API au build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Build avec la variable injectée
RUN npm run build

CMD ["npm", "run", "start"]