from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Template
from app.forms import *
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


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.')
    return redirect(url_for('main.index'))


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
            name=form.name.data,
            filename=filename,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    return render_template('upload.html', form=form)


@bp.route('/delete/<int:template_id>', methods=['GET'])
@login_required
def delete_template(template_id):
    template = Template.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You are not allowed to delete this template.')
        return redirect(url_for('main.dashboard'))
    db.session.delete(template)
    db.session.commit()
    flash('Template deleted successfully.')
    return redirect(url_for('main.dashboard'))


@bp.route('/publish/<int:template_id>', methods=['GET'])
@login_required
def publish_template(template_id):
    template = Template.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('You are not allowed to publish this template.')
        return redirect(url_for('main.dashboard'))
    template.is_public = True
    db.session.commit()
    flash('Template published successfully.')
    return redirect(url_for('main.dashboard'))


@bp.route('/edit_template/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    template = Template.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash("У вас нет прав...", "danger")
        return redirect(url_for('main.dashboard'))

    form = EditTemplateForm()

    if form.validate_on_submit():
        template.name = form.name.data
        template.description = form.description.data

        if form.file.data:
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            filename = secure_filename(form.file.data.filename)
            form.file.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            template.filename = filename

        db.session.commit()
        flash("Макет обновлен!", "success")
        return redirect(url_for('main.dashboard'))
    form.name.data = template.name
    form.description.data = template.description

    return render_template('edit.html', form=form, template=template)


@bp.route('/editor')
@login_required
def editor():
    return render_template('editor.html', message="Здесь будет реализован редактор")

