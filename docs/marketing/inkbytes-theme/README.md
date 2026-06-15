# InkBytes WordPress theme

The marketing landing theme for **inkbytes.news**, derived 1:1 from
[`../index.html`](../index.html). It's a custom classic theme (single-page) whose
homepage is `front-page.php`. CSS and markup are copied verbatim from the
prototype; the only WordPress-side changes are: head/body hooks (`wp_head`,
`wp_body_open`, `wp_footer`), enqueued fonts + stylesheet, dynamic brand/footer
links, and the "Start reading / Browse" CTAs wired to the reader app
(`INKBYTES_READER_URL`, default `https://inkbytes.org`).

```
inkbytes/
├── style.css        theme header + the full landing-page CSS
├── functions.php    enqueue fonts/stylesheet, reader-URL helper, lean <head>
├── header.php       <head> (fixed marketing <title>/OG), brand SVG, sticky nav
├── front-page.php   the landing page (homepage)
├── footer.php       footer + wp_footer()
└── index.php        fallback for posts/pages/404
```

## Where it runs

`inkbytes.news` WordPress lives on the **Hostinger box** (`82.112.250.139`,
`/docker/wordpress-yybr`) — the same box as Ollama, behind Traefik. It is NOT in
this repo's deploy pipeline; this directory is the **source of record**, deployed
manually.

## Deploy / update

From this directory (`docs/marketing/inkbytes-theme/`):

```bash
# stream the theme into the running container
tar -cf - inkbytes | ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 \
  'docker cp - wordpress-yybr-wordpress-1:/var/www/html/wp-content/themes/'

# fix ownership + lint
ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 \
  'docker exec wordpress-yybr-wordpress-1 sh -c "chown -R www-data:www-data /var/www/html/wp-content/themes/inkbytes && for f in /var/www/html/wp-content/themes/inkbytes/*.php; do php -l \$f; done"'
```

⚠️ Use `docker cp` (or `docker exec -i`), never a bare `docker exec … 'cat > file'`
heredoc — without `-i`, `docker exec` discards stdin and writes a 0-byte file
(and `php -l` on an empty file passes, so it fails silently).

## Activate (no wp-cli on the box)

```bash
ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 \
  'docker exec wordpress-yybr-db-1 sh -c "mysql -uwordpress -p\$MYSQL_PASSWORD wordpress -e \
   \"UPDATE wp_options SET option_value=\\\"inkbytes\\\" WHERE option_name IN (\\\"template\\\",\\\"stylesheet\\\");\""'
```

## Revert to the stock theme

```bash
# set template + stylesheet back to twentytwentyfive
… WHERE option_name IN ("template","stylesheet") -> "twentytwentyfive"
```
