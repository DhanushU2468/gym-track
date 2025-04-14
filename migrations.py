from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from app import app, db
from flask_migrate import upgrade

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

def migrate():
    with app.app_context():
        # Create/Upgrade database tables
        upgrade()

if __name__ == '__main__':
    migrate() 