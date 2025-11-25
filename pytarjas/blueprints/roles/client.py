# pytarjas/client.py
"""
Client UI blueprint for read-only access.
"""
from flask import Blueprint, url_for, redirect
from pytarjas.auth import login_required

# Create blueprint with URL prefix /client
bp = Blueprint("client", __name__, url_prefix="/client")

# The root /client/ will redirect to a placeholder view (like worker's dashboard)
# as a dedicated client dashboard template hasn't been defined yet.
@bp.route("/")
@login_required
def index():
    """
    Client dashboard - redirects to a read-only or worker view for now.
    """
    # Placeholder: Redirect clients to the general worker index until client UI is built.
    # Alternatively, you could render a placeholder template if you have one.
    return redirect(url_for("worker.index")) 

# You may add other client-specific routes here later.