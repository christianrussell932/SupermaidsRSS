import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session

from config.settings import DATABASE_URL, SECRET_KEY, DEBUG, HOST, PORT
from app.models.models import Base, Source, Keyword, Match, NotificationSetting
from app.scraper.scheduler import ScraperScheduler
from app.alert.alert_system import AlertSystem
from app.utils.error_handling import setup_logger, handle_errors, log_user_activity

# Configure logging
logger = setup_logger('app.dashboard')

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
db_session = scoped_session(sessionmaker(bind=engine))

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize scheduler and alert system
scheduler = ScraperScheduler()
alert_system = AlertSystem()

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.route('/')
@login_required
@handle_errors
def index():
    """Dashboard home page"""
    # Get recent matches
    recent_matches = db_session.query(Match).order_by(desc(Match.created_at)).limit(10).all()
    
    # Get source and keyword counts
    source_count = db_session.query(Source).count()
    keyword_count = db_session.query(Keyword).count()
    match_count = db_session.query(Match).count()
    
    # Get notification settings
    notification_settings = db_session.query(NotificationSetting).first()
    
    log_user_activity('view', 'Dashboard home page')
    
    return render_template('index.html', 
                          recent_matches=recent_matches,
                          source_count=source_count,
                          keyword_count=keyword_count,
                          match_count=match_count,
                          notification_settings=notification_settings)

@app.route('/matches')
@login_required
@handle_errors
def matches():
    """View all matches with filtering options"""
    # Get filter parameters
    source_id = request.args.get('source_id', type=int)
    keyword_id = request.args.get('keyword_id', type=int)
    days = request.args.get('days', type=int, default=30)
    
    # Build query
    query = db_session.query(Match)
    
    # Apply filters
    if source_id:
        query = query.filter(Match.source_id == source_id)
    
    if keyword_id:
        query = query.filter(Match.keyword_id == keyword_id)
    
    if days:
        date_filter = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Match.created_at >= date_filter)
    
    # Get matches with pagination
    page = request.args.get('page', type=int, default=1)
    per_page = 20
    matches = query.order_by(desc(Match.created_at)).limit(per_page).offset((page-1)*per_page).all()
    total = query.count()
    
    # Get sources and keywords for filter dropdowns
    sources = db_session.query(Source).all()
    keywords = db_session.query(Keyword).all()
    
    log_user_activity('view', f'Matches page with filters: source_id={source_id}, keyword_id={keyword_id}, days={days}')
    
    return render_template('matches.html', 
                          matches=matches,
                          sources=sources,
                          keywords=keywords,
                          current_source_id=source_id,
                          current_keyword_id=keyword_id,
                          current_days=days,
                          page=page,
                          per_page=per_page,
                          total=total)

@app.route('/sources')
@login_required
@handle_errors
def sources():
    """View and manage sources"""
    sources = db_session.query(Source).all()
    log_user_activity('view', 'Sources page')
    return render_template('sources.html', sources=sources)

@app.route('/sources/add', methods=['GET', 'POST'])
@login_required
@handle_errors
def add_source():
    """Add a new source"""
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        source_type = request.form.get('source_type')
        
        if not name or not url or not source_type:
            flash('All fields are required', 'danger')
            return redirect(url_for('add_source'))
        
        # Create new source
        source = Source(
            name=name,
            url=url,
            source_type=source_type,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db_session.add(source)
        db_session.commit()
        
        log_user_activity('add', f'Added new {source_type} source: {name}')
        
        flash('Source added successfully', 'success')
        return redirect(url_for('sources'))
    
    log_user_activity('view', 'Add source page')
    return render_template('add_source.html')

@app.route('/sources/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@handle_errors
def edit_source(id):
    """Edit an existing source"""
    source = db_session.query(Source).filter_by(id=id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        is_active = 'is_active' in request.form
        
        if not name or not url:
            flash('Name and URL are required', 'danger')
            return redirect(url_for('edit_source', id=id))
        
        # Update source
        source.name = name
        source.url = url
        source.is_active = is_active
        
        db_session.commit()
        
        log_user_activity('edit', f'Updated source: {name} (ID: {id})')
        
        flash('Source updated successfully', 'success')
        return redirect(url_for('sources'))
    
    log_user_activity('view', f'Edit source page for ID: {id}')
    return render_template('edit_source.html', source=source)

@app.route('/sources/delete/<int:id>', methods=['POST'])
@login_required
@handle_errors
def delete_source(id):
    """Delete a source"""
    source = db_session.query(Source).filter_by(id=id).first_or_404()
    
    source_name = source.name
    db_session.delete(source)
    db_session.commit()
    
    log_user_activity('delete', f'Deleted source: {source_name} (ID: {id})')
    
    flash('Source deleted successfully', 'success')
    return redirect(url_for('sources'))

@app.route('/keywords')
@login_required
@handle_errors
def keywords():
    """View and manage keywords"""
    keywords = db_session.query(Keyword).all()
    log_user_activity('view', 'Keywords page')
    return render_template('keywords.html', keywords=keywords)

@app.route('/keywords/add', methods=['GET', 'POST'])
@login_required
@handle_errors
def add_keyword():
    """Add a new keyword"""
    if request.method == 'POST':
        text = request.form.get('text')
        
        if not text:
            flash('Keyword text is required', 'danger')
            return redirect(url_for('add_keyword'))
        
        # Check if keyword already exists
        existing = db_session.query(Keyword).filter_by(text=text).first()
        if existing:
            flash('Keyword already exists', 'danger')
            return redirect(url_for('add_keyword'))
        
        # Create new keyword
        keyword = Keyword(
            text=text,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db_session.add(keyword)
        db_session.commit()
        
        log_user_activity('add', f'Added new keyword: {text}')
        
        flash('Keyword added successfully', 'success')
        return redirect(url_for('keywords'))
    
    log_user_activity('view', 'Add keyword page')
    return render_template('add_keyword.html')

@app.route('/keywords/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@handle_errors
def edit_keyword(id):
    """Edit an existing keyword"""
    keyword = db_session.query(Keyword).filter_by(id=id).first_or_404()
    
    if request.method == 'POST':
        text = request.form.get('text')
        is_active = 'is_active' in request.form
        
        if not text:
            flash('Keyword text is required', 'danger')
            return redirect(url_for('edit_keyword', id=id))
        
        # Check if keyword already exists
        existing = db_session.query(Keyword).filter_by(text=text).first()
        if existing and existing.id != id:
            flash('Keyword already exists', 'danger')
            return redirect(url_for('edit_keyword', id=id))
        
        # Update keyword
        keyword.text = text
        keyword.is_active = is_active
        
        db_session.commit()
        
        log_user_activity('edit', f'Updated keyword: {text} (ID: {id})')
        
        flash('Keyword updated successfully', 'success')
        return redirect(url_for('keywords'))
    
    log_user_activity('view', f'Edit keyword page for ID: {id}')
    return render_template('edit_keyword.html', keyword=keyword)

@app.route('/keywords/delete/<int:id>', methods=['POST'])
@login_required
@handle_errors
def delete_keyword(id):
    """Delete a keyword"""
    keyword = db_session.query(Keyword).filter_by(id=id).first_or_404()
    
    keyword_text = keyword.text
    db_session.delete(keyword)
    db_session.commit()
    
    log_user_activity('delete', f'Deleted keyword: {keyword_text} (ID: {id})')
    
    flash('Keyword deleted successfully', 'success')
    return redirect(url_for('keywords'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@handle_errors
def settings():
    """View and manage notification settings"""
    settings = db_session.query(NotificationSetting).first()
    
    if not settings:
        settings = NotificationSetting(
            email_enabled=True,
            slack_enabled=True
        )
        db_session.add(settings)
        db_session.commit()
    
    if request.method == 'POST':
        email_enabled = 'email_enabled' in request.form
        email_address = request.form.get('email_address')
        slack_enabled = 'slack_enabled' in request.form
        slack_webhook = request.form.get('slack_webhook')
        
        # Update settings
        settings.email_enabled = email_enabled
        settings.email_address = email_address
        settings.slack_enabled = slack_enabled
        settings.slack_webhook = slack_webhook
        settings.updated_at = datetime.utcnow()
        
        db_session.commit()
        
        log_user_activity('update', f'Updated notification settings: email={email_enabled}, slack={slack_enabled}')
        
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    log_user_activity('view', 'Settings page')
    return render_template('settings.html', settings=settings)

@app.route('/run-scrapers', methods=['POST'])
@login_required
@handle_errors
def run_scrapers():
    """Run scrapers manually"""
    try:
        scheduler.run_scrapers_now()
        log_user_activity('action', 'Manually ran scrapers')
        flash('Scrapers started successfully', 'success')
    except Exception as e:
        logger.error(f"Error running scrapers: {str(e)}")
        flash(f'Error running scrapers: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/process-alerts', methods=['POST'])
@login_required
@handle_errors
def process_alerts():
    """Process alerts manually"""
    try:
        alert_system.process_new_matches()
        log_user_activity('action', 'Manually processed alerts')
        flash('Alerts processed successfully', 'success')
    except Exception as e:
        logger.error(f"Error processing alerts: {str(e)}")
        flash(f'Error processing alerts: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(e)}")
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

def start_app():
    """Start the Flask application and scheduler"""
    try:
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Start the Flask app
        logger.info(f"Starting Flask app on {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=DEBUG)
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        raise

if __name__ == '__main__':
    start_app()
