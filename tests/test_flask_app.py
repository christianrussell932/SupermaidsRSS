import os
import sys
import unittest
from flask import Flask
from flask_testing import TestCase

# Add the parent directory to the path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dashboard.app import app
from app.models.models import Base, Source, Keyword, Match, NotificationSetting
from app.config.settings import DATABASE_URL

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

class TestFlaskApp(TestCase):
    """Test the Flask application"""
    
    def create_app(self):
        """Create and configure the Flask app for testing"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = TEST_DATABASE_URL
        return app
    
    def setUp(self):
        """Set up the test database"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, scoped_session
        
        # Create an in-memory database
        self.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(self.engine)
        
        # Create a session
        self.session = scoped_session(sessionmaker(bind=self.engine))
        
        # Create test data
        source = Source(
            name="Test Facebook Group",
            url="https://www.facebook.com/groups/test",
            source_type="facebook",
            is_active=True
        )
        
        keyword = Keyword(
            text="recommend a house cleaner",
            is_active=True
        )
        
        settings = NotificationSetting(
            email_enabled=True,
            email_address="test@example.com",
            slack_enabled=True,
            slack_webhook="https://hooks.slack.com/services/xxx/yyy/zzz"
        )
        
        # Add to session and commit
        self.session.add(source)
        self.session.add(keyword)
        self.session.add(settings)
        self.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        self.session.remove()
        Base.metadata.drop_all(self.engine)
    
    def test_index_page(self):
        """Test the index page"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Get the index page
        response = self.client.get('/')
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the page contains expected content
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Recent Matches', response.data)
    
    def test_sources_page(self):
        """Test the sources page"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Get the sources page
        response = self.client.get('/sources')
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the page contains expected content
        self.assertIn(b'Sources', response.data)
        self.assertIn(b'Test Facebook Group', response.data)
    
    def test_add_source(self):
        """Test adding a source"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Post a new source
        response = self.client.post('/sources/add', data={
            'name': 'New Test Group',
            'url': 'https://www.facebook.com/groups/newtest',
            'source_type': 'facebook'
        }, follow_redirects=True)
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the new source is in the database
        source = self.session.query(Source).filter_by(name='New Test Group').first()
        self.assertIsNotNone(source)
        self.assertEqual(source.url, 'https://www.facebook.com/groups/newtest')
    
    def test_keywords_page(self):
        """Test the keywords page"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Get the keywords page
        response = self.client.get('/keywords')
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the page contains expected content
        self.assertIn(b'Keywords', response.data)
        self.assertIn(b'recommend a house cleaner', response.data)
    
    def test_add_keyword(self):
        """Test adding a keyword"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Post a new keyword
        response = self.client.post('/keywords/add', data={
            'text': 'new test keyword'
        }, follow_redirects=True)
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the new keyword is in the database
        keyword = self.session.query(Keyword).filter_by(text='new test keyword').first()
        self.assertIsNotNone(keyword)
    
    def test_settings_page(self):
        """Test the settings page"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Get the settings page
        response = self.client.get('/settings')
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the page contains expected content
        self.assertIn(b'Notification Settings', response.data)
        self.assertIn(b'test@example.com', response.data)
    
    def test_update_settings(self):
        """Test updating settings"""
        # Skip login for testing
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        
        # Post updated settings
        response = self.client.post('/settings', data={
            'email_enabled': 'on',
            'email_address': 'updated@example.com',
            'slack_enabled': 'on',
            'slack_webhook': 'https://hooks.slack.com/services/aaa/bbb/ccc'
        }, follow_redirects=True)
        
        # Check that the response is successful
        self.assert200(response)
        
        # Check that the settings were updated in the database
        settings = self.session.query(NotificationSetting).first()
        self.assertEqual(settings.email_address, 'updated@example.com')
        self.assertEqual(settings.slack_webhook, 'https://hooks.slack.com/services/aaa/bbb/ccc')


if __name__ == '__main__':
    unittest.main()
