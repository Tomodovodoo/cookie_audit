# Cookie audit for the Netherlands

Local, resumable consent screening with a static GitHub Pages register. The report is at https://Tomodovodoo.github.io/cookie_audit/ when Pages deployment completes.

This is an observational tool, not an AP ruling or a GDPR compliance certificate. Read [the method](docs/methodology.html) before interpreting the green checks. The current source top 1,000 has 124 adult-filter exclusions, leaving 876 eligible domains. The audit reaches 1,000 targets by adding 124 separately labelled .nl domains from NetAPI's global ranking. These additions have global ranks only, not invented Netherlands ranks.

## Run on Windows

Python 3.11+ and installed Google Chrome are required. Tested on Python 3.14, Windows, with 32 GB RAM. The crawler uses offscreen Chrome and isolated contexts, not your personal profile.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe prepare.py
./.venv/Scripts/python.exe supplement.py
./.venv/Scripts/python.exe audit.py --workers 4 --wait 7 --country NL
./.venv/Scripts/python.exe build.py
```

`--country` records the measured network location; it does not change your IP. Verify your egress country first. Browser language and timezone do not move your connection. `prepare.py` refreshes the ranking and filter inputs; omit it to reproduce the checked-in input snapshot. Downloaded source hashes are in `data/sources.json`.

Resume with the same audit command; completed rows are skipped. `--force` repeats selected sites. For the six requested calibration examples:

```powershell
./.venv/Scripts/python.exe audit.py --domains bol.com,abnamro.nl,rabobank.nl,nrc.nl,ad.nl,marktplaats.nl --workers 3 --wait 7 --country NL --force
```

The CLI supports 1–16 workers, an alternate `--chrome` executable, `--headless`, and `--limit`. Start with 4 workers; increasing concurrency can cause memory pressure, timeouts and site blocks. Each site takes several observation windows plus network loading and screenshots. A cohort of this size is a sustained crawl, not an instantaneous check. No API model or paid service is required.

Chrome is launched through Playwright with `--enable-automation` removed and `--disable-blink-features=AutomationControlled`. It remains detectable. This approach was used after separately launched Chrome exited before exposing its debugging port in this environment. Do not treat the flags as a promise to bypass bot protection.

## Data and rules

- `prepare.py`: country ranking, adult filtering and tracker input snapshots.
- `supplement.py`: separately labelled globally ranked .nl additions to reach 1,000 targets.
- `audit.py` and `inspect.js`: isolated browser journeys and redacted evidence capture.
- `rules.py`: explicit matching and scoring rules. No site-specific pass/fail overrides.
- `rescore.py`: reapply corrected rules to existing captures.
- `compact.py`: shorten repeated context excerpts and archive superseded captures outside the public tree.
- `build.py`: public JSON/CSV, sorting metadata, evidence hashes and documented company groupings.
- `docs/`: buildless HTML/CSS/JS plus evidence and results, published using GitHub Pages.

Green means the observed check passed within its measurement limits. Red means a configured technical failure was observed. Grey means inconclusive or not tested. Requests to known tracker endpoints alone are grey because libraries and consent-mode pings are not proof of unlawful tracking. Known advertising cookie identifiers are red. Analytics identifiers remain grey pending configuration review.

Before, after-refusal, reload and isolated acceptance captures are separate files. Cookie values, storage values, query strings and request bodies are not published. Screenshots show fresh anonymous visits. Block pages are retained as redacted JSON without a screenshot because they can expose the machine's IP. Inspect evidence before publication. The report currently tests one desktop viewport and does not measure all tracking techniques, navigation-triggered trackers, server-side activity or full legal scope per company.

## Source attribution

- Netherlands ranking: [NetAPI](https://netapi.com/top-websites/nl/), CC BY 4.0. CrUX groups plus NetAPI signals, not exact measured visit counts.
- Adult filter: [StevenBlack hosts](https://github.com/StevenBlack/hosts/tree/master/alternates/porn-only), MIT repository with constituent source licences. Only the derived domain set is retained.
- Tracker classifications: [Disconnect](https://github.com/disconnectme/disconnect-tracking-protection), CC BY-NC-SA 4.0, as stated in `data/trackers.json`. This dataset is not covered by the software's MIT licence. Respect its noncommercial/share-alike terms.
- Company groupings: [DPG brand list](https://www.dpgmediagroup.com/en-NL/permission-brands) and [Mediahuis brands](https://www.mediahuis.com/nl/merken). Unverified ownership remains explicit.
- Legal scope: [AP banner rules](https://autoriteitpersoonsgegevens.nl/themas/internet-slimme-apparaten/cookies/heldere-en-misleidende-cookiebanners), [ACM exemptions](https://www.acm.nl/nl/verkoop-aan-consumenten/reclame-en-verleiden/online-beinvloeden/cookies-plaatsen), and [GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng).

## Publish

Run `build.py`, review the results, commit source and `docs/`, then configure GitHub Pages to serve `/docs` from the reviewed branch. No build framework, server or client-side tracking is needed. Screenshots remain subject to their original owners' rights. Open issues for reproducible false positives and include the capture timestamp.

## Research references

The user supplied these references during implementation. They inform the follow-up work; their published accuracy numbers do not apply to this crawler.

- [CookieAudit](https://github.com/SzymonNastaly/CookieAudit): a browser extension with a notice picker, learned control/purpose classification, cookie classification and subpage exploration. Its manual notice selection is not a direct unattended 1,000-site solution. No extension code or model weights were copied here.
- [CookieEnforcer](https://research.google/pubs/cookieenforcer-automated-cookie-notice-analysis-and-enforcement/): models the sequence of UI actions needed to disable optional cookies. Its reported 93.7% concerns its own evaluation of action generation, not tracking-law adjudication or this implementation.
- [ConsentCrawl](https://github.com/dumkydewilde/consentcrawl): demonstrates batch Playwright collection, CMP detection and before/after-acceptance comparison. We retain a separate refusal journey; acceptance-only comparison does not establish equal refusal ease.

`consent-state.js` additionally records available IAB TCF and Cookiebot consent receipts without consent strings or user IDs. A stable post-refusal receipt still granting advertising or special-feature consent can flag an unsuccessful refusal. Absence of a supported receipt is not proof of success. Earlier captures without this field have not undergone that additional check. Subpage exploration and a trained multilingual classifier remain limitations of this first release, not implemented capabilities.
