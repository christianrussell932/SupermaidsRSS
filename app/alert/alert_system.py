import logging
import json
from datetime import datetime
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sendgrid
from sendgrid.helpers.mail import Mail, Content, Email

from app.config.settings import (
    DATABASE_URL, SLACK_WEBHOOK_URL, 
    SENDGRID_API_KEY, NOTIFICATION_EMAIL, SENDER_EMAIL
)
from app.models.models import Match, NotificationSetting, Source, Keyword

# Configure logger
logger = logging.getLogger(__name__)

class AlertSystem:
    """
    Alert system for sending notifications via Slack and email
    """
    
    def __init__(self):
        """Initialize the alert system and database connection"""
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize notification clients
        self.sendgrid_client = None
        if SENDGRID_API_KEY:
            self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    
    def process_new_matches(self):
        """Process all new matches that haven't been notified yet"""
        logger.info("Processing new matches for notifications")
        
        try:
            # Create a new session
            session = self.Session()
            
            # Get notification settings
            settings = session.query(NotificationSetting).first()
            if not settings:
                # Create default settings if none exist
                settings = NotificationSetting(
                    email_enabled=bool(NOTIFICATION_EMAIL),
                    email_address=NOTIFICATION_EMAIL,
                    slack_enabled=bool(SLACK_WEBHOOK_URL),
                    slack_webhook=SLACK_WEBHOOK_URL
                )
                session.add(settings)
                session.commit()
            
            # Get all unnotified matches
            unnotified_matches = session.query(Match).filter_by(is_notified=False).all()
            
            if not unnotified_matches:
                logger.info("No new matches to notify")
                session.close()
                return
            
            logger.info(f"Found {len(unnotified_matches)} new matches to notify")
            
            # Process each match
            for match in unnotified_matches:
                try:
                    # Get source and keyword information
                    source = session.query(Source).filter_by(id=match.source_id).first()
                    keyword = session.query(Keyword).filter_by(id=match.keyword_id).first()
                    
                    if not source or not keyword:
                        logger.error(f"Missing source or keyword for match ID {match.id}")
                        continue
                    
                    # Send notifications based on settings
                    notification_sent = False
                    
                    if settings.slack_enabled and settings.slack_webhook:
                        slack_sent = self.send_slack_notification(
                            settings.slack_webhook,
                            match,
                            source,
                            keyword
                        )
                        notification_sent = notification_sent or slack_sent
                    
                    if settings.email_enabled and settings.email_address:
                        email_sent = self.send_email_notification(
                            settings.email_address,
                            match,
                            source,
                            keyword
                        )
                        notification_sent = notification_sent or email_sent
                    
                    # Mark as notified if at least one notification was sent
                    if notification_sent:
                        match.is_notified = True
                        session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing match ID {match.id}: {str(e)}")
                    session.rollback()
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in process_new_matches: {str(e)}")
            try:
                session.close()
            except:
                pass
    
    def send_slack_notification(self, webhook_url, match, source, keyword):
        """
        Send a notification to Slack
        
        Args:
            webhook_url (str): Slack webhook URL
            match (Match): Match object
            source (Source): Source object
            keyword (Keyword): Keyword object
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Format the post date
            post_date_str = "Unknown date"
            if match.post_date:
                post_date_str = match.post_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Create the message payload
            payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 New House Cleaning Lead Alert!"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Source:*\n{source.name} ({source.source_type.capitalize()})"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Matched Keyword:*\n{keyword.text}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Post Content:*\n```{match.post_text[:500]}{'...' if len(match.post_text) > 500 else ''}```"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Author:*\n{match.post_author or 'Unknown'}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Date:*\n{post_date_str}"
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Original Post"
                                },
                                "url": match.post_url
                            }
                        ]
                    }
                ]
            }
            
            # Send the notification
            response = requests.post(
                webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent for match ID {match.id}")
                return True
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False
    
    def send_email_notification(self, email_address, match, source, keyword):
        """
        Send a notification via email
        
        Args:
            email_address (str): Recipient email address
            match (Match): Match object
            source (Source): Source object
            keyword (Keyword): Keyword object
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not self.sendgrid_client:
            logger.error("SendGrid client not initialized")
            return False
        
        try:
            # Format the post date
            post_date_str = "Unknown date"
            if match.post_date:
                post_date_str = match.post_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Create the email subject
            subject = f"New House Cleaning Lead Alert: {keyword.text}"
            
            # Create the email content
            html_content = f"""
            <h1>🔍 New House Cleaning Lead Alert!</h1>
            <p><strong>Source:</strong> {source.name} ({source.source_type.capitalize()})</p>
            <p><strong>Matched Keyword:</strong> {keyword.text}</p>
            <p><strong>Author:</strong> {match.post_author or 'Unknown'}</p>
            <p><strong>Date:</strong> {post_date_str}</p>
            <h2>Post Content:</h2>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                <p>{match.post_text}</p>
            </div>
            <p><a href="{match.post_url}" style="display: inline-block; margin-top: 20px; padding: 10px 15px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;">View Original Post</a></p>
            """
            
            # Create the email message
            message = Mail(
                from_email=Email(SENDER_EMAIL),
                to_emails=email_address,
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            # Send the email
            response = self.sendgrid_client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email notification sent for match ID {match.id}")
                return True
            else:
                logger.error(f"Failed to send email notification: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
