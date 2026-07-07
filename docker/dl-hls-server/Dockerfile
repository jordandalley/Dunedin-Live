FROM alpine:latest

# Install Nginx and FFmpeg
RUN apk add --no-cache nginx ffmpeg curl

# Copy Nginx config
COPY build/nginx.conf /etc/nginx/nginx.conf

# Copy entrypoint script
COPY build/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create the web root directory and give permissions to nginx user
#RUN mkdir -p /usr/share/nginx/html && chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

CMD ["/entrypoint.sh"]
