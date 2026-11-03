# Cloudflare Free capacity and full-length articles

Goal: keep complete articles and large syntheses while preventing an oversized
Cloudflare deployment. Article length is not a file count: one long HTML article
can remain one asset; images and search fragments consume additional assets.

The deployment census runs after rendering and search indexing. It includes its
own report exactly once. With `--enforce`, more than 17,000 files blocks upload;
more than 20,000 produces a separate provider-ceiling error. An individual file
above 25 MiB also blocks upload. The existing production approval remains required.
Default census mode remains nonblocking, so archive generation is independent.

The census conservatively counts every file on disk, including hidden files; it
does not interpret Wrangler ignore rules. Consequently it may stop an upload that
Wrangler could accept when ignored files are present. This is a safety margin,
not a claim of exact parity with Wrangler. The deployed tree must not add files
after the guard runs.

Acceptance: 17,000 files passes; 17,001 fails the safety budget; 20,001 fails the
provider ceiling; a 25 MiB file passes and a larger file fails. Repeated census
runs do not increase the reported count. No article truncation is introduced.

This guard does not provide unlimited free archive storage. The existing rolling
window and GitHub Pages fallback remain separate capacity mechanisms. On
2026-11-03, a complete traversal of the archive's gh-pages Git tree counted
41,905 files totalling 851,555,206 bytes. This measures repository-tree content,
not a guaranteed measurement of the final Pages artifact. GitHub documents a
1 GB maximum for a published Pages site. Growth rate and future article sizes
have not been measured, so no remaining-days forecast is justified.

Before expanding the archive, measure the published artifact and daily byte
growth. A separate archive site is a possible next design, but needs verified
routing, publication, correction and deletion handling; it is not implemented by
this guard. No extra repositories, paid products or new storage services are
created here.

Official limits:
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
