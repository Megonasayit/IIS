import bdb
import datetime
from . import *
from .models import *


def create_tables():
    db.drop_all()
    db.create_all()


def populate_tables():
    user1 = User(name="FFF",
                 surname="SSS",
                 email="admin@najlepsiaponuka.xyz",
                 phone="123456789",
                 password=bcrypt.generate_password_hash("adminxbican03").decode("utf-8"),
                 type=UserType.ADMIN
                 )

    user2 = User(name="lici",
                 surname="tator",
                 email="licitator@najlepsiaponuka.xyz",
                 phone="123456789",
                 password=bcrypt.generate_password_hash("licitator123").decode("utf-8"),
                 type=UserType.AUCTIONEER
                 )

    user3 = User(name="basic",
                 surname="user",
                 email="user@najlepsiaponuka.xyz",
                 phone="123456789",
                 password=bcrypt.generate_password_hash("user123").decode("utf-8"),
                 type=UserType.BASIC
                 )

    db.session.bulk_save_objects([user1, user2, user3])
    db.session.commit()


def drop_table(table):
    table.__table__.drop(db.session.bind)


def create_table(table):
    table.__table__.create(db.session.bind)


def main():
    create_tables()
    populate_tables()


if __name__ == "__main__":
    main()