# Статический лендинг Шехерезады — отдаётся Caddy.
# Railway подставляет порт в переменную PORT.
FROM caddy:2-alpine
WORKDIR /srv
COPY . /srv
RUN rm -f /srv/Dockerfile /srv/README.md
CMD ["sh", "-c", "caddy file-server --root /srv --listen :${PORT:-8080}"]
