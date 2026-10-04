# Singapore HTTPS deployment

The public domains are `zqxiaochengxv.xin` and `www.zqxiaochengxv.xin`.
Caddy terminates TLS, redirects HTTP to HTTPS, and renews certificates automatically.
Keep the `caddy_data` volume: it contains the ACME account and certificates.

Run from `/opt/openhrm` for all future deployment updates:

```sh
docker compose -f docker-compose.prod.yml -f docker-compose.https.yml up -d --build
```

The HTTPS overlay removes the frontend's public port and mounts its Nginx
configuration. Caddy is the public entry point on TCP 80 and 443. Nginx preserves
the forwarded HTTPS scheme for Django and OnlyOffice. Internal OnlyOffice
callbacks continue to use `http://frontend` on the Docker network.

Verification:

```sh
curl -I https://zqxiaochengxv.xin
curl -I https://www.zqxiaochengxv.xin
curl -I http://zqxiaochengxv.xin
curl https://zqxiaochengxv.xin/onlyoffice/healthcheck
```

Expect HTTPS 200, HTTP 308, and OnlyOffice `true`. Do not use `curl -k`.
