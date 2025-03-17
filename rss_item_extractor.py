import asyncio
from crawl4ai import AsyncWebCrawler
from pymongo import MongoClient
from datetime import datetime
import logging
from typing import List, Dict
import math
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class RSSItemContentExtractor:
    def __init__(self, num_workers: int = 5):
        # MongoDB connection
        self.client = MongoClient('mongodb+srv://jainambhavsar95:Gr8estSecr8Is%3F@stocks.3zfgscg.mongodb.net/?retryWrites=true&w=majority&appName=stocks')
        self.db = self.client['news_articles']
        self.rss_items_collection = self.db['rss_items']
        self.num_workers = num_workers
        self.progress_bar = None

    def get_items_without_content(self) -> List[Dict]:
        """Get all items that don't have content field"""
        return list(self.rss_items_collection.find(
            {"content": {"$exists": False}},
            {"_id": 1, "url": 1}
        ))[:1000]

    async def process_item(self, item: Dict, crawler: AsyncWebCrawler) -> None:
        """Process a single item to extract its content"""
        try:
            # Extract content using crawl4ai
            result = await crawler.arun(url=item['url'])
            
            if result and result.markdown:
                # Update the document with the extracted content
                self.rss_items_collection.update_one(
                    {"_id": item["_id"]},
                    {
                        "$set": {
                            "content": result.markdown,
                            "content_extracted_at": datetime.utcnow()
                        }
                    }
                )
            else:
                logging.warning(f"No content extracted for URL: {item['url']}")
                
        except Exception as e:
            logging.error(f"Error processing URL {item['url']}: {str(e)}")
        finally:
            self.progress_bar.update(1)

    async def process_batch(self, items: List[Dict]) -> None:
        """Process a batch of items using a single crawler instance"""
        async with AsyncWebCrawler() as crawler:
            for item in items:
                await self.process_item(item, crawler)

    async def process_all_items(self) -> None:
        """Process all items without content in parallel"""
        # Get all items that need processing
        items = self.get_items_without_content()[:1000]
        total_items = len(items)
        
        if total_items == 0:
            logging.info("No items found that need content extraction")
            return

        logging.info(f"Found {total_items} items that need content extraction")
        
        # Create progress bar
        self.progress_bar = tqdm(total=total_items, desc="Extracting content")

        # Split items into batches for parallel processing
        batch_size = math.ceil(total_items / self.num_workers)
        batches = [items[i:i + batch_size] for i in range(0, total_items, batch_size)]

        # Create tasks for parallel processing
        tasks = [self.process_batch(batch) for batch in batches]
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        
        self.progress_bar.close()
        logging.info("Completed content extraction for all items")

async def main():
    extractor = RSSItemContentExtractor(num_workers=5)
    await extractor.process_all_items()

if __name__ == "__main__":
    asyncio.run(main()) 