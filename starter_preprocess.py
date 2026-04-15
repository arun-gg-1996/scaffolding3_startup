"""
starter_preprocess.py
Starter code for text preprocessing - focus on the statistics, not the regex!

This is the same code you'll use in the main Shannon assignment next week.
"""

import re
import json
import requests
from typing import List, Dict, Tuple
from collections import Counter
import string

class TextPreprocessor:
    """Handles all the annoying text cleaning so you can focus on the fun stuff"""
    
    def __init__(self):
        # Gutenberg markers (these are common, add more if needed)
        self.gutenberg_markers = [
            "*** START OF THIS PROJECT GUTENBERG",
            "*** END OF THIS PROJECT GUTENBERG",
            "*** START OF THE PROJECT GUTENBERG",
            "*** END OF THE PROJECT GUTENBERG",
            "*END*THE SMALL PRINT",
            "<<THIS ELECTRONIC VERSION"
        ]
    
    def clean_gutenberg_text(self, raw_text: str) -> str:
        """Remove Project Gutenberg headers/footers"""
        lines = raw_text.split('\n')
        
        # Find start and end markers
        start_idx = 0
        end_idx = len(lines)
        
        for i, line in enumerate(lines):
            if any(marker in line for marker in self.gutenberg_markers[:4]):
                if "START" in line:
                    start_idx = i + 1
                elif "END" in line:
                    end_idx = i
                    break
        
        # Join the cleaned lines
        cleaned = '\n'.join(lines[start_idx:end_idx])
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        return cleaned.strip()
    
    def normalize_text(self, text: str, preserve_sentences: bool = True) -> str:
        """
        Normalize text while preserving sentence boundaries
        
        Args:
            text: Input text
            preserve_sentences: If True, keeps . ! ? for sentence detection
        """
        # Convert to lowercase
        text = text.lower()
        
        # Standardize curly quotes and dashes using Unicode code points
        # to avoid encoding issues with smart quote characters in regex patterns
        text = re.sub('[\u201c\u201d]', '"', text)   # left/right double curly quotes -> "
        text = re.sub("[\u2018\u2019]", "'", text)   # left/right single curly quotes -> '
        text = re.sub('[\u2014\u2013]', '-', text)   # em dash / en dash -> -

        if preserve_sentences:
            # Keep sentence endings but remove other punctuation
            # This regex keeps . ! ? but removes , ; : etc
            text = re.sub(r"[^\w\s.!?'\-]", ' ', text)
        else:
            # Remove all punctuation except apostrophes in contractions
            text = re.sub(r"(?<!\w)'(?!\w)|[^\w\s]", ' ', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter (you can make this fancier with NLTK)
        sentences = re.split(r'[.!?]+', text)
        
        # Clean up and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def tokenize_words(self, text: str) -> List[str]:
        """Split text into words"""
        # Remove sentence endings for word tokenization
        text_for_words = re.sub(r'[.!?]', '', text)
        
        # Split on whitespace and filter empty strings
        words = text_for_words.split()
        words = [w for w in words if w]
        
        return words
    
    def tokenize_chars(self, text: str, include_space: bool = True) -> List[str]:
        """Split text into characters"""
        if include_space:
            # Replace multiple spaces with single space
            text = re.sub(r'\s+', ' ', text)
            return list(text)
        else:
            return [c for c in text if c != ' ']
    
    def get_sentence_lengths(self, sentences: List[str]) -> List[int]:
        """Get word count for each sentence"""
        return [len(self.tokenize_words(sent)) for sent in sentences]
    
    # TODO: Implement these methods for the warm-up assignment
    
    def fetch_from_url(self, url: str) -> str:
        """
        Fetch raw text content from a URL.
        Only accepts .txt URLs (e.g. Project Gutenberg plain text files).

        Args:
            url: URL to a .txt file

        Returns:
            Raw text content as a string

        Raises:
            ValueError: If the URL does not point to a .txt file
            Exception: If the request fails or returns a non-200 status
        """
        # Only allow .txt URLs to avoid fetching HTML or binary files
        if not url.endswith('.txt'):
            raise ValueError("URL must point to a .txt file")

        # Project Gutenberg blocks requests that look like bots.
        # Adding a User-Agent header makes the request look like it's coming from a browser.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Increased timeout to 60s — some Gutenberg files are large and slow to download
        response = requests.get(url, headers=headers, timeout=60)

        # Raise an error if the server returned a bad status code
        if response.status_code != 200:
            raise Exception(f"Failed to fetch URL. Status code: {response.status_code}")

        return response.text
    
    def get_text_statistics(self, text: str) -> Dict:
        """
        Calculate basic statistics about the given text.

        Returns a dictionary with:
            - total_characters: number of characters in the text
            - total_words: number of words
            - total_sentences: number of sentences
            - avg_word_length: average number of characters per word
            - avg_sentence_length: average number of words per sentence
            - most_common_words: top 10 most frequent words
        """
        # Use existing tokenizer methods to break text into words and sentences
        words = self.tokenize_words(text)
        sentences = self.tokenize_sentences(text)

        # Avoid division by zero if text is empty
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        avg_sentence_length = len(words) / len(sentences) if sentences else 0

        # Count word frequencies and return the top 10
        word_counts = Counter(words)
        most_common = word_counts.most_common(10)

        return {
            "total_characters": len(text),
            "total_words": len(words),
            "total_sentences": len(sentences),
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "most_common_words": most_common
        }
    
    def skip_front_matter(self, text: str) -> str:
        """
        Skip past the table of contents and front matter to find
        where the actual story prose begins.

        Strategy: split the text into paragraphs (blank-line separated blocks)
        and return from the first paragraph that looks like real prose.

        A paragraph is considered real prose if:
        - It is long enough to be a sentence (at least 80 characters)
        - It does not contain 3 or more chapter/letter references (i.e. not a TOC)
        - It is not a short all-caps heading

        If no prose paragraph is found, the original text is returned as-is.
        """
        # Split on one or more blank lines to get paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        for i, para in enumerate(paragraphs):
            stripped = para.strip()

            # Skip very short blocks — these are headings or single labels
            if len(stripped) < 80:
                continue

            # Skip TOC paragraphs — they repeat "chapter" or "letter" many times
            lower = stripped.lower()
            if lower.count('chapter') >= 3 or lower.count('letter') >= 3:
                continue

            # Skip blocks that are entirely uppercase (e.g. "ETYMOLOGY. (Supplied by...)")
            # by checking if most words are uppercase
            words = stripped.split()
            upper_words = sum(1 for w in words if w.isupper() and len(w) > 1)
            if len(words) > 0 and upper_words / len(words) > 0.5:
                continue

            # This paragraph looks like real prose — return from here
            return '\n\n'.join(paragraphs[i:]).strip()

        # Nothing matched — return the full text unchanged
        return text

    def create_summary(self, text: str, num_sentences: int = 3) -> str:
        """
        Create a simple extractive summary by returning the first N sentences.
        This is not AI-based — it just takes the opening sentences of the text.

        Args:
            text: Cleaned/normalized text
            num_sentences: How many sentences to include in the summary (default 3)

        Returns:
            A string containing the first N sentences joined together
        """
        sentences = self.tokenize_sentences(text)

        # Filter out junk sentences using two checks:
        # 1. Must have at least 6 words (removes short headings and captions)
        # 2. Must not be a TOC dump — those are long strings like "Chapter 1 Chapter 2 Chapter 3..."
        #    We detect them by counting how many times "chapter" or "letter" appears in one sentence
        def is_meaningful(sentence):
            words = sentence.split()
            if len(words) < 6:
                return False
            lower = sentence.lower()
            # If "chapter" or "letter" appears 3+ times, it's probably a TOC line
            if lower.count('chapter') >= 3 or lower.count('letter') >= 3:
                return False
            return True

        meaningful = [s for s in sentences if is_meaningful(s)]

        # Take the first N meaningful sentences (or fewer if not enough)
        selected = meaningful[:num_sentences]

        # Join them back into a readable paragraph
        return '. '.join(selected) + '.'


class FrequencyAnalyzer:
    """Calculate n-gram frequencies from tokenized text"""
    
    def calculate_ngrams(self, tokens: List[str], n: int) -> Dict[Tuple[str, ...], int]:
        """
        Calculate n-gram frequencies
        
        Args:
            tokens: List of tokens (words or characters)
            n: Size of n-gram (1=unigram, 2=bigram, 3=trigram)
        
        Returns:
            Dictionary mapping n-grams to their counts
        """
        if n == 1:
            # Special case for unigrams (return as single strings, not tuples)
            return dict(Counter(tokens))
        
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i + n])
            ngrams.append(ngram)
        
        return dict(Counter(ngrams))
    
    def calculate_probabilities(self, ngram_counts: Dict, smoothing: float = 0.0) -> Dict:
        """
        Convert counts to probabilities
        
        Args:
            ngram_counts: Dictionary of n-gram counts
            smoothing: Laplace smoothing parameter (0 = no smoothing)
        """
        total = sum(ngram_counts.values()) + smoothing * len(ngram_counts)
        
        probabilities = {}
        for ngram, count in ngram_counts.items():
            probabilities[ngram] = (count + smoothing) / total
        
        return probabilities
    
    def save_frequencies(self, frequencies: Dict, filename: str):
        """Save frequency dictionary to JSON file"""
        # Convert tuples to strings for JSON serialization
        json_friendly = {}
        for key, value in frequencies.items():
            if isinstance(key, tuple):
                json_friendly['||'.join(key)] = value
            else:
                json_friendly[key] = value
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_friendly, f, indent=2, ensure_ascii=False)
    
    def load_frequencies(self, filename: str) -> Dict:
        """Load frequency dictionary from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert string keys back to tuples where needed
        frequencies = {}
        for key, value in json_data.items():
            if '||' in key:
                frequencies[tuple(key.split('||'))] = value
            else:
                frequencies[key] = value
        
        return frequencies


# Example usage to test your setup
if __name__ == "__main__":
    # Test with a small example
    sample_text = """
    This is a test. This is only a test! 
    If this were a real emergency, you would be informed.
    """
    
    preprocessor = TextPreprocessor()
    analyzer = FrequencyAnalyzer()
    
    # Clean and normalize
    clean_text = preprocessor.normalize_text(sample_text)
    print(f"Cleaned text: {clean_text}\n")
    
    # Get sentences
    sentences = preprocessor.tokenize_sentences(clean_text)
    print(f"Sentences: {sentences}\n")
    
    # Get words
    words = preprocessor.tokenize_words(clean_text)
    print(f"Words: {words}\n")
    
    # Calculate bigrams
    bigrams = analyzer.calculate_ngrams(words, 2)
    print(f"Word bigrams: {bigrams}\n")
    
    # Calculate character trigrams
    chars = preprocessor.tokenize_chars(clean_text)
    char_trigrams = analyzer.calculate_ngrams(chars, 3)
    print(f"Character trigrams (first 5): {dict(list(char_trigrams.items())[:5])}")
    
    print("\n✅ Basic functionality working!")
    print("Now implement the TODO methods for your assignment!")