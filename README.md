# ChatMessageParser

A chat message parser that analyzes text messages and extracts structured information.  

### ▶️ How to Run  
1. Install Python 3.7+
2. Open command prompt and run the following:  
```
cd/  
mkdir temp  
cd temp  
git clone https://github.com/MitchScopes/ChatMessageParser.git  
cd ChatMessageParser  
python gui_parser.py
```

### Features:  
**Parsing:**
- *@mentions* - Username references starting with '@' [Examples: @user_123, @user]
- *#hashtags* - Extracts #hashtags similar to @mentions [Examples: #awesome, #python]
- *(Emoticons)* - Text-based emoji expressions [Examples: (smile), (happy123), (tableflip)]
- *Word Count* - Count of regular words [Examples: hi, hello, there]
- *URLs* - Any string starting with http:// or https:// [Examples: ht<span>tps://github.com, ht<span>tp://example.com]
  - Fetch multiple URL titles with async
  - Timing information for fetching
  - LRU caching for quick fetches for repeated URLs

**Data Management (SQLite, LRU Cache):**
- Saves most used words in mentions, hashtags, emoticons, etc to database
- Each run saves links to LRU cache and database; only using cache for retrieval for speed (database is loaded into cache on startup)
- User configuration settings are saved to database

**Graphical User Interface:**
- Type in your own messages then click parse (or press enter)
- View most frequent mentions, hashtags, emoticons across multiple messages (ability to clear stats from database)
- Interact with configurations (customizing emoticon length, title length, etc) (ability to set back to defualt settings)

**Unit Testing** - Run ```python test_parser.py```

 ### Future Features: 
 - Add more configuration settings
 - Update GUI design and visuals
 - Prompt user before clearing database and reset config
