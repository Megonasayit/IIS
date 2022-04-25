from . import db
from enum import Enum


class EnumChoices(Enum):
    @classmethod
    def choices(cls):
        return [(choice, choice) for choice in cls]

    @classmethod
    def coerce(cls, item):
        return cls(str(item)) if not isinstance(item, cls) else item

    def __str__(self):
        return str(self.value)


class UserType(EnumChoices):
    BASIC = "basic"
    ADMIN = "admin"
    AUCTIONEER = "licitátor"

class AuctionType(EnumChoices):
    OFFER = "ponuková"
    DEMAND = "dopytová"


class AuctionState(EnumChoices):
    ACTIVE = "aktívna"
    CONFIRMED = "schválená"
    CREATED = "vytvorená"
    CLOSED = "ukončená"


class AuctionRules(EnumChoices):
    OPEN = "otvorená"
    CLOSED = "zatvorená"


class AuctionCategory(EnumChoices):
    ELECTRONICS = "elektronika"
    CAR = "auto"
    SPORT = "šport"
    FURNITURE = "nábytok"
    PROPERTY = "nehnuteľnosť"
    SERVICE = "služba"
    OTHERS = "iné"


class AuctionRegistrationState(EnumChoices):
    CREATED = "vytvorená"
    ALLOWED = "schválená"
    FORBIDDEN = "zakázaná"

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(UserType))
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(254))
    password = db.Column(db.String(60))
    authenticated = db.Column(db.BOOLEAN, default=False, nullable=False)

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.email

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_admin(self):
        return self.type is UserType.ADMIN

    def is_auctioneer(self):
        return self.type in (UserType.ADMIN, UserType.AUCTIONEER)

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False

    def is_registered_on_auction(self, auction_id):
        reg = AuctionRegistration.query.filter_by(auction_id=auction_id, creator_id=self.user_id).first()
        return reg is not None and reg.state == AuctionRegistrationState.ALLOWED

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "surname": self.surname,
            "type": self.type.value,
            "phone": self.phone,
            "email": self.email,
            "link": f"/admin/user/profile?id={self.user_id}",
            "delete": f"/deleteUser/{self.user_id}"
        }


class Auction(db.Model):
    auction_id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Numeric(20,2))
    start_price = db.Column(db.Numeric(20,2))
    minimal_bid = db.Column(db.Numeric(20,2))
    title = db.Column(db.TEXT)
    rules = db.Column(db.Enum(AuctionRules))
    description = db.Column(db.TEXT)
    type = db.Column(db.Enum(AuctionType))
    state = db.Column(db.Enum(AuctionState))
    category = db.Column(db.Enum(AuctionCategory))
    image = db.Column(db.String(60))
    start_date = db.Column(db.TIMESTAMP(6))
    end_date = db.Column(db.TIMESTAMP(6))

    creator_id = db.Column(db.Integer, db.ForeignKey('user.user_id', ondelete="cascade"), nullable=False)
    creation_timestamp = db.Column(db.TIMESTAMP(6))

    auctioneer_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    confirmation_timestamp = db.Column(db.TIMESTAMP(6))

    def view_auction_to_dict(self):
        return {
            "creator_id": self.creator_id,
            "auction_id": self.auction_id,
            "image": self.image,
            "title": self.title,
            "type": self.type.value,
            "category": self.category.value,
            "description": self.description,
            "detail": f"/auctionDetail/{self.auction_id}",
            "rules": self.rules.value,
            "state": self.state.value,
        }

    def edit_to_dict(self):
        return {
            "auction_id": self.auction_id,
            "title": self.title,
            "start_price": self.start_price,
            "type": self.type.value,
            "state": self.state.value,
            "category": self.category.value,
            "link": f"/editAuction/{self.auction_id}"
        }

    def bid_to_dict(self):
        return {
            "title": self.title,
            "start_price": self.start_price,
            "price": self.price,
            "type": self.type.value,
            "state": self.state.value,
            "category": self.category.value,
            "detail": f"/auctionDetail/{self.auction_id}"
        }

    def manage_to_dict(self):
        return {
            "auction_id": self.auction_id,
            "title": self.title,
            "start_price": self.start_price,
            "type": self.type.value,
            "state": self.state.value,
            "category": self.category.value,
            "manage": f"/manageAuction/{self.auction_id}",
            "delete": f"/deleteAuction/{self.auction_id}"
        }

    def show_bid(self, user):
        if not user.is_authenticated:
            return False
        return Bid.query.filter_by(auction_id=self.auction_id,
                                   creator_id=user.user_id).first().price

    def did_user_bid_on_closed(self, user):
        if not user.is_authenticated:
            return False
        return Bid.query.filter_by(auction_id=self.auction_id,
                                   creator_id=user.user_id).first() and self.is_rules_closed()

    def is_rules_closed(self):
        return self.rules == AuctionRules.CLOSED

    def is_closed(self):
        return self.state == AuctionState.CLOSED

    def is_offer(self):
        return self.type == AuctionType.OFFER

    def has_bid(self):
        return Bid.query.filter_by(auction_id=self.auction_id).first()

    def last_bid_current_users(self, current_user):
        if not current_user.is_authenticated:
            return False
        if Bid.query.filter_by(creator_id=current_user.user_id, auction_id=self.auction_id, price=self.price).first() is not None:
            return True

    def is_confirmed(self):
        return self.state == AuctionState.CONFIRMED


class Bid(db.Model):
    bid_id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Numeric(20,2))
    timestamp = db.Column(db.TIMESTAMP(6))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.auction_id', ondelete='CASCADE'), nullable=False)


class AuctionRegistration(db.Model):
    auction_registration_id = db.Column(db.Integer, primary_key=True)
    creation_timestamp = db.Column(db.TIMESTAMP(6))
    checked_timestamp = db.Column(db.TIMESTAMP(6))
    state = db.Column(db.Enum(AuctionRegistrationState))
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.auction_id', ondelete='CASCADE'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    auctioneer_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))

    def registration_to_dict(self):
        user = User.query.filter_by(user_id=self.creator_id).first()
        return {
            "user_id": self.creator_id,
            "name": user.name,
            "surname": user.surname,
            "type": user.type.value,
            "phone": user.phone,
            "email": user.email,
            "allow": f"/user/{self.auction_registration_id}/allow",
            "deny": f"/user/{self.auction_registration_id}/deny"
        }
