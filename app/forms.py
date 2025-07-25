from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, EqualTo, InputRequired, Email, ValidationError, Length


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(message="Введите пароль"),
        Length(min=8, message="Пароль должен содержать минимум 8 символов")
    ])
    confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message="Подтвердите пароль"),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    submit = SubmitField('Register')


class UploadForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Upload')


class EditTemplateForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Save')

class CreateExhibitionForm(FlaskForm):
    name = StringField('Название выставки', validators=[DataRequired()])
    templates = SelectMultipleField(
        'Выбранные макеты',
        coerce=int,
    )
    layouts = SelectMultipleField(
        'Выбранные Layouts',
        coerce=int,
    )
    submit = SubmitField('Создать выставку')

    def validate(self, extra_validators=None):
        rv = super(CreateExhibitionForm, self).validate(extra_validators=extra_validators)
        if not rv:
            return False
        if not (self.templates.data or self.layouts.data):
            msg = 'Выберите хотя бы один макет или Layout'
            self.templates.errors.append(msg)
            return False
        return True
