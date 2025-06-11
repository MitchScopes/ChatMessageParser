import json
import re
import urllib.request


def extract_prefix(word, prefixes):
    if (word[0] in prefixes 
        and re.fullmatch(r"[A-Za-z0-9_]+", word[1:])):  # Contains letters, numbers, underscores

        key = prefixes[word[0]]
        value = word[1:]

        return key, value
    return None


def extract_character_pairs(word, character_pairs):
    if (word[0] in character_pairs and word[-1] == (character_pairs[word[0]]['close'])
        and len(word[1:-1]) <= 15                       # Max charater length of 15 not counting ()
        and re.fullmatch(r"[A-Za-z0-9]+", word[1:-1])): # Contains letters and numbers

        key = character_pairs[word[0]]['category']
        value = word[1:-1]

        return key, value
    return None


def extract_website_title(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            if (match := re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)):
                title = match.group(1).strip()
                if len(title) > 200:
                    return "No title found"
                return title
    except Exception:
        return "No title found"


def parse_message(message):
    #'category': 'data type'
    result = {
        "mentions": [],
        "hashtags": [],
        "emoticons": [],
        "links": [],
        "words": 0
    }
    #'remove': 'category'
    prefixes = {
        '@': 'mentions',
        '#': 'hashtags'
    }
    #'remove': {x: 'remove', x: 'category'}
    character_pairs = {
        '(': {
            'close': ')',
            'category': 'emoticons'
        }
    }

    words = message.split()

    for word in words:

        # Prefixes (mentions) - allows letters, numbers, underscores 
        if (extracted_prefix := extract_prefix(word, prefixes)):
            key, value = extracted_prefix
            result[key].append(value)

        # Character Pairs (emoticons) - allows only letters and numbers 
        elif (extracted_character_pairs := extract_character_pairs(word, character_pairs)):
            key, value = extracted_character_pairs
            result[key].append(value)

        # Links - Start with https(s):// or www
        elif re.match(r'https?://\S+|www\.\S+', word):
            url = word.rstrip('.,!?;:')
            title = extract_website_title(url)
            result["links"].append({
                "url": url,
                "title": title
            })

        # Word Count - Any letter(s) or number(s)
        elif re.search(r"[A-Za-z0-9]+", word):
            result["words"] += 1         

    # Removes empty
    return json.dumps({k: v for k, v in result.items() if v}, indent = 2, ensure_ascii=False)


if __name__ == "__main__":
    # @user_1 @user2_ Hey! Check this out: https://github.com! (happy) #AWESOME 
    while True:
        message = input("Enter message to parse: ")
        json_output = parse_message(message)
        print(json_output)