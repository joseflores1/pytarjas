# main.py
"""
Entry point for the Pytarjas application on Azure App Service.
This file imports the app factory and exposes the 'app' object for Gunicorn.
"""

from pytarjas import create_app

# Create the application instance using the factory
# Azure App Service (Linux) looks for an object named 'app' or 'application'
app = create_app()

if __name__ == "__main__":
    # This block is used for local testing; in production, Gunicorn handles the execution
    app.run()