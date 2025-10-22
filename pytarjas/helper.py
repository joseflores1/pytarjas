from flask import request

def wants_json():
    """
    Helper function to determine if the client wants a JSON response.
    
    REASONING:
    This allows the same endpoint to serve both:
    - HTML: Traditional browser requests (clicking links, submitting forms)
    - JSON: API clients, AJAX requests, Progressive Web App
    
    Checks multiple indicators:
    1. Content-Type header is application/json
    2. Accept header includes application/json
    3. Flask's request.is_json flag
    
    Returns:
        bool: True if client wants JSON, False if HTML
    """
    return (
        request.is_json or 
        request.headers.get("Accept") == "application/json" or
        "application/json" in request.headers.get("Accept", "")
    )
