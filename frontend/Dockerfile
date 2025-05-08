# Use an official Node.js runtime as a parent image
# Choose a version that matches your project's requirements (e.g., 18, 20, etc.)
FROM node:18-alpine

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

# The port your frontend development server runs on (e.g., 3000 for React, 5173 for Vite)
# Update this if your frontend runs on a different port
EXPOSE 5173

# The command to start your development server
CMD ["npm", "run", "dev"] 