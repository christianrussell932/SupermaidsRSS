import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import DATABASE_URL, SCRAPE_INTERVAL_MINUTES
from app.models.models import Base, Source, Keyword, Match
from app.scraper.facebook_scraper import FacebookScraper
from app.scraper.nextdoor_scraper import NextdoorScraper

# Configure logger
logger = logging.getLogger(__name__)

class ScraperScheduler:
    """
    Scheduler for running Facebook and Nextdoor scrapers periodically
    """
    
    def __init__(self):
        """Initialize the scheduler and database connection"""
        self.scheduler = BackgroundScheduler()
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize scrapers
        self.facebook_scraper = None
        self.nextdoor_scraper = None
    
    def start(self):
        """Start the scheduler"""
        # Add jobs to the scheduler
        self.scheduler.add_job(
            self.run_facebook_scraper,
            IntervalTrigger(minutes=SCRAPE_INTERVAL_MINUTES),
            id='facebook_scraper',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.run_nextdoor_scraper,
            IntervalTrigger(minutes=SCRAPE_INTERVAL_MINUTES),
            id='nextdoor_scraper',
            replace_existing=True
        )
        
        # Start the scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started. Running scrapers every {SCRAPE_INTERVAL_MINUTES} minutes.")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped.")
        
        # Close scrapers
        if self.facebook_scraper:
            self.facebook_scraper.close()
        
        if self.nextdoor_scraper:
            self.nextdoor_scraper.close()
    
    def run_facebook_scraper(self):
        """Run the Facebook scraper for all active sources"""
        logger.info("Running Facebook scraper job")
        
        try:
            # Create a new session
            session = self.Session()
            
            # Get all active Facebook sources
            sources = session.query(Source).filter_by(source_type='facebook', is_active=True).all()
            
            if not sources:
                logger.info("No active Facebook sources found")
                session.close()
                return
            
            # Get all active keywords
            keywords = session.query(Keyword).filter_by(is_active=True).all()
            keyword_texts = [keyword.text for keyword in keywords]
            
            if not keyword_texts:
                logger.info("No active keywords found")
                session.close()
                return
            
            # Initialize Facebook scraper if needed
            if not self.facebook_scraper:
                self.facebook_scraper = FacebookScraper()
                
            # Login to Facebook
            if not self.facebook_scraper.login():
                logger.error("Failed to log in to Facebook")
                session.close()
                return
            
            # Scrape each source
            for source in sources:
                try:
                    logger.info(f"Scraping Facebook group: {source.name}")
                    
                    # Scrape the group
                    matched_posts = self.facebook_scraper.scrape_group(source.url, keyword_texts)
                    
                    # Process matches
                    for post in matched_posts:
                        # Check if this match already exists in the database
                        existing_match = None
                        if post['id']:
                            existing_match = session.query(Match).filter_by(
                                source_id=source.id,
                                post_id=post['id']
                            ).first()
                        
                        if not existing_match:
                            # Find the keyword that matched
                            keyword = next((k for k in keywords if k.text.lower() == post.get('matched_keyword', '').lower()), None)
                            
                            if keyword:
                                # Create a new match
                                match = Match(
                                    source_id=source.id,
                                    keyword_id=keyword.id,
                                    post_id=post['id'],
                                    post_url=post['url'],
                                    post_text=post['text'],
                                    post_author=post['author'],
                                    post_date=post['date'],
                                    matched_text=post['matched_keyword'],
                                    is_notified=False,
                                    created_at=datetime.utcnow()
                                )
                                
                                session.add(match)
                    
                    # Update last scraped timestamp
                    source.last_scraped = datetime.utcnow()
                    session.commit()
                    
                except Exception as e:
                    logger.error(f"Error scraping Facebook group {source.name}: {str(e)}")
                    session.rollback()
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in Facebook scraper job: {str(e)}")
            try:
                session.close()
            except:
                pass
    
    def run_nextdoor_scraper(self):
        """Run the Nextdoor scraper for all active sources"""
        logger.info("Running Nextdoor scraper job")
        
        try:
            # Create a new session
            session = self.Session()
            
            # Get all active Nextdoor sources
            sources = session.query(Source).filter_by(source_type='nextdoor', is_active=True).all()
            
            if not sources:
                logger.info("No active Nextdoor sources found")
                session.close()
                return
            
            # Get all active keywords
            keywords = session.query(Keyword).filter_by(is_active=True).all()
            keyword_texts = [keyword.text for keyword in keywords]
            
            if not keyword_texts:
                logger.info("No active keywords found")
                session.close()
                return
            
            # Initialize Nextdoor scraper if needed
            if not self.nextdoor_scraper:
                self.nextdoor_scraper = NextdoorScraper()
                
            # Login to Nextdoor
            if not self.nextdoor_scraper.login():
                logger.error("Failed to log in to Nextdoor")
                session.close()
                return
            
            # Scrape each source
            for source in sources:
                try:
                    logger.info(f"Scraping Nextdoor neighborhood: {source.name}")
                    
                    # Scrape the neighborhood
                    matched_posts = self.nextdoor_scraper.scrape_neighborhood(source.url, keyword_texts)
                    
                    # Process matches
                    for post in matched_posts:
                        # Check if this match already exists in the database
                        existing_match = None
                        if post['id']:
                            existing_match = session.query(Match).filter_by(
                                source_id=source.id,
                                post_id=post['id']
                            ).first()
                        
                        if not existing_match:
                            # Find the keyword that matched
                            keyword = next((k for k in keywords if k.text.lower() == post.get('matched_keyword', '').lower()), None)
                            
                            if keyword:
                                # Create a new match
                                match = Match(
                                    source_id=source.id,
                                    keyword_id=keyword.id,
                                    post_id=post['id'],
                                    post_url=post['url'],
                                    post_text=post['text'],
                                    post_author=post['author'],
                                    post_date=post['date'],
                                    matched_text=post['matched_keyword'],
                                    is_notified=False,
                                    created_at=datetime.utcnow()
                                )
                                
                                session.add(match)
                    
                    # Update last scraped timestamp
                    source.last_scraped = datetime.utcnow()
                    session.commit()
                    
                except Exception as e:
                    logger.error(f"Error scraping Nextdoor neighborhood {source.name}: {str(e)}")
                    session.rollback()
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in Nextdoor scraper job: {str(e)}")
            try:
                session.close()
            except:
                pass
    
    def run_scrapers_now(self):
        """Run both scrapers immediately"""
        self.run_facebook_scraper()
        self.run_nextdoor_scraper()
