import unittest
from unittest.mock import patch
import json
from logic_parser import Parser

class TestParser(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.parser = Parser()

    # Unicode in json output
    @patch.object(Parser, 'extract_website_title', autospec=True)
    async def test_unicode(self, mock_extract):
        unicode_title = "Chat · Message · Parser"
        mock_extract.return_value = (unicode_title, 0.175)
        message = "See this https://github.com/"
        result = await self.parser.parse(message)
        # Check that the Unicode middle dot appears
        self.assertIn("·", result)
        self.assertNotIn("\\u00b7", result)
        self.assertIn("Chat", result)
        self.assertIn("Message", result)
        self.assertIn("Parser", result)
        data = json.loads(result)
        links = data.get("links", [])
        self.assertTrue(any(link["title"] == unicode_title for link in links))

    # Duplicate URLs processed and returned using the same cached fetch_time
    async def test_url_fetch_time_cached(self):
        url = "https://example.com"
        first_result = await self.parser.parse(url)
        first_links = json.loads(first_result).get("links", [])
        self.assertTrue(first_links)
        first_time = first_links[0]["fetch_time"]
        second_result = await self.parser.parse(f"{url} {url}")
        second_links = json.loads(second_result).get("links", [])
        self.assertEqual(len(second_links), 2)
        self.assertEqual(second_links[0]["fetch_time"], first_time)
        self.assertEqual(second_links[1]["fetch_time"], first_time)

    async def test_mentions(self):
        message = "@alice @bob hey, check this out!"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("mentions"), ["alice", "bob"])
        self.assertEqual(result_dict.get("words"), 4)

    async def test_emoticons(self):
        message = "Good morning! (coffee) (yawn)"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("emoticons"), ["coffee", "yawn"])
        self.assertEqual(result_dict.get("words"), 2)

    async def test_links_and_emoticons(self):
        message = "Olympics starting soon! https://olympics.com/en/ (excited)"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("emoticons"), ["excited"])
        self.assertEqual(result_dict.get("words"), 3)
        links = result_dict.get("links", [])
        self.assertTrue(any(link["url"] == "https://olympics.com/en/" for link in links))
        for link in links:
            if link["url"] == "https://olympics.com/en/":
                self.assertIsInstance(link.get("title"), str)
                self.assertTrue(len(link["title"]) > 0)

    async def test_mentions_emoticons_links(self):
        message = "@sarah @mike_123 (success) great work on https://github.com/"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("mentions"), ["sarah", "mike_123"])
        self.assertListEqual(result_dict.get("emoticons"), ["success"])
        self.assertEqual(result_dict.get("words"), 3)
        links = result_dict.get("links", [])
        self.assertTrue(any(link["url"] == "https://github.com/" for link in links))
        for link in links:
            if link["url"] == "https://github.com/":
                self.assertIsInstance(link.get("title"), str)
                self.assertTrue(len(link["title"]) > 0)
    
    async def test_multiple_spaces_between_words(self):
        message = "hello    world   this  is   spaced"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertEqual(result_dict.get("words"), 5)

    async def test_url_punctuation_trim(self):
        message = "check this site: https://example.com."
        result = await self.parser.parse(message)
        self.assertIn("https://example.com", result)
        self.assertNotIn("https://example.com.", result)

    async def test_invalid_emoticon_long(self):
        message = "(toomanycharactershere)"
        result = await self.parser.parse(message)
        self.assertNotIn("emoticons", result)

    async def test_invalid_emoticon_spaces(self):
        message = "(has spaces)"
        result = await self.parser.parse(message)
        self.assertNotIn("emoticons", result)

    async def test_mentions_with_numbers_and_underscores(self):
        message = "@user_123 @anotherUser99 hello"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("mentions"), ["user_123", "anotherUser99"])
        self.assertEqual(result_dict.get("words"), 1)

    async def test_empty_input_string(self):
        message = ""
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertEqual(result_dict, {})

    async def test_malformed_urls_or_unreachable_sites(self):
        message = "Check this bad url http://this_is_not_a_valid_url and unreachable https://unreachable.domain"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        links = result_dict.get("links", [])
        self.assertTrue(any(link["url"] == "http://this_is_not_a_valid_url" for link in links))
        self.assertTrue(any(link["url"] == "https://unreachable.domain" for link in links))
        for link in links:
            self.assertIn("title", link)
            self.assertIsInstance(link["title"], str)

    async def test_hashtag(self):
        message = "This is a #hashtag test #Python"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        self.assertListEqual(result_dict.get("hashtags"), ["hashtag", "Python"])
        self.assertEqual(result_dict.get("words"), 4)

    async def test_url_repeated_uses_cache(self):
        message = "https://example.com https://example.com"
        await self.parser.parse(message)
        cached = self.parser.url_cache.get("https://example.com")
        self.assertIsInstance(cached, tuple)

    async def test_url_fetch_time(self):
        message = "https://example.com"
        result = await self.parser.parse(message)
        result_dict = json.loads(result)
        links = result_dict.get("links", [])
        self.assertTrue(len(links) > 0)
        self.assertIn("fetch_time", links[0])
        self.assertIsInstance(links[0]["fetch_time"], float)
        self.assertGreaterEqual(links[0]["fetch_time"], 0.0)


if __name__ == '__main__':
    unittest.main()
