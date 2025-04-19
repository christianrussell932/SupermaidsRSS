import unittest
import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.models import Base, Source, Keyword, Match, NotificationSetting
from app.scraper.facebook_scraper import FacebookScraper
from app.scraper.nextdoor_scraper import NextdoorScraper
from app.alert.alert_system import AlertSystem
from app.config.settings import DATABASE_URL

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

class TestModels(unittest.TestCase):
    """Test the database models"""
    
    def setUp(self):
        """Set up the test database"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Create an in-memory database
        self.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(self.engine)
        
        # Create a session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def tearDown(self):
        """Clean up after tests"""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_source_model(self):
        """Test the Source model"""
        # Create a source
        source = Source(
            name="Test Facebook Group",
            url="https://www.facebook.com/groups/test",
            source_type="facebook",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(source)
        self.session.commit()
        
        # Query the source
        queried_source = self.session.query(Source).first()
        
        # Check that the source was created correctly
        self.assertEqual(queried_source.name, "Test Facebook Group")
        self.assertEqual(queried_source.url, "https://www.facebook.com/groups/test")
        self.assertEqual(queried_source.source_type, "facebook")
        self.assertTrue(queried_source.is_active)
    
    def test_keyword_model(self):
        """Test the Keyword model"""
        # Create a keyword
        keyword = Keyword(
            text="recommend a house cleaner",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(keyword)
        self.session.commit()
        
        # Query the keyword
        queried_keyword = self.session.query(Keyword).first()
        
        # Check that the keyword was created correctly
        self.assertEqual(queried_keyword.text, "recommend a house cleaner")
        self.assertTrue(queried_keyword.is_active)
    
    def test_match_model(self):
        """Test the Match model"""
        # Create a source and keyword
        source = Source(
            name="Test Facebook Group",
            url="https://www.facebook.com/groups/test",
            source_type="facebook",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        keyword = Keyword(
            text="recommend a house cleaner",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(source)
        self.session.add(keyword)
        self.session.commit()
        
        # Create a match
        match = Match(
            source_id=source.id,
            keyword_id=keyword.id,
            post_id="123456789",
            post_url="https://www.facebook.com/groups/test/posts/123456789",
            post_text="Can anyone recommend a house cleaner in the area?",
            post_author="John Doe",
            post_date=datetime.utcnow(),
            matched_text="recommend a house cleaner",
            is_notified=False,
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(match)
        self.session.commit()
        
        # Query the match
        queried_match = self.session.query(Match).first()
        
        # Check that the match was created correctly
        self.assertEqual(queried_match.source_id, source.id)
        self.assertEqual(queried_match.keyword_id, keyword.id)
        self.assertEqual(queried_match.post_id, "123456789")
        self.assertEqual(queried_match.post_url, "https://www.facebook.com/groups/test/posts/123456789")
        self.assertEqual(queried_match.post_text, "Can anyone recommend a house cleaner in the area?")
        self.assertEqual(queried_match.post_author, "John Doe")
        self.assertEqual(queried_match.matched_text, "recommend a house cleaner")
        self.assertFalse(queried_match.is_notified)
    
    def test_notification_setting_model(self):
        """Test the NotificationSetting model"""
        # Create notification settings
        settings = NotificationSetting(
            email_enabled=True,
            email_address="test@example.com",
            slack_enabled=True,
            slack_webhook="https://hooks.slack.com/services/xxx/yyy/zzz",
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(settings)
        self.session.commit()
        
        # Query the settings
        queried_settings = self.session.query(NotificationSetting).first()
        
        # Check that the settings were created correctly
        self.assertTrue(queried_settings.email_enabled)
        self.assertEqual(queried_settings.email_address, "test@example.com")
        self.assertTrue(queried_settings.slack_enabled)
        self.assertEqual(queried_settings.slack_webhook, "https://hooks.slack.com/services/xxx/yyy/zzz")


class TestFacebookScraper(unittest.TestCase):
    """Test the Facebook scraper"""
    
    @patch('app.scraper.facebook_scraper.webdriver.Chrome')
    def test_login_with_cookies(self, mock_chrome):
        """Test login with cookies"""
        # Mock the driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock the is_logged_in method
        with patch.object(FacebookScraper, '_is_logged_in', return_value=True):
            # Create a scraper
            scraper = FacebookScraper()
            
            # Mock the cookies file
            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', MagicMock()), \
                 patch('json.load', return_value=[{'name': 'test', 'value': 'test'}]):
                
                # Call login
                result = scraper.login()
                
                # Check that login was successful
                self.assertTrue(result)
                
                # Check that the driver was called correctly
                mock_driver.get.assert_called_with('https://www.facebook.com/')
                mock_driver.add_cookie.assert_called()
    
    @patch('app.scraper.facebook_scraper.webdriver.Chrome')
    def test_match_keyword(self, mock_chrome):
        """Test keyword matching"""
        # Create a scraper
        scraper = FacebookScraper()
        
        # Test matching
        self.assertTrue(scraper._match_keyword("Can anyone recommend a house cleaner?", "recommend a house cleaner"))
        self.assertTrue(scraper._match_keyword("I need a cleaning service for my apartment", "cleaning service"))
        self.assertFalse(scraper._match_keyword("I'm looking for a plumber", "house cleaner"))
        self.assertFalse(scraper._match_keyword("", "house cleaner"))
        self.assertFalse(scraper._match_keyword("I need a cleaner", ""))


class TestAlertSystem(unittest.TestCase):
    """Test the alert system"""
    
    def setUp(self):
        """Set up the test database"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Create an in-memory database
        self.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(self.engine)
        
        # Create a session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create test data
        self.source = Source(
            name="Test Facebook Group",
            url="https://www.facebook.com/groups/test",
            source_type="facebook",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.keyword = Keyword(
            text="recommend a house cleaner",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.settings = NotificationSetting(
            email_enabled=True,
            email_address="test@example.com",
            slack_enabled=True,
            slack_webhook="https://hooks.slack.com/services/xxx/yyy/zzz",
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(self.source)
        self.session.add(self.keyword)
        self.session.add(self.settings)
        self.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    @patch('app.alert.alert_system.requests.post')
    def test_send_slack_notification(self, mock_post):
        """Test sending Slack notifications"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create a match
        match = Match(
            source_id=self.source.id,
            keyword_id=self.keyword.id,
            post_id="123456789",
            post_url="https://www.facebook.com/groups/test/posts/123456789",
            post_text="Can anyone recommend a house cleaner in the area?",
            post_author="John Doe",
            post_date=datetime.utcnow(),
            matched_text="recommend a house cleaner",
            is_notified=False,
            created_at=datetime.utcnow()
        )
        
        # Add to session and commit
        self.session.add(match)
        self.session.commit()
        
        # Create an alert system with a mocked session
        with patch('app.alert.alert_system.create_engine'), \
             patch('app.alert.alert_system.sessionmaker') as mock_sessionmaker:
            
            # Mock the session
            mock_session = MagicMock()
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [self.source, self.keyword]
            mock_sessionmaker.return_value.return_value = mock_session
            
            # Create the alert system
            alert_system = AlertSystem()
            
            # Call send_slack_notification
            result = alert_system.send_slack_notification(
                "https://hooks.slack.com/services/xxx/yyy/zzz",
                match,
                self.source,
                self.keyword
            )
            
            # Check that the notification was sent
            self.assertTrue(result)
            mock_post.assert_called_once()
            
            # Check that the payload contains the expected data
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['data'])
            self.assertIn("House Cleaning Lead Alert", payload['blocks'][0]['text']['text'])
            self.assertIn("recommend a house cleaner", str(payload))
            self.assertIn("Can anyone recommend a house cleaner in the area?", str(payload))


if __name__ == '__main__':
    unittest.main()
