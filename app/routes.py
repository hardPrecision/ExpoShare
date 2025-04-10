from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Template, Exhibition, ExhibitionItem
from app.forms import *
from werkzeug.utils import secure_filename
import os
import shutil
import secrets
import qrcode

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


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
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(0)
        if current_user.total_size + file_size > current_app.config['USER_FILE_LIMIT']:
            flash(f"Превышен лимит хранилища", "danger")
            return render_template('upload.html', form=form)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        f.save(file_path)

        template = Template(
            name=form.name.data,
            filename=filename,
            file_size=file_size,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(template)
        current_user.total_size += file_size
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

    current_user.total_size -= template.file_size
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

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
            form.file.data.seek(0, os.SEEK_END)
            new_file_size = form.file.data.tell()
            form.file.data.seek(0)
            old_filename = template.filename
            old_file_size = template.file_size
            new_total_size = current_user.total_size - old_file_size + new_file_size
            if new_total_size > current_app.config['USER_FILE_LIMIT']:
                flash("Превышен лимит хранилища", "danger")
                return render_template('edit.html', form=form, template=template)
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            filename = secure_filename(form.file.data.filename)
            form.file.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            template.filename = filename
            template.file_size = new_file_size

            current_user.total_size = new_total_size

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


def generate_qr(exhibition):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(exhibition.public_url)  # Используем внешний URL
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(current_app.config['QR_CODE_DIR'], qr_filename)
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)

    return qr_filename

@bp.route('/create_exhibition', methods=['GET', 'POST'])
@login_required
def create_exhibition():
    form = CreateExhibitionForm()
    user_templates = Template.query.filter_by(user_id=current_user.id).all()
    form.templates.choices = [(t.id, t.name) for t in user_templates]

    if form.validate_on_submit():
        selected_templates = Template.query.filter(Template.id.in_(form.templates.data)).all()

        url_key = secrets.token_hex(16)
        while Exhibition.query.filter_by(url_key=url_key).first():
            url_key = secrets.token_hex(16)

        exhibition = Exhibition(
            name=form.name.data,
            user_id=current_user.id,
            url_key=url_key
        )
        db.session.add(exhibition)
        db.session.commit()

        exhibition.qr_filename = generate_qr(exhibition)
        db.session.commit()

        exhibition_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'exhibitions', str(exhibition.id))
        os.makedirs(exhibition_dir, exist_ok=True)

        for template in selected_templates:
            src_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.filename)
            dst_filename = template.filename
            dst_path = os.path.join(exhibition_dir, dst_filename)

            shutil.copy2(src_path, dst_path)

            item = ExhibitionItem(
                exhibition_id=exhibition.id,
                original_template_id=template.id,
                name=template.name,
                filename=dst_filename,
                description=template.description
            )
            db.session.add(item)

        db.session.commit()
        return redirect(url_for('main.manage_exhibitions', url_key=url_key))

    return render_template('create_exhibition.html', form=form)

@bp.route('/exhibition/<url_key>')
def view_exhibition(url_key):
    exhibition = Exhibition.query.filter_by(url_key=url_key).first_or_404()

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(request.url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(current_app.config['QR_CODE_DIR'], qr_filename)
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)

    items = [
        {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'filename': item.filename
        }
        for item in exhibition.items
    ]

    return render_template(
        'exhibition.html',
        exhibition=exhibition,
        items=items,
        qr_filename=qr_filename
    )


@bp.route('/manage_exhibitions')
@login_required
def manage_exhibitions():
    exhibitions = Exhibition.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_exhibitions.html', exhibitions=exhibitions)


@bp.route('/delete_exhibition/<int:exhibition_id>', methods=['POST'])
@login_required
def delete_exhibition(exhibition_id):
    exhibition = Exhibition.query.get_or_404(exhibition_id)
    if exhibition.user_id != current_user.id:
        return "Forbidden", 403

    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(current_app.config['QR_CODE_DIR'], qr_filename)
    if os.path.exists(qr_path):
        os.remove(qr_path)

    exhibition_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'exhibitions', str(exhibition.id))
    if os.path.exists(exhibition_dir):
        shutil.rmtree(exhibition_dir)

    db.session.delete(exhibition)
    db.session.commit()
    flash('Выставка удалена')
    return redirect(url_for('main.manage_exhibitions'))