from app import create_app, db
from app.models import User, Template, Exhibition, ExhibitionItem

app = create_app()

with app.app_context():
    # Создаем все таблицы в базе данных
    db.create_all()
    print("База данных инициализирована. Таблицы созданы.")