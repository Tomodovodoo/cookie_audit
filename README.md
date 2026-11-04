# Cookieonderzoek

Controle van cookies weigeren, zichtbaarheid, tracking en het onthouden van keuzes op 1.000 websites die in Nederland worden bezocht.

[Bekijk de resultaten](https://tomodovodoo.github.io/cookie_audit/) · [Methodologie](https://tomodovodoo.github.io/cookie_audit/methodology.html)

## Zelf uitvoeren

Vereist Python 3.11+, Google Chrome en een Nederlandse internetverbinding.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe audit.py --workers 4 --wait 7 --country NL
./.venv/Scripts/python.exe build.py
```

Een volgende run slaat afgeronde websites over. Gebruik `--force` om opnieuw te meten en `--domains bol.com,ad.nl` voor een selectie. `--country NL` registreert de locatie; het verandert je IP niet.

De meetregels staan in `rules.py`, de resultaten en screenshots in `docs/`. GitHub Pages publiceert `/docs` vanuit `main`.

## Bronnen

- Ranglijsten: [NetAPI](https://netapi.com/top-websites/nl/), CC BY 4.0.
- Domeinfilter: [StevenBlack](https://github.com/StevenBlack/hosts/tree/master/alternates/porn-only), met de licenties van de gebruikte bronnen.
- Trackerlijst: [Disconnect](https://github.com/disconnectme/disconnect-tracking-protection), CC BY-NC-SA 4.0.

De code valt onder de [MIT-licentie](LICENSE). De datasets behouden hun eigen licenties.
