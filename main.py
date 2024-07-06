import platform
import subprocess
import urllib.request
from datetime import datetime, timezone
from time import sleep
from urllib.parse import urlsplit

from utils import load_json, load_text, write_json, write_text


def craft_url(url: str) -> str:
    split_url = urlsplit(url)

    # url_query = f'?{split_url.query}' if split_url.query else ''
    url_query = ''
    url_block = (domain := split_url.netloc.split(':')[0]).removeprefix('www.')

    if len(url_path := f'{split_url.path}{url_query}') > 1:
        url_block += url_path
    
    return domain, url_block.rstrip('/')

def main():
    req = urllib.request.Request('https://openphish.com/feed.txt', method='GET')

    while True:
        with urllib.request.urlopen(req) as response:
            data: bytes = response.read()
            if response.status == 200:
                write_text(data.decode().strip(), 'feed.txt')
                break
        sleep(300)

    ddl_cmd = 'dead-domains-linter'
    if platform.system() == 'Windows':
        ddl_cmd += '.cmd'

    subprocess.run([ddl_cmd, '-i', 'feed.txt', '--export', 'dead_domains.txt'])

    filters_dict = load_json('filters.json')
    whitelist = []
    for whitelist_url in load_text('whitelist.txt', True):
        for url in filters_dict.keys():
            if whitelist_url not in url: continue
            whitelist.append(url)
    
    for url in whitelist:
        filters_dict.pop(url, None)

    dt = datetime.now(timezone.utc).isoformat(timespec='milliseconds')

    dead_domains = set(load_text('dead_domains.txt', True))
    for url in load_text('feed.txt', True):
        if craft_url(url)[0] in dead_domains:
            filters_dict.pop(url, None)
            continue
        
        filters_dict[url] = dt
    
    filters_set = set()
    def yield_filter():
        for url in filters_dict.keys():
            if (url_block := craft_url(url)[1]) in filters_set: continue

            filters_set.add(url_block)
            yield f'||{url_block}^$document,subdocument,popup'
    
    write_json(filters_dict, 'filters.json')
    write_text(yield_filter(), 'filters_init.txt')
    exit()

if __name__ == "__main__":
    main()