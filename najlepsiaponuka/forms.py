import datetime

from flask_wtf import FlaskForm, file
from wtforms.fields import StringField, DecimalField, SelectField, IntegerField, DateTimeField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, StopValidation, Optional
from .models import User, AuctionType, AuctionRules, AuctionCategory, UserType, AuctionState
from flask_login import current_user
import phonenumbers
import email_validator
from . import bcrypt
from flask_uploads import IMAGES, UploadSet, secure_filename


def stop_validation_if_empty(form, field):
    if not field.data:
        field.errors[:] = []
        raise StopValidation()


class AuctionManageForm(FlaskForm):
    state = SelectField(label="Stav",
                        choices=AuctionState.choices(),
                        coerce=AuctionState.coerce)
    start_date = DateTimeField(label="Plánované začatie aukcie",
                               format='%d/%m/%Y %H:%M:%S',
                               validators=[
                                   Optional(),
                               ])

    def validate_start_date(self, start_date):
        if start_date.data:
            if start_date.data < datetime.datetime.now():
                raise ValidationError("Nemôže byť v minulosti.")


class AuctionForm(FlaskForm):
    start_price = DecimalField(label="Vyvolávacia cena",
                               default=0,
                               places=2,
                               validators=[
                                   DataRequired(),
                               ])

    minimal_bid = DecimalField(label="Minimálne navýšenie",
                               default=0.01,
                               places=2,
                              )

    title = StringField(label="Názov", validators=[

        DataRequired(),
        Length(min=3, max=50)
    ])

    description = StringField(label="Popis", validators=[
        stop_validation_if_empty,
        Length(min=10, max=255)
    ])

    rules = SelectField(label="Pravidlá",
                        choices=AuctionRules.choices(),
                        coerce=AuctionRules.coerce,
                        default=AuctionRules.OPEN)

    type = SelectField(label="Typ",
                       choices=AuctionType.choices(),
                       coerce=AuctionType.coerce,
                       default=AuctionType.OFFER)

    category = SelectField(label="Kategória",
                           choices=AuctionCategory.choices(),
                           coerce=AuctionCategory.coerce,
                           default=AuctionCategory.OTHERS)

    image = FileField(label='Obrázok', validators=[
        FileAllowed(['jpg','jpeg','png','gif'])
    ])


class RegistrationForm(FlaskForm):
    name = StringField(label='Meno', validators=[
        stop_validation_if_empty,
        Length(max=50),
    ])

    surname = StringField(label='Priezvisko', validators=[
        stop_validation_if_empty,
        Length(max=50),
    ])

    email = StringField(label='E-mail', validators=[
        DataRequired(),
        Length(min=3, max=254),
        # Email(message="Neplatný email.")
    ])

    phone = StringField('Tel. číslo')

    password = StringField(label='Heslo', validators=[
        DataRequired(),
        Length(min=6, max=50)
    ])

    password_confirm = StringField(label='Potvrdenie hesla', validators=[
        DataRequired(),
        Length(min=6, max=50),
        EqualTo('password', message='Heslá musia byť zhodné')
    ])

    def validate_phone(self, phone):
        message = "Neplatné telefonné číslo."
        if not phone:
            try:
                p = phonenumbers.parse(phone.data)
            except phonenumbers.phonenumberutil.NumberParseException:
                raise ValidationError(message)
            else:
                if not phonenumbers.is_valid_number(p):
                    raise ValidationError(message)

    def validate_email(self, email):
        message_bad_format = "Email je v zlom formáte."
        message_user_exists = "účet s týmto emailom už existuje."
        user = User.query.filter(User.email == email.data).first()
        try:
            valid = email_validator.validate_email(email.data)
            e = valid.email
        except email_validator.EmailNotValidError:
            # raise ValidationError(message_bad_format)
            pass
        else:
            if user:
                raise ValidationError(message_user_exists)


class LoginForm(FlaskForm):
    email = StringField(label='E-mail', validators=[
        DataRequired()
    ])
    password = StringField(label='Heslo', validators=[
        DataRequired()
    ])

    def validate_email(self, email):
        message_bad_format = "Email je v zlom formáte."
        message_no_email = "účet s týmto emailom neexistuje."
        user = User.query.filter(User.email == email.data).first()
        try:
            valid = email_validator.validate_email(email.data)
            e = valid.email
        except email_validator.EmailNotValidError:
            # raise ValidationError(message_bad_format)
            pass
        else:
            if not user:
                raise ValidationError(message_no_email)

    def validate_password(self, password):
        user = User.query.filter(User.email == self.email.data).first()
        message = "Heslo je nesprávne."
        if user:
            if not bcrypt.check_password_hash(user.password, password.data):
                raise ValidationError(message)


class UpdateForm(FlaskForm):
    name = StringField(label='Nové meno', validators=[
        stop_validation_if_empty,
        Length(max=50),
    ])

    surname = StringField(label='Nové priezvisko', validators=[
        stop_validation_if_empty,
        Length(max=50),
    ])

    email = StringField(label='Nový E-mail', validators=[
        stop_validation_if_empty,
        Length(min=3, max=254),
        Email(message="Neplatný email.")
    ])

    phone = StringField('Nové tel. číslo')

    password = StringField(label='Nové heslo', validators=[
        stop_validation_if_empty,
        Length(min=6, max=50)
    ])

    password_confirm = StringField(label='Aktuálne heslo', validators=[
        DataRequired(),
    ])

    def validate_password_confirm(self, password_confirm):
        message = "Nesprávne heslo."

        if not bcrypt.check_password_hash(current_user.password, password_confirm.data):
            raise ValidationError(message)

    def validate_phone(self, phone):
        message = "Neplatné telefonné číslo."
        try:
            p = phonenumbers.parse(phone.data)
        except phonenumbers.phonenumberutil.NumberParseException:
            # raise ValidationError(message)
            pass
        else:
            if not phonenumbers.is_valid_number(p):
                raise ValidationError(message)

    def validate_email(self, email):
        if email.data:
            message = "Email už bol použitý na registráciu."
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError(message)


class UserManagementForm(UpdateForm):
    type = SelectField(label="Typ",
                       choices=UserType.choices(),
                       coerce=UserType.coerce)

    password_confirm = StringField(label='Admin heslo', validators=[
        DataRequired(),
    ])


class BidForm(FlaskForm):
    price = DecimalField(label="Nová ponuka", places=2)

    def __init__(self, *args, auction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.auction = auction

    def validate_price(self, price, *args):
        if self.auction.type == AuctionType.OFFER:
            if not self.auction.has_bid():
                condition = price.data >= self.auction.price
            else:
                condition = price.data >= self.auction.price + self.auction.minimal_bid

            if not condition:
                raise ValidationError(
                    f"Minimálna výška prihodenia je {self.auction.minimal_bid}."
                )

        else:
            if not self.auction.has_bid():
                condition = price.data <= self.auction.price
            else:
                condition = price.data <= self.auction.price - self.auction.minimal_bid

            if not condition:
                raise ValidationError(
                    f"Minimálna výška sníženia je {self.auction.minimal_bid}."
                )

