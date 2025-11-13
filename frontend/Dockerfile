# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Disable source maps for faster build
ENV GENERATE_SOURCEMAP=false

COPY package*.json ./
RUN npm install --legacy-peer-deps --no-package-lock

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

