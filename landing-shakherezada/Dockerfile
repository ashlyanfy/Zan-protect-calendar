# Статический лендинг Шехерезады — отдаётся Caddy.
# Railway подставляет порт в переменную PORT.
FROM caddy:2-alpine
WORKDIR /srv
COPY . /srv
RUN rm -f /srv/Dockerfile /srv/README.md && mv /srv/Caddyfile /etc/caddy/Caddyfile
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
