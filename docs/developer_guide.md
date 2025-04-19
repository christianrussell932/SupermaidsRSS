# Social Media Keyword Alert SaaS - Developer Documentation

## Architecture Overview

The Social Media Keyword Alert SaaS application is built with a modular architecture consisting of the following components:

1. **Database Models**: SQLAlchemy models for storing data
2. **Scraper Engine**: Components for extracting data from social media platforms
3. **Alert System**: Notification mechanisms for sending alerts
4. **Web Dashboard**: Flask application for user interaction
5. **Error Handling & Logging**: System for tracking and managing errors

## Directory Structure

```
social_media_alert_saas/
├── app/
│   ├── alert/              # Alert system components
│   ├── config/             # Configuration settings
│   ├── dashboard/          # Flask web application
│   ├── models/             # Database models
│   ├── scraper/            # Scraper components
│   ├── static/             # Static assets for web dashboard
│   ├── templates/          # HTML templates
│   └── utils/              # Utility functions
├── docs/                   # Documentation
├── logs/                   # Log files
└── tests/                  # Unit tests
```

## Component Details

### Database Models

Located in `app/models/models.py`, the application uses SQLAlchemy ORM with the following models:

- **Source**: Represents a Facebook Group or Nextdoor neighborhood
- **Keyword**: Represents keywords to monitor
- **Match**: Represents a keyword match found in a source
- **NotificationSetting**: Stores user notification preferences

### Scraper Engine

The scraper engine consists of:

- **FacebookScraper** (`app/scraper/facebook_scraper.py`): Handles Facebook Group scraping
- **NextdoorScraper** (`app/scraper/nextdoor_scraper.py`): Handles Nextdoor neighborhood scraping
- **ScraperScheduler** (`app/scraper/scheduler.py`): Manages periodic scraping

The scrapers use Selenium WebDriver to automate browser interactions and extract post data.

### Alert System

The alert system (`app/alert/alert_system.py`) handles:

- Processing new matches
- Sending Slack notifications via webhooks
- Sending email notifications via SendGrid

### Web Dashboard

The Flask application (`app/dashboard/app.py`) provides:

- Dashboard overview with statistics
- Match viewing with filtering
- Source management
- Keyword management
- Notification settings
- Manual actions (run scrapers, process alerts)

### Error Handling & Logging

The error handling system (`app/utils/error_handling.py`) provides:

- Configurable logging with rotation
- Error handling decorators for routes
- Specific handlers for common errors (CAPTCHA, authentication)
- Activity logging for scrapers, alerts, and user actions

## Configuration

The application uses environment variables loaded from a `.env` file for configuration. See `app/config/settings.py` for details.

## Deployment

The application can be deployed using:

- **Docker**: Using `Dockerfile` and `docker-compose.yml`
- **Render.com**: Using `render.yaml` for Blueprint deployment

## Testing

Unit tests are located in the `tests/` directory and can be run using:

```bash
./run_tests.sh
```

## Future Enhancements

Potential enhancements for scaling to a full multi-user SaaS:

1. **User Authentication**: Implement user registration and login
2. **Multi-tenancy**: Isolate data between users
3. **Billing Integration**: Add Stripe or LemonSqueezy for payments
4. **Usage Limits**: Implement tiered access based on subscription level
5. **API Access**: Create REST API for programmatic access
6. **Additional Platforms**: Support for other social media platforms

## Maintenance

Regular maintenance tasks:

1. Update Chrome and WebDriver versions
2. Monitor for changes in Facebook/Nextdoor page structure
3. Review and rotate logs
4. Update dependencies for security patches
