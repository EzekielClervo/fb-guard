# Auto Guard - Facebook Security Tool

A comprehensive Facebook profile security web application focused on enhancing user account protection and privacy management.

## Key Features

- **Profile Guard Activation**: Secure your Facebook profile with automated guard activation
- **Auto Post Management**: Create, update, and manage posts with automatic engagement metrics
- **Multi-credential Support**: Works with any Facebook credential type (Email, UID, Username, Phone)
- **Post Privacy Control**: Control the visibility of your Facebook posts (Public, Friends, Only Me)
- **Bulk Post Management**: Delete all or selected posts from your timeline
- **Admin Dashboard**: Comprehensive admin interface to manage users and monitor app usage

## Technology Stack

- **Backend**: Flask, SQLAlchemy, SQLite (free tier)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Authentication**: Flask-Login, Facebook API integration
- **Task Scheduling**: APScheduler for automated posts and updates
- **Deployment**: Render.com with free tier hosting

## Deployment

This application is configured for deployment on Render.com's free tier:

1. Create a new web service pointing to this repository
2. Render will automatically detect the `render.yaml` configuration
3. The application will use SQLite for the database in the free tier
4. No payment information is required for deployment

## Development

To run the application locally:

```
# Clone the repository
git clone https://github.com/EzekielClervo/fb-guard.git
cd fb-guard

# Install dependencies
pip install -r requirements-render.txt

# Run the application
gunicorn --bind 0.0.0.0:5000 main:app
```

## Credits

Developed by Divon Logan