# Simple lightweight Nginx container to serve the static frontend
FROM nginx:alpine

# Copy all static frontend files to Nginx public html directory
COPY . /usr/share/nginx/html

# Expose port 80 for serving the app
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
