from pytarjas import create_app
from pytarjas.models.user_models import db, Admin

app = create_app()

with app.app_context():
    admin=Admin(
        username="admin",
        email="admin@hgt.com",
        role="admin",
    )
    admin.set_user_password(admin, "admin123")
    db.session.add(admin)
    db.session.commit()
    print(f"Created admin: {admin.username}")