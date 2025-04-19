# Social Media Keyword Alert SaaS - User Guide

## Introduction

Welcome to the Social Media Keyword Alert SaaS application! This tool helps you monitor Facebook Groups and Nextdoor neighborhoods for potential house cleaning leads by detecting specific keywords and sending alerts via email or Slack.

## Getting Started

### Prerequisites

Before using the application, you'll need:

1. Facebook account with membership in the groups you want to monitor
2. Nextdoor account with access to the neighborhoods you want to monitor
3. Slack workspace (optional, for Slack notifications)
4. SendGrid account (optional, for email notifications)

### Initial Setup

1. **Environment Variables**: Create a `.env` file in the root directory with the following variables:

```
# Database Configuration
DB_TYPE=sqlite  # Use 'postgresql' for production
DB_HOST=localhost  # Only needed for PostgreSQL
DB_PORT=5432  # Only needed for PostgreSQL
DB_NAME=social_media_alert
DB_USER=username  # Only needed for PostgreSQL
DB_PASSWORD=password  # Only needed for PostgreSQL

# Facebook Configuration
FACEBOOK_EMAIL=your_facebook_email@example.com
FACEBOOK_PASSWORD=your_facebook_password
# Alternatively, you can use cookies (more reliable)
FACEBOOK_COOKIES={"name":"c_user","value":"123456789",...}

# Nextdoor Configuration
NEXTDOOR_EMAIL=your_nextdoor_email@example.com
NEXTDOOR_PASSWORD=your_nextdoor_password
# Alternatively, you can use cookies (more reliable)
NEXTDOOR_COOKIES={"name":"nd_session","value":"abc123",...}

# Notification Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
SENDGRID_API_KEY=your_sendgrid_api_key
NOTIFICATION_EMAIL=your_email@example.com
SENDER_EMAIL=alerts@socialmediaalert.com

# Application Configuration
SECRET_KEY=generate_a_secure_random_key
DEBUG=False
SCRAPE_INTERVAL_MINUTES=60
```

2. **Install Dependencies**: Run `pip install -r requirements.txt` to install all required packages.

3. **Initialize Database**: The application will automatically create the database on first run.

4. **Start the Application**: Run `python app/dashboard/app.py` to start the web server.

## Using the Dashboard

### Dashboard Overview

The dashboard home page provides a quick overview of:
- Total sources being monitored
- Active keywords
- Total matches found
- Recent matches with links to original posts

### Managing Sources

1. Navigate to the **Sources** page
2. Click **Add New Source** to add a Facebook Group or Nextdoor neighborhood
3. Enter a descriptive name, select the source type, and paste the full URL
4. Click **Add Source** to save

To edit or delete a source, use the corresponding buttons in the sources table.

### Managing Keywords

1. Navigate to the **Keywords** page
2. Click **Add New Keyword** to add a new keyword or phrase
3. Enter the keyword text (e.g., "recommend a house cleaner")
4. Click **Add Keyword** to save

The Keywords page also includes suggested keywords for house cleaning leads that you can add with one click.

To edit or delete a keyword, use the corresponding buttons in the keywords table.

### Viewing Matches

1. Navigate to the **Matches** page
2. Use the filters to narrow down results by source, keyword, or time period
3. Click **View Post** to open the original post in a new tab

### Notification Settings

1. Navigate to the **Settings** page
2. Configure email notifications:
   - Toggle the switch to enable/disable
   - Enter the email address to receive notifications
3. Configure Slack notifications:
   - Toggle the switch to enable/disable
   - Enter the Slack webhook URL
4. Click **Save Settings** to apply changes

### Manual Actions

From the dashboard, you can manually:
- Run scrapers immediately using the **Run Scrapers Now** button
- Process pending alerts using the **Process Alerts Now** button

## Deployment

### Local Deployment

1. Clone the repository
2. Create and configure the `.env` file
3. Install dependencies: `pip install -r requirements.txt`
4. Start the application: `python app/dashboard/app.py`

### Docker Deployment

1. Configure environment variables in `.env` file
2. Build and start containers: `docker-compose up -d`

### Render.com Deployment

1. Push your code to a Git repository
2. Connect your repository to Render.com
3. Use the `render.yaml` file for Blueprint deployment
4. Configure the required environment variables in the Render dashboard

## Troubleshooting

### Common Issues

1. **Login Failures**:
   - Check your Facebook/Nextdoor credentials
   - Consider using cookies instead of email/password
   - Look for CAPTCHA errors in the logs

2. **No Matches Found**:
   - Verify your keywords are commonly used in the groups
   - Check that the scraper is running (see logs)
   - Try running the scrapers manually

3. **Notifications Not Sending**:
   - Verify your Slack webhook URL or SendGrid API key
   - Check notification settings are enabled
   - Look for errors in the logs

### Logs

Log files are stored in the `logs` directory:
- `app.log`: General application logs
- `captcha_errors.log`: CAPTCHA detection errors
- `auth_errors.log`: Authentication failures

## Scaling to Multi-User SaaS

To scale this application to a full multi-user SaaS:

1. Implement user authentication and registration
2. Add user-specific data isolation
3. Implement billing with Stripe or LemonSqueezy
4. Set up usage limits for different pricing tiers

## Support

For additional support, please contact the development team.
