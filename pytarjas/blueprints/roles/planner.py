# pytarjas/planner.py
"""
Planner UI blueprint for the role-centric dashboard.

This module defines the /planner/ endpoint, which acts as the role's main
landing page (index) for navigation.
"""

from flask import Blueprint, render_template, g 
from pytarjas.auth import login_required

# Create blueprint with URL prefix /planner
bp = Blueprint("planner", __name__, url_prefix="/planner")


@bp.route("/")
@login_required
def index():
    """
    Planner Dashboard - main landing page for the role.

    Renders the planner index page with links to resources (Forms, Tasks, Plannings).
    """
    # FIX: Change immediate redirect to rendering the role's dashboard/index page.
    # The links in this page will lead to the resource blueprints (e.g., plannings.list_plannings)
    return render_template(
        "planner/index.html",
        user=g.user
    )