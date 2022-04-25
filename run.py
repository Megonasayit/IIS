from najlepsiaponuka import db_setup
from najlepsiaponuka.app import app
from najlepsiaponuka.models import *


def setup_db():
    db_setup.main()


def force_create(table):
    db_setup.drop_table(table)
    db_setup.create_table(table)


def run_app():
    app.run(debug=True)


if __name__ == "__main__":
    # force_create(AuctionRegistration)
    # setup_db()
    run_app()

