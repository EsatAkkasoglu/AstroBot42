# database.py
import json
import os
import csv
import feedparser
def retrieve(filename: str) -> dict:
    """Retrieve data from a local JSON file."""
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # Return an empty dict if file doesn't exist

def update(data, filename: str):
    """Update data in a local JSON file."""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)
class CsvManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.fieldnames = ['server_id', 'server_name', 'channel_id', 'thread_id', 'user_name']
    async def read_channel_list(self):
        with open(self.file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            # Ensure all columns are considered
            return [{key: row[key] for key in self.fieldnames if key in row} for row in reader]
    
    async def update_channel_info(self, server_id, server_name, channel_id, thread_id=None, user_name=None):
        channels = await self.read_channel_list()
        updated = False
        for channel in channels:
            if channel['server_id'] == str(server_id):
                channel['server_name'] = str(server_name)
                channel['channel_id'] = str(channel_id)
                if thread_id is not None:
                    channel['thread_id'] = str(thread_id)
                if user_name is not None:
                    channel['user_name'] = str(user_name)
                updated = True
                break
        
        if not updated:
            channels.append({
                'server_id': str(server_id),
                'server_name': str(server_name),
                'channel_id': str(channel_id),
                'thread_id': str(thread_id) if thread_id is not None else '',
                'user_name': str(user_name) if user_name is not None else ''
            })
        
        
        with open(self.file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(channels)
    
    async def remove_channel(self, channel_id):
        channels = await self.read_channel_list()
        channels = [channel for channel in channels if channel['channel_id'] != str(channel_id)]

        with open(self.file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(channels)
    
    async def get_thread_id(self, server_id):
        channels = await self.read_channel_list()
        for channel in channels:
            if channel['server_id'] == str(server_id):
                return channel.get('thread_id')
        return None
    
# Path to the CSV file where news links will be saved
news_csv_file = 'database/csv/news_links.csv'

# Load seen news items from the file if it exists, otherwise create an empty set
seen_news = set()
if os.path.exists(news_csv_file):
    with open(news_csv_file, 'r', newline='') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            seen_news.add(row['link'])

# RSS feed URLs of popular space news channels
rss_urls = {
    'NASA Breaking News': 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
    'Space.com News': 'https://www.space.com/feeds/all',
    'Sky & Telescope - News': 'https://skyandtelescope.org/astronomy-news/feed/',
    'ESA Top News': 'https://www.esa.int/rssfeed/TopNews',
    'ESA Space Science News': 'https://www.esa.int/rssfeed/Our_Activities/Space_Science',
    'ESA Human Spaceflight and Exploration News': 'https://www.esa.int/rssfeed/HSF',
    'New Scientist - Space': 'https://www.newscientist.com/subject/space/feed/',
    'Science Daily - Space & Time': 'https://www.sciencedaily.com/rss/space_time.xml',
}

def fetch_news(rss_url):
    # Fetch and parse the RSS feed
    feed = feedparser.parse(rss_url)
    news_items = []
    
    for entry in feed.entries:
        # Extract the necessary information from each news item
        title = entry.title if 'title' in entry else 'No Title'
        link = entry.link if 'link' in entry else 'No Link'
        published = entry.published if 'published' in entry else 'No Publication Date'
        
        # Append the news item to the list
        news_items.append({
            'title': title,
            'link': link,
            'published': published
        })
    
    return news_items

