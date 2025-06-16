import json
import re
import urllib.request
import asyncio
import time
import copy
from collections import OrderedDict

from src.db import ParserDB
from src.config import RESULT_TEMPLATE, PREFIXES, CHARACTER_PAIRS, DEFAULT_CONFIG

class Parser:
    def __init__(self):
        # Load settings from config
        self.load_config()

        self.prefixes = PREFIXES
        self.character_pairs = CHARACTER_PAIRS

        # Load database into cache
        self.url_cache = OrderedDict()
        self.loads_data_url_cache()

        # Safe Scan Regex
        self.prefix_pattern = re.compile(r'[A-Za-z0-9_]+')
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.title_pattern = re.compile(r'<title>(.*?)</title>', re.IGNORECASE | re.DOTALL)
        self.word_pattern = re.compile(r'[A-Za-z0-9]+')

        # Full Sweep Mode Regex
        prefix_chars = ''.join(re.escape(k) for k in self.prefixes.keys())
        pair_opens = ''.join(re.escape(k) for k in self.character_pairs.keys())
        pair_closes = ''.join(re.escape(v['close']) for v in self.character_pairs.values())

        token_pattern_str = (
            rf'[{prefix_chars}]{self.prefix_pattern.pattern}'
            rf'|[{pair_opens}]{self.word_pattern.pattern}[{pair_closes}]'
            rf'|{self.url_pattern.pattern}'
            rf'|{self.word_pattern.pattern}'
        )
        self.token_pattern = re.compile(token_pattern_str)


    def load_config(self):
        db = ParserDB()
        config = db.get_all_config()
        db.close()
        # Dynamically set settings based on DEFAULT_CONFIG
        for field in DEFAULT_CONFIG:
            key = field["key"]
            typ = field["type"]
            value = typ(config[key])
            setattr(self, key, value)


    def loads_data_url_cache(self):
        db = ParserDB()
        rows = db.conn.execute(
            "SELECT url, title, fetch_time, last_accessed FROM links ORDER BY last_accessed"
        ).fetchall()

        for url, title, fetch_time, last_accessed in rows:
            self.url_cache[url] = (title, fetch_time, last_accessed)
        db.close()


    def extract_prefix(self, word):
        if (word and word[0] in self.prefixes 
            and self.prefix_pattern.fullmatch(word[1:])):

            key = self.prefixes[word[0]]
            value = word[1:]

            return key, value
        return None


    def extract_character_pairs(self, word):
        if (word and word[0] in self.character_pairs and word[-1] == (self.character_pairs[word[0]]['close'])
            and len(word[1:-1]) <= self.max_pair_length
            and self.word_pattern.fullmatch(word[1:-1])):

            key = self.character_pairs[word[0]]['category']
            value = word[1:-1]

            return key, value
        return None

    # Runs asynchronously (async) while avoiding blocking library (urllib.request) by using run_in_executor (runs in seperate thread(s))
    async def extract_website_title(self, word):
        loop = asyncio.get_running_loop()
        
        def fetch():
            with urllib.request.urlopen(word, timeout=5) as response:
                return response.read().decode('utf-8', errors='ignore')
            
        title = "No title found"
        duration = 0.0

        try:
            start = time.perf_counter()
            html = await loop.run_in_executor(None, fetch)
            elapsed = round(time.perf_counter() - start, 3)

            if (match := self.title_pattern.search(html)):
                extracted_title = match.group(1).strip()
                if len(extracted_title) <= self.max_title_length:
                    title = extracted_title
                    duration = elapsed
        except Exception:
            pass

        return title, duration


    async def parse(self, message, mode):
        result = copy.deepcopy(RESULT_TEMPLATE)

        tasks = []

        if mode == "Full_Sweep":
            words = self.token_pattern.findall(message)
        else:
            words = message.split()

        for word in words:
            word = word.rstrip('.,!?;:')

            # Prefixes (mentions, hashtags, etc) - allows letters, numbers, underscores
            if (extracted_prefix := self.extract_prefix(word)):
                key, value = extracted_prefix
                result[key].append(value)

            # Character Pairs (emoticons, etc) - allows only letters and numbers
            elif (extracted_character_pairs := self.extract_character_pairs(word)):
                key, value = extracted_character_pairs
                result[key].append(value)

            # Links - Start with https(s):// or www.
            elif self.url_pattern.match(word):
                # Attempts retrieval from cache
                cached = self.url_cache.get(word)

                # Ensures LRU cache order by adding word to cache before async execution
                if cached is None:
                    now = int(time.time())
                    self.url_cache[word] = (None, None, now)  # Add to cache
                    self.url_cache.move_to_end(word)

                    if len(self.url_cache) > self.MAX_CACHE_SIZE:
                        self.url_cache.popitem(last=False) # LRU eviction

                    task = self.extract_website_title(word)
                    tasks.append((word, task))

                elif isinstance(cached, tuple):
                    self.url_cache.move_to_end(word)
                    title, duration, _ = cached
                    result["links"].append({
                        "url": word,
                        "title": title,
                        "fetch_time": duration
                    })

                else:
                    # Appends again to be displayed correct amount of times
                    tasks.append((word, cached))
                
            # Word Count - Any letter(s) or number(s)
            elif self.word_pattern.search(word):
                result["words"] += 1

        if tasks:
            # Runs tasks (extract_website_title) asynchronously per link
            titles = await asyncio.gather(*(task for _, task in tasks))
            for (url, _), (title, duration) in zip(tasks, titles):
                result["links"].append({
                    "url": url,
                    "title": title,
                    "fetch_time": duration
                })
                _, _, time_seen = self.url_cache[url]
                self.url_cache[url] = (title, duration, time_seen) # Adds data to cache

        try: # Add data from cache to database
            db = ParserDB()
            list_categories = [k for k, v in RESULT_TEMPLATE.items() if isinstance(v, list) and k != "links"]
            for category in list_categories:
                for value in result[category]:
                    if isinstance(value, (str, int)):
                        db.add(category, value)      

            for url, (title, fetch_time, time_seen) in self.url_cache.items():
                db.add_link(url, title, fetch_time, time_seen)
            
            # Update database with LRU cache
            cache_urls = set(self.url_cache.keys())
            db_urls = set(row[0] for row in db.conn.execute("SELECT url FROM links"))
            urls_to_remove = db_urls - cache_urls
            for url in urls_to_remove:
                db.conn.execute("DELETE FROM links WHERE url = ?", (url,))

            db.conn.commit()
        finally:
            db.conn.execute("VACUUM")
            db.close()

        return json.dumps(
            {k: v for k, v in result.items() if v}, # Removes empty items
            indent = 2,         # Json formatting
            ensure_ascii=False) # Unicode fix for website titles