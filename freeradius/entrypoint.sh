#!/bin/sh
set -eu
if [ "${LINTECH_RADIUS_ISOLATED:-0}" = "1" ]; then
    test "${#LINTECH_RADIUS_INTERNAL_TOKEN}" -ge 32 || exit 1
    cp /opt/lintech/lintech-clients.conf /etc/freeradius/3.0/clients.conf
    # inner-tunnel is unused; preserve its file but remove the listener symlink.
    rm -f /etc/freeradius/3.0/sites-enabled/default /etc/freeradius/3.0/sites-enabled/inner-tunnel
    rm -f /etc/freeradius/3.0/mods-enabled/eap
    cp /opt/lintech/lintech-site /etc/freeradius/3.0/sites-enabled/lintech
    cp /opt/lintech/lintech-dynamic /etc/freeradius/3.0/sites-enabled/lintech-dynamic
    cp /opt/lintech/lintech-rest /etc/freeradius/3.0/mods-enabled/lintech-rest
fi
exec "$@"
