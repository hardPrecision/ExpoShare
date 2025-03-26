from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Template
from app.forms import LoginForm, RegistrationForm, UploadForm
from werkzeug.utils import secure_filename
import os

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    public_templates = Template.query.filter_by(is_public=True).all()
    return render_template('index.html', templates=public_templates)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)


@bp.route('/dashboard')
@login_required
def dashboard():
    templates = Template.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', templates=templates)


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        f.save(file_path)

        template = Template(
            filename=filename,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    return render_template('upload.html', form=form)