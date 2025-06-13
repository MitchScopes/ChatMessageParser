import json
import re
import urllib.request
import asyncio
import time

class Parser:
    def __init__(self):

        self.prefix_pattern = re.compile(r'[A-Za-z0-9_]+')
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.title_pattern = re.compile(r'<title>(.*?)</title>', re.IGNORECASE | re.DOTALL)
        self.word_pattern = re.compile(r'[A-Za-z0-9]+')

        self.url_cache = {}


    def extract_prefix(self, word):
        if (word and word[0] in self.prefixes 
            and self.prefix_pattern.fullmatch(word[1:])):

            key = self.prefixes[word[0]]
            value = word[1:]

            return key, value
        return None


    def extract_character_pairs(self, word):
        if (word and word[0] in self.character_pairs and word[-1] == (self.character_pairs[word[0]]['close'])
            and len(word[1:-1]) <= 15
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
                if len(extracted_title) <= 200:
                    title = extracted_title
                    duration = elapsed
        except Exception:
            pass

        return title, duration


    async def parse(self, user_input):
        #'category': 'data type'
        result = {
            "mentions": [],
            "hashtags": [],
            "emoticons": [],
            "links": [],
            "words": 0
        }
        #'remove': 'category'
        self.prefixes = {
            '@': 'mentions',
            '#': 'hashtags'
        }
        #'remove': {x: 'remove', x: 'category'}
        self.character_pairs = {
            '(': {
                'close': ')',
                'category': 'emoticons'
            }
        }

        tasks = []

        words = user_input.split()

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
                cached = self.url_cache.get(word)

                # Stores coroutines in cache temporarily (runtime cache)
                if cached is None:
                    coro = self.extract_website_title(word)
                    self.url_cache[word] = coro
                    tasks.append((word, coro))

                # Retrieves link data from cache (memory cache)
                elif isinstance(cached, tuple):
                    title, duration = cached
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

        # Runs tasks (extract_website_title) asynchronously per link
        titles = await asyncio.gather(*(task for _, task in tasks))

        for (url, _), (title, duration) in zip(tasks, titles):
            result["links"].append({
                "url": url,
                "title": title,
                "fetch_time": duration
            })
            self.url_cache[url] = (title, duration) # Adds to cache

        return json.dumps(
            {k: v for k, v in result.items() if v}, # Removes empty items
            indent = 2,         # Json formatting
            ensure_ascii=False) # Unicode fix for website titles


    async def main(self):
        while True:
            user_input = input("chat-parser> ").strip()
            json_output = await self.parse(user_input)
            print(json_output)


if __name__ == "__main__":
    parser = Parser()
    asyncio.run(parser.main())
