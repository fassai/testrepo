# MYDA Studio — Landing Page

Static HTML/CSS/JS landing site. No build step. Deploy by copying the
`/myda` folder to any static host (BTS Post Future, Netlify, Cloudflare
Pages, etc.) and pointing the domain at it.

## Pages

- `index.html` — Home (hero stats, portfolio with priority + roster tiers, mid-portfolio CTA intercept)
- `profile.html` — Profile / About (founder, credentials, philosophy)
- `partners.html` — Partners (logo grid, tiered)
- `contact.html` — Inquire (form + direct contact)

Hamburger menu in the header on every page opens a full-screen drawer
with links to all pages.

## Design

- Black & white only (no accent color)
- Headlines: **Archivo Black** — bold and commanding, but not Impact
- Body: **Inter**
- Warm, family-first tone in the writing

## Placeholders

Where photos and videos aren't ready yet, gray rectangle placeholders
are used in three aspect ratios:

- `ph--1x1` — Square
- `ph--9x16` — Portrait (TikTok / Reels)
- `ph--16x9` — Landscape (YouTube / banner)

Each placeholder includes a label specifying exactly what asset to
request from the client (สายเมฆ).

## Open items pending from client

- Names of 4–5 K-pop artists produced by the studio
- Organization name where the owner serves as judge / committee member
- Specific competition name in the USA
- Partner logo files (Grammy, Mono, AHI, others)
- Photo and video assets to replace placeholders
- Final domain decision (myda.com vs alternative)
- Owner bio / credential copy for the Profile page
- Contact details (phone, LINE, email, address)
- Form submission endpoint for `contact.html`

## Local preview

```sh
cd myda
python3 -m http.server 8000
# open http://localhost:8000
```
