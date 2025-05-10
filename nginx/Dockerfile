# This Dockerfile builds the frontend and then sets up Nginx.
# It assumes the Docker build context is the project root.

# Stage 1: Build the frontend application
FROM node:18-alpine AS frontend-builder
WORKDIR /app

# Copy package files from the frontend directory
COPY frontend/package.json frontend/package-lock.json* ./
# If you use yarn:
# COPY frontend/yarn.lock ./

RUN npm install
# If you use yarn:
# RUN yarn install

# Copy the rest of the frontend application code
COPY frontend/ ./

# This build will use VITE_API_URL from frontend/.env.production (e.g., /api)
RUN npm run build
# This should create a 'dist' folder in /app/dist (standard for Vite)

# Stage 2: Production Nginx server
FROM nginx:alpine AS production-server

WORKDIR /usr/share/nginx/html

# Remove default Nginx server configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration
# COPY nginx/nginx.conf /etc/nginx/nginx.conf # <-- OLD LINE TO BE REMOVED/COMMENTED
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend assets from the frontend-builder stage
COPY --from=frontend-builder /app/dist/ .

EXPOSE 80

# Start Nginx when the container launches
CMD ["nginx", "-g", "daemon off;"] 