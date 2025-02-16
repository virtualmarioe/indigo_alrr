import os
import re
import feedparser
import requests
from datetime import datetime
import time
import logging
from dotenv import load_dotenv
from time import sleep
from random import uniform

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BlogTranslator:
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.gemini_endpoint = os.getenv('GEMINI_ENDPOINT', 'https://api.gemini.com/v2/flash/completions')
        self.output_dir = os.path.join("..", "_posts")
        # Update images directory to use the root assets folder
        self.images_dir = os.path.join("..", "assets", "images", "blog")
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        self.retry_count = 3
        self.base_delay = 2  # Base delay in seconds
        self.max_delay = 10  # Maximum delay in seconds

    def backoff_retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic"""
        for attempt in range(self.retry_count):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_count - 1:  # Last attempt
                    raise
                
                # Calculate delay with jitter
                delay = min(self.base_delay * (2 ** attempt) + uniform(0, 1), self.max_delay)
                logging.warning(f"API request failed. Retrying in {delay:.2f} seconds...")
                sleep(delay)

    def gemini_completion(self, prompt, model="gemini-pro", temperature=0.3):
        """Send request to Gemini API with rate limiting and error handling"""
        headers = {
            "Content-Type": "application/json"
        }
        
        params = {
            "key": self.gemini_api_key
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": temperature
            }
        }
        
        def make_request():
            response = requests.post(
                self.gemini_endpoint,
                headers=headers,
                params=params,
                json=payload
            )
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text']

        return self.backoff_retry(make_request)

    def translate_and_process_feed(self, feed_url):
        """Main function to process the blog feed"""
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                self.process_entry(entry)
                time.sleep(1)  # Rate limiting
        except Exception as e:
            logging.error(f"Feed processing failed: {e}")

    def process_entry(self, entry):
        """Process individual blog entries"""
        try:
            translated_content = self.translate_entry(entry)
            self.save_entry(translated_content)
        except Exception as e:
            logging.error(f"Entry processing failed for {entry.title}: {e}")

    def clean_html(self, text):
        """Clean HTML while preserving structure and formatting"""
        # Store complete structures
        placeholders = {
            'tables': [],
            'lists': [],
            'images': []
        }
        
        def store_element(match, element_type):
            placeholders[element_type].append(match.group(0))
            return f"__{element_type.upper()}_{len(placeholders[element_type])-1}__"

        # Store tables
        text = re.sub(r'<table.*?</table>', lambda m: store_element(m, 'tables'), text, flags=re.DOTALL)
        
        # Store lists with their items
        text = re.sub(r'(<ul.*?>.*?</ul>)', lambda m: store_element(m, 'lists'), text, flags=re.DOTALL)
        
        # Store images
        text = re.sub(r'<img.*?>', lambda m: store_element(m, 'images'), text)
        
        # Clean up any remaining HTML
        text = re.sub(r'<(?!li|/li|ul|/ul)[^>]+>', '', text)
        
        # Convert list items to markdown style
        text = text.replace('<li>', '* ')
        text = text.replace('</li>', '\n')
        text = text.replace('<ul>', '\n')
        text = text.replace('</ul>', '\n')
        
        # Clean up whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = text.strip()
        
        # Restore stored elements
        for element_type, elements in placeholders.items():
            for i, element in enumerate(elements):
                text = text.replace(f"__{element_type.upper()}_{i}__", element)
        
        return text

    def translate_large_text(self, text, chunk_size=800):
        """Split and translate text while preserving formatting"""
        try:
            # Clean and preserve HTML structure
            text = self.clean_html(text)
            
            # Split by double newlines while preserving lists
            sections = re.split(r'(\n\n(?!\*))', text)
            translated_sections = []
            
            for section in sections:
                if not section.strip():
                    translated_sections.append(section)
                    continue
                
                # Keep HTML structures intact
                if '<table' in section or '<img' in section:
                    translated_sections.append(section)
                    continue
                
                # Special handling for lists
                if section.strip().startswith('*'):
                    # Translate each list item separately
                    items = section.split('\n')
                    translated_items = []
                    for item in items:
                        if item.strip():
                            translated = self.gemini_completion(
                                f"Translate this Spanish text to English (preserve the * at the start if present): {item}"
                            )
                            translated_items.append(translated)
                            sleep(1)
                    translated_sections.append('\n'.join(translated_items))
                else:
                    # Regular translation
                    translated = self.gemini_completion(
                        f"Translate this Spanish text to English: {section}"
                    )
                    translated_sections.append(translated)
                    sleep(2)
            
            return '\n\n'.join(translated_sections)
            
        except Exception as e:
            logging.error(f"Translation of large text failed: {e}")
            raise

    def translate_entry(self, entry):
        """Translate a blog entry from Spanish to English"""
        try:
            # Get the date first so we can use it for image naming
            if 'published_parsed' in entry:
                published_dt = datetime(*entry.published_parsed[:6])
            else:
                published_dt = datetime.now()

            # Translate title
            translated_title = self.gemini_completion(
                f"Translate this Spanish title to English: {entry.title}"
            )

            # Extract and translate tags
            original_tags = []
            if hasattr(entry, 'tags'):
                original_tags = [tag.term for tag in entry.tags]
            
            translated_tags = []
            for tag in original_tags:
                translated_tag = self.gemini_completion(
                    f"Translate this Spanish tag to English: {tag}"
                )
                translated_tags.append(translated_tag)
            
            # If no tags found, add default ones
            if not translated_tags:
                translated_tags = ['Blog', 'Translation']

            # Translate content in chunks
            content = entry.content[0].value if 'content' in entry else entry.summary
            translated_content = self.translate_large_text(content)

            # Add translation notice
            translation_notice = f"""
> This is an English translation of the original Spanish blog post.  
> The original post can be found at: <a href="{entry.link}" target="_blank">{entry.link}</a>

---

"""
            final_content = translation_notice + translated_content

            # Rest of the method remains the same
            
            image_path = ""
            image_match = re.search(r'<img.*?src=["\'](.*?)["\']', content)
            if image_match:
                image_url = image_match.group(1)
                # Pass both title and publication date
                image_path = self.download_image(image_url, translated_title, published_dt)

            return {
                'title': translated_title,
                'content': final_content,
                'date': published_dt,
                'image': image_path,
                'original_link': entry.link if 'link' in entry else "",
                'tags': translated_tags
            }
        except Exception as e:
            logging.error(f"Translation failed for entry '{entry.title}': {e}")
            raise

    def download_image(self, image_url, post_title=None, post_date=None):
        """Download an image and return its local path"""
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                # Get original extension or default to jpg
                original_ext = os.path.splitext(image_url.split("?")[0])[1].lower() or '.jpg'
                
                # Create a clean name from post title
                if post_title:
                    # Get first 3-4 words of title
                    title_words = self.slugify(post_title).split('-')[:3]
                    clean_title = '-'.join(title_words)
                    
                    # Use post date for the date string
                    date_str = post_date.strftime('%Y%m') if post_date else datetime.now().strftime('%Y%m')
                    filename = f'{clean_title}-{date_str}{original_ext}'
                else:
                    # Fallback name using post date
                    date_str = post_date.strftime('%Y%m%d-%H%M') if post_date else datetime.now().strftime('%Y%m%d-%H%M')
                    filename = f'blog-image-{date_str}{original_ext}'
                
                filepath = os.path.join(self.images_dir, filename)
                
                # Ensure filename is unique by adding a counter if needed
                counter = 1
                while os.path.exists(filepath):
                    base, ext = os.path.splitext(filename)
                    filename = f"{base}-{counter}{ext}"
                    filepath = os.path.join(self.images_dir, filename)
                    counter += 1

                with open(filepath, "wb") as f:
                    f.write(response.content)
                logging.info(f"Downloaded image: {filename}")
                return f"/assets/images/blog/{filename}"
            else:
                logging.warning(f"Failed to download image {image_url}: HTTP {response.status_code}")
                return ""
        except Exception as e:
            logging.error(f"Failed to download image {image_url}: {e}")
            return ""

    def save_entry(self, entry_data):
        """Save the translated entry as a markdown file"""
        try:
            slug = self.slugify(entry_data['title'])
            filename = f"{entry_data['date'].strftime('%Y-%m-%d')}-{slug}.md"
            filepath = os.path.join(self.output_dir, filename)

            # Check if file exists and remove it
            if os.path.exists(filepath):
                logging.info(f"Replacing existing file: {filename}")
                os.remove(filepath)

            # Format tags for YAML
            tags_yaml = '\n'.join(f'  - {tag}' for tag in entry_data['tags'])
            
            # Only include image if it was successfully downloaded
            image_yaml = f'image: "{entry_data["image"]}"' if entry_data["image"] else ""
            headerImage_yaml = "headerImage: true" if entry_data["image"] else ""

            content = f"""---
title: "{entry_data['title']}"
layout: post
date: {entry_data['date'].strftime('%Y-%m-%d %H:%M')}
tag:
{tags_yaml}
{image_yaml}
{headerImage_yaml}
description: "Translated from Spanish blog post"
category: blog
author: adrianaruiz
externalLink: "{entry_data['original_link']}"
---

{entry_data['content']}
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logging.info(f"Created: {filepath}")
        except Exception as e:
            logging.error(f"Failed to save entry {entry_data['title']}: {e}")
            raise

    def slugify(self, title):
        """Convert title to URL-friendly slug"""
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
        return slug

def main():
    try:
        feed_url = os.getenv('BLOG_FEED_URL')
        if not feed_url:
            raise ValueError("BLOG_FEED_URL environment variable not set")

        translator = BlogTranslator()
        translator.translate_and_process_feed(feed_url)
    except Exception as e:
        logging.error(f"Translation process failed: {e}")

if __name__ == "__main__":
    main()
