"""Conservative NSFW exclusions in addition to the downloaded domain blocklist."""
import re

EXPLICIT = set('onlyfans.com fansly.com hasmoves.com chaturbate.com stripchat.com xhamster.com xvideos.com xnxx.com pornhub.com chatgirl.nl opwindend.net easytoys.nl fabguys.com f2f.com simpcity.cr hai8g.com ay267.com luugy.com indoav.com darkero.com 405kk.com p4455.com mydesi2.net xv-ru.com gays-cruising.com binkdate.nl bullchat.com chatnu.com novamora.nl ondeugend-daten.nl regioswingers.nl stouteschatten.com janitorai.com secondlove.nl'.split())
PATTERN = re.compile(r'porn|xxx|hentai|sexvideo|xhamster|xnxx|xvideos|^sex[-a-z]|simpcity',re.I)

def excluded(domain, blocklist):
    return bool(PATTERN.search(domain) or any('.'.join(domain.split('.')[i:]) in blocklist or '.'.join(domain.split('.')[i:]) in EXPLICIT for i in range(len(domain.split('.')))))
