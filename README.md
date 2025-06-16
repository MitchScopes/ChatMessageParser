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
python main.py
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
- Type in your own messages then click parse
- View most frequent mentions, emoticons, etc across multiple messages (ability to clear stats from database)
- Interact with configurations (customizing emoticon length, title length, etc) (ability to set back to defualt settings)

**Adding New Features:**
- Config.py file to add more prefixes (mentions, hashtags) or character_pairs (emoticons) (add to result template as well). The new parsed variable will automatically be added to database and show on GUI.
- Add new config settings that get dynamically added to GUI and can be easily updated in logic

**Unit Testing**
- Run ```python -m unittest discover -s tests```

### Future Features:
- Update GUI visuals
- Prompt user before clearing database and reset config