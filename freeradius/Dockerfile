FROM debian:bookworm-slim

ARG LINTECH_RELEASE=development
LABEL org.opencontainers.image.revision=$LINTECH_RELEASE

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        freeradius \
        freeradius-postgresql \
        freeradius-rest \
        freeradius-utils \
        postgresql-client \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY clients.conf /etc/freeradius/3.0/clients.conf
COPY sql /etc/freeradius/3.0/mods-available/sql

RUN rm -f /etc/freeradius/3.0/mods-enabled/sql \
    && ln -s \
        /etc/freeradius/3.0/mods-available/sql \
        /etc/freeradius/3.0/mods-enabled/sql \
    && sed -i \
        's/^[[:space:]]*-sql/        sql/' \
        /etc/freeradius/3.0/sites-enabled/default

EXPOSE 1812/udp
EXPOSE 1813/udp

COPY lintech-* /opt/lintech/
COPY entrypoint.sh /usr/local/bin/lintech-radius
RUN chmod +x /usr/local/bin/lintech-radius
ENTRYPOINT ["lintech-radius"]
CMD ["freeradius", "-f"]