# key: 'Variable name in logic', label: 'Name on GUI', type: 'data type', defualt: 'value'
DEFAULT_CONFIG = [
    {"key": "max_pair_length", "label": "Max Character Pair Length (emoticons, etc)", "type": int, "default": 15},
    {"key": "max_title_length", "label": "Max Title Length (for links)", "type": int, "default": 200},
    {"key": "MAX_CACHE_SIZE", "label": "Max LRU Cache Size", "type": int, "default": 100}
]

#'category': 'data type'
RESULT_TEMPLATE = {
    "mentions": [],
    "hashtags": [],
    "emoticons": [],
    "links": [],
    "words": 0
}

#'remove': 'category'
PREFIXES = {
    '@': 'mentions',
    '#': 'hashtags',
}

#'remove': {x: 'remove', x: 'category'}
CHARACTER_PAIRS = {
    '(': {
        'close': ')',
        'category': 'emoticons'
    }
}