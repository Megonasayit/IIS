import datetime

from . import *
from flask import flash, redirect, render_template, request, url_for, abort
from .forms import RegistrationForm, LoginForm, AuctionForm, UpdateForm, UserManagementForm, AuctionManageForm, BidForm, \
    secure_filename
from .models import *
from flask_login import current_user, login_user, login_required, logout_user
import os


def redirect_url(default='index'):
    return request.form.get('referrer') or \
           request.referrer or \
           url_for(default)


def roles_required(*roles):
    """
    Checks the required roles before accessing endpoint
    if requirements are not met user is redirected to the home page at /index.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):

            if hasattr(current_user, "type"):
                if current_user.type in roles:
                    return func(*args, **kwargs)

            flash(f"Nedostatočné práva k prístupu na /{request.url.split('/', maxsplit=3)[2]}.")
            return abort(403)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


@login_manager.user_loader
def load_user(email):
    """
    :param user_id: email as email is what user uses as a login username
    :return: return User object
    """
    return User.query.filter(User.email == email).first()


@app.route("/")
def index():  # put application's code here
    return render_template("index.html")


@app.route("/auth/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if request.method == "POST":
        if form.validate_on_submit():
            user = User(
                email=form.email.data,
                password=form.password.data
            )
            login_user(user, remember=True, duration=datetime.timedelta(seconds=5))
            return redirect(redirect_url())

    return render_template("auth/login.html", form=form)


@app.route("/auth/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/auth/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()

    if request.method == "POST":
        if form.validate_on_submit():
            user = User(name=form.name.data,
                        surname=form.surname.data,
                        email=form.email.data,
                        phone=form.phone.data,
                        password=bcrypt.generate_password_hash(form.password.data),
                        type="basic"
                        )
            db.session.add(user)
            db.session.commit()
            return redirect(redirect_url())

    return render_template("auth/register.html", form=form)


@app.route("/deleteUser/<string:user_id>")
@roles_required(UserType.ADMIN)
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    else:
        flash("Užívateľ neexistuje.")
    return redirect(url_for("user_management"))


@app.route("/auctions")
def auctions_controller():
    auctions = Auction.query.filter(Auction.state.in_([AuctionState.ACTIVE, AuctionState.CLOSED, AuctionState.CONFIRMED])).all()
    return render_template("auction/auctions.html", auctions=auctions)


@app.route("/auctionDetail/<string:auction_id>", methods=["GET", "POST"])
def auction_detail(auction_id):
    auction = Auction.query.get(auction_id)
    bid_form = BidForm(auction_price=auction.price, minimal_bid=auction.minimal_bid)
    if not auction.has_bid():
        bid_form.price.data = auction.price
    else:
        if auction.is_offer():
            bid_form.price.data = auction.price + auction.minimal_bid
        else:
            bid_form.price.data = auction.price - auction.minimal_bid

    if request.method == "GET":
        return render_template("auction/auctionDetail.html", auction=auction, bid_form=bid_form)
    elif request.method == "POST" and current_user.is_authenticated:
        if auction.state == AuctionState.CONFIRMED:
            reg = AuctionRegistration.query.filter_by(auction_id=auction_id, creator_id=current_user.user_id).first()
            if auction.auctioneer_id != current_user.user_id and auction.creator_id != current_user.user_id and reg is None:
                flash("Registrácia bola vytvorená.")
                registration = AuctionRegistration(
                    auction_id=auction.auction_id,
                    creator_id=current_user.user_id,
                    auctioneer_id=auction.auctioneer_id,
                    state=AuctionRegistrationState.CREATED
                )
                db.session.add(registration)
                db.session.commit()
            return redirect(url_for("auction_detail", auction_id=auction_id))
        else:
            flash("Na aukciu sa už nedá registrovať.")
            return redirect(url_for("auction_detail", auction_id=auction_id))
    else:
        return render_template("auction/auctionNotFound.html")


@app.route("/user/<string:auction_registration_id>/allow")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def allow_registration(auction_registration_id):
    registration = AuctionRegistration.query.get(auction_registration_id)
    registration.state = AuctionRegistrationState.ALLOWED
    registration.checked_timestamp = datetime.datetime.now()
    db.session.commit()
    return redirect(url_for("manage_auction", auction_id=registration.auction_id))


@app.route("/user/<string:auction_registration_id>/deny")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def deny_registration(auction_registration_id):
    registration = AuctionRegistration.query.get(auction_registration_id)
    registration.state = AuctionRegistrationState.FORBIDDEN
    registration.checked_timestamp = datetime.datetime.now()
    db.session.commit()
    return redirect(url_for("manage_auction", auction_id=registration.auction_id))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile/profile.html")


@app.route("/updateProfile", methods=["GET", "POST"])
@login_required
def update_profile():
    form = UpdateForm()
    if request.method == "POST":
        if form.validate_on_submit():
            if form.name.data:
                current_user.name = form.name.data
            if form.surname.data:
                current_user.surname = form.surname.data
            if form.email.data:
                current_user.email = form.email.data
            if form.phone.data:
                current_user.phone = form.phone.data
            if form.password.data:
                current_user.password = bcrypt.generate_password_hash(form.password.data)
            db.session.commit()
            return redirect(url_for("profile"))
    return render_template("profile/updateProfile.html", form=form)


@app.route("/auctionManagement")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def auction_management():
    return render_template("auction/auctionsManagement.html")


@app.route("/deleteAuction/<string:auction_id>")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def delete_auction(auction_id):
    auction = Auction.query.filter_by(auction_id=auction_id).first()
    if auction:
        db.session.delete(auction)
        db.session.commit()
    else:
        flash("Aukcia neexistuje.")
    return redirect(url_for("auction_management"))


@app.route("/manageAuction/<string:auction_id>", methods=["GET", "POST"])
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def manage_auction(auction_id):
    auction = Auction.query.filter_by(auction_id=auction_id).first()
    form = AuctionManageForm()
    if request.method == "GET":
        form.state.data = auction.state

    elif request.method == "POST":
        if form.validate_on_submit():
            auction.state = form.state.data
            if auction.state == AuctionState.CONFIRMED:
                auction.auctioneer_id = current_user.user_id
                auction.confirmation_timestamp = datetime.datetime.now()
            elif auction.state == AuctionState.CLOSED:
                auction.end_date = datetime.datetime.now()
            elif auction.state == AuctionState.CREATED:
                auction.auctioneer_id = None
            elif auction.state == AuctionState.ACTIVE:
                auction.start_date = datetime.datetime.now()

            db.session.commit()
            return redirect(url_for("auction_management"))

    return render_template("auction/manageAuction.html", form=form, auction=auction)


@app.route("/editAuction/<string:auction_id>", methods=["GET", "POST"])
@login_required
def edit_auction(auction_id):
    auction = Auction.query.filter_by(auction_id=auction_id).first()
    form = AuctionForm()

    if request.method == 'GET':
        form.title.data = auction.title
        form.description.data = auction.description
        form.start_price.data = auction.start_price
        form.rules.data = auction.rules
        form.type.data = auction.type
        form.category.data = auction.category

    elif request.method == 'POST':
        if auction.state == AuctionState.CREATED:
            if form.validate_on_submit():
                if form.title.data:
                    auction.title = form.title.data
                if form.description.data:
                    auction.description = form.description.data
                if form.start_price.data:
                    auction.start_price = form.start_price.data
                if form.rules.data:
                    auction.rules = form.rules.data
                if form.type.data:
                    auction.type = form.type.data
                if form.category.data:
                    auction.category = form.category.data
                db.session.commit()
                flash("Aukcia upravená.")
                return redirect(url_for("my_auctions"))
        else:
            flash("Aukcia sa už nedá upraviť.")
            return redirect(url_for("my_auctions"))

    return render_template("auction/editAuction.html", form=form)


@app.route("/userManagement")
@roles_required(UserType.ADMIN)
def user_management():
    return render_template("admin/userManagement.html")


@app.route("/myAuctions")
@login_required
def my_auctions():
    return render_template("auction/auctionsOverview.html")


@app.route("/createAuction", methods=["GET", "POST"])
def create_auction():
    form = AuctionForm()
    if request.method == "POST" and current_user.is_authenticated:

        if form.validate_on_submit():
            auction = Auction(
                title=form.title.data,
                description=form.description.data,
                price=form.start_price.data,
                start_price=form.start_price.data,
                minimal_bid=form.minimal_bid.data,
                rules=form.rules.data,
                type=form.type.data,
                category=form.category.data,
                state=AuctionState.CREATED,
                creation_timestamp=datetime.datetime.now(),
                creator_id=current_user.user_id,
            )
            db.session.add(auction)
            db.session.commit()

            flash("Aukcia bola vytvorená.")
            if form.image.data:
                filename = secure_filename(
                    f"auction_image_{auction.auction_id}.{form.image.data.filename.rsplit('.')[-1]}")
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                form.image.data.save(file_path)
                auction.image = f"static/images/{filename}"
            else:
                auction.image = "static/images/placeholder.png"
            db.session.commit()
            return redirect(url_for("auction_detail", auction_id=auction.auction_id))

    return render_template("auction/createAuction.html", form=form)


@app.route("/admin/user/profile", methods=["GET", "POST"])
@roles_required(UserType.ADMIN)
def manage_user():
    form = UserManagementForm()

    # shows info about user and let's you edit it
    if request.method == "GET":
        id = request.args.get("id", type=int)
        if id:
            user = User.query.get(id)
            if user:
                form.type.data = user.type
                return render_template("admin/userManage.html", form=form, user=user)
            else:
                abort(404)

    elif request.method == "POST":
        id = request.args.get("id", type=int)
        user = User.query.get(id)
        if form.validate_on_submit():
            user.type = form.type.data
            if form.name.data:
                user.name = form.name.data
            if form.surname.data:
                user.surname = form.surname.data
            if form.email.data:
                user.email = form.email.data
            if form.phone.data:
                user.phone = form.phone.data
            if form.password.data:
                user.password = bcrypt.generate_password_hash(form.password.data)
            db.session.commit()
            return redirect(url_for("user_management"))

    return render_template("profile/profile.html")


@app.route("/api/data/editAuctions")
@login_required
def data_edit_auctions():
    return {
        "data": [auction.edit_to_dict() for auction in Auction.query.filter_by(creator_id=current_user.user_id).all()]}


@app.route("/api/data/bidAuctions")
@login_required
def data_bid_auctions():
    data = []
    auction_dict = {}
    regs = AuctionRegistration.query.filter_by(creator_id=current_user.user_id).all()
    for reg in regs:
        auction = Auction.query.get(reg.auction_id)
        if auction:
            auction_dict = auction.bid_to_dict()
        auction_dict["registration_state"] = reg.state.value
        data.append(auction_dict)

    return {"data": data }


@app.route("/api/data/joinedAuctions")
@login_required
def data_joined_auctions():
    return {
        "data": [auction.edit_to_dict() for auction in Auction.query.filter_by(creator_id=current_user.user_id).all()]
    }


@app.route("/api/data/manageAuctions")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def data_manage_auctions():
    return {"data": [auction.manage_to_dict() for auction in Auction.query.all() if
                     auction.creator_id != current_user.user_id and (
                             auction.auctioneer_id == current_user.user_id or auction.auctioneer_id is None)]}


@app.route("/api/data/manageRegistrations/<string:auction_id>")
@roles_required(UserType.ADMIN, UserType.AUCTIONEER)
def data_auction_registrations(auction_id):
    return {"data": [registration.registration_to_dict() for registration in
                     AuctionRegistration.query.filter_by(auction_id=auction_id).all() if
                     registration.state == AuctionRegistrationState.CREATED]}


@app.route("/api/data/users")
@roles_required(UserType.ADMIN)
def data_users():
    return {"data": [user.to_dict() for user in User.query.all()]}


@app.route("/api/data/auctions")
def data_auctions():
    data = []
    for auction in Auction.query.filter(Auction.state.in_([AuctionState.ACTIVE, AuctionState.CLOSED, AuctionState.CONFIRMED])).all():
        auction_dict = auction.view_auction_to_dict()
        auction_dict["register_link"] = None
        auction_dict["edit_link"] = None
        if not current_user.is_authenticated:
            auction_dict["registered"] = f'neregistrovaný'

        elif auction.auctioneer_id == current_user.user_id:
            auction_dict["registered"] = "licitátor"
            auction_dict["edit_link"] = f'/manageAuction/{auction.auction_id}'

        elif auction.creator_id == current_user.user_id:
            auction_dict["registered"] = "moja aukcia"
            auction_dict["edit_link"] = f'/editAuction/{auction.auction_id}'
        else:
            reg = AuctionRegistration.query.filter_by(auction_id=auction.auction_id,
                                                      creator_id=current_user.user_id).first()
            if not reg:
                auction_dict["register_link"] = f'/auctionDetail/{auction.auction_id}'
                auction_dict["registered"] = f'neregistrovaný'
            elif reg.state == AuctionRegistrationState.CREATED:
                auction_dict["register_link"] = f'/auctionDetail/{auction.auction_id}'
                auction_dict["registered"] = f'schvaľuje sa'
            elif reg.state == AuctionRegistrationState.FORBIDDEN:
                auction_dict["register_link"] = f'/auctionDetail/{auction.auction_id}'
                auction_dict["registered"] = f'zamietnutá'
            else:
                auction_dict["registered"] = f'registrovaný'
        data.append(auction_dict)

    return {"data": data}


@app.route("/auctionBid/<string:auction_id>", methods=["POST"])
@login_required
def auction_bid(auction_id):
    auction = Auction.query.get(auction_id)
    form = BidForm(auction=auction)

    if request.method == "POST":

        if form.validate_on_submit():
            if not current_user.is_registered_on_auction(auction_id):
                flash("Nie ste registrovaný na aukciu alebo vaša registrácia nebola schvalená.")
                return redirect(url_for("auction_detail", auction_id=auction_id))
            if auction.state != AuctionState.ACTIVE:
                flash("Aukcia nie je aktívna.")
                return redirect(url_for("auction_detail", auction_id=auction_id))

            price = form.price.data

            if auction.rules == AuctionRules.OPEN:
                bid = Bid(price=price,
                          timestamp=datetime.datetime.now(),
                          creator_id=current_user.user_id,
                          auction_id=auction.auction_id)

                db.session.add(bid)
                auction.price = price
                flash("Prihodenie prebehlo úspešne.")
                db.session.commit()
            elif auction.rules == AuctionRules.CLOSED and not auction.did_user_bid_on_closed(current_user):
                bid = Bid(price=price,
                          timestamp=datetime.datetime.now(),
                          creator_id=current_user.user_id,
                          auction_id=auction.auction_id)
                db.session.add(bid)
                auction.price = price
                flash("Prihodenie prebehlo úspešne.")
                db.session.commit()

        return redirect(url_for("auction_detail", auction_id=auction_id))

    else:
        abort(400)
