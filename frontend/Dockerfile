# Build Stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package.json from frontend directory
COPY frontend/package.json frontend/
WORKDIR /app/frontend
RUN npm install

# Copy the rest of the frontend code and database_artefacts
WORKDIR /app
COPY frontend/ frontend/
COPY database_artefacts/ database_artefacts/

# Change working directory to frontend to run the build
WORKDIR /app/frontend
RUN npm run build

# Runtime Stage
FROM nginx:alpine

# Copy build artifacts
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Copy custom configuration
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/entrypoint.sh /docker-entrypoint.d/99-custom-entrypoint.sh

# Make entrypoint executable
RUN chmod +x /docker-entrypoint.d/99-custom-entrypoint.sh

EXPOSE 8080

# Nginx image automatically runs entrypoint scripts in /docker-entrypoint.d/
# and then starts nginx.
