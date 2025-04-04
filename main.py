"""
Entry point for local development server
"""
from api import create_app

# Create the Flask application
app = create_app()

# Run the development server if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
