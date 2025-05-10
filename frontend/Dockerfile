# Use an official Node.js runtime as a parent image
# Choose a version that matches your project's requirements (e.g., 18, 20, etc.)
FROM node:18-alpine AS builder

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock if you use Yarn)
COPY package.json ./
COPY package-lock.json ./
# If you use yarn, uncomment the next line and comment out the package-lock.json line
# COPY yarn.lock ./

# Install project dependencies
RUN npm install
# If you use yarn, uncomment the next line and comment out the npm install line
# RUN yarn install

# Copy the rest of the frontend application code into the container
COPY . .

# npm run build will use .env.production (if it exists) by default, setting VITE_API_URL=/api
RUN npm run build

# Stage 2: Development server (this will be targeted by the 'frontend' service in docker-compose)
FROM node:18-alpine AS development
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
# If you use yarn, adjust:
# COPY yarn.lock ./
RUN npm install
# If you use yarn, adjust:
# RUN yarn install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"] 