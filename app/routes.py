from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Template, Exhibition, ExhibitionItem, Layout
from app.forms import *
from werkzeug.utils import secure_filename
import os
import shutil
import secrets
import qrcode
from datetime import datetime

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
    layouts = Layout.query.filter_by(user_id=current_user.id).order_by(Layout.created_at.desc()).all()
    return render_template('dashboard.html', templates=templates, layouts=layouts)


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        files_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'files', current_user.uuid)
        os.makedirs(files_dir, exist_ok=True)
        file_path = os.path.join(files_dir, filename)
        f.save(file_path)

        rel_path = f"files/{current_user.uuid}/{filename}"
        template = Template(
            name=form.name.data,
            filename=rel_path,
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
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

            filename = secure_filename(form.file.data.filename)
            files_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'files', current_user.uuid)
            os.makedirs(files_dir, exist_ok=True)
            form.file.data.save(os.path.join(files_dir, filename))
            template.filename = f"files/{current_user.uuid}/{filename}"

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


@bp.route('/layout/<int:layout_id>/view')
@login_required
def view_layout(layout_id):
    layout = Layout.query.get_or_404(layout_id)
    if layout.user_id != current_user.id:
        return redirect(url_for('main.dashboard'))
    # Render editor template in preview-only mode
    return render_template('editor.html', layout=layout, view_mode=True)


@bp.route('/editor/save', methods=['POST'])
@login_required
def save_layout():
    data = request.get_json() or {}
    # Determine layout name, content, and file extension
    name = data.get('name', f'Layout {datetime.utcnow().strftime("%Y%m%d%H%M%S")}')
    content = data.get('content', '')
    ext = 'html' if data.get('mode') == 'html' else 'md'
    layout_id = data.get('id')
    # Prevent duplicate names
    conflict = Layout.query.filter_by(user_id=current_user.id, name=name)
    if layout_id:
        layout = Layout.query.get_or_404(layout_id)
        if layout.user_id != current_user.id:
            return {'success': False, 'error': 'Forbidden'}, 403
        if conflict.first() and conflict.first().id != layout.id:
            return {'success': False, 'error': 'Duplicate name'}
        # Update record and overwrite file
        layout.name = name
        layout.content = content
        safe = secure_filename(name)
        filename = f"{layout.id}_{safe}.{ext}" if safe else f"{layout.id}.{ext}"
        layouts_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'layouts', current_user.uuid)
        file_path = os.path.join(layouts_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        layout.filename = filename
        db.session.commit()
        return {'success': True, 'id': layout.id, 'name': layout.name}
    # New layout creation
    if conflict.first():
        return {'success': False, 'error': 'Duplicate name'}
    layout = Layout(name=name, filename='', content=content, user_id=current_user.id)
    db.session.add(layout)
    db.session.commit()
    safe = secure_filename(name)
    filename = f"{layout.id}_{safe}.{ext}" if safe else f"{layout.id}.{ext}"
    layouts_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'layouts', current_user.uuid)
    os.makedirs(layouts_dir, exist_ok=True)
    file_path = os.path.join(layouts_dir, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    layout.filename = filename
    db.session.commit()
    return {'success': True, 'id': layout.id, 'name': layout.name}


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

    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', current_user.uuid)
    os.makedirs(qr_dir, exist_ok=True)
    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    img.save(qr_path)

    return qr_filename


@bp.route('/create_exhibition', methods=['GET', 'POST'])
@login_required
def create_exhibition():
    form = CreateExhibitionForm()
    user_templates = Template.query.filter_by(user_id=current_user.id).all()
    user_layouts = Layout.query.filter_by(user_id=current_user.id).all()
    form.templates.choices = [(t.id, t.name) for t in user_templates]
    form.layouts.choices = [(l.id, l.name) for l in user_layouts]

    if form.validate_on_submit():
        selected_templates = Template.query.filter(Template.id.in_(form.templates.data)).all()
        selected_layouts = Layout.query.filter(Layout.id.in_(form.layouts.data)).all()

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

        exhibition_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'exhibitions', current_user.uuid, str(exhibition.id))
        os.makedirs(exhibition_dir, exist_ok=True)

        for template in selected_templates:
            src_path = os.path.join(current_app.config['UPLOAD_FOLDER'], template.filename)
            dst_filename = os.path.basename(template.filename)
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

        # add layout items
        for layout in selected_layouts:
            # copy layout file into exhibition folder
            src = os.path.join(current_app.config['UPLOAD_FOLDER'], 'layouts', current_user.uuid, layout.filename)
            dst = os.path.join(exhibition_dir, layout.filename)
            shutil.copy2(src, dst)
            item = ExhibitionItem(
                exhibition_id=exhibition.id,
                original_template_id=None,
                name=layout.name,
                filename=layout.filename,
                description=''  # or layout.content preview
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

    user = User.query.get(exhibition.user_id)
    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', user.uuid)
    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)

    items = []
    for item in exhibition.items:
        item_data = {'id': item.id, 'name': item.name, 'description': item.description, 'filename': item.filename}
        # add animation settings for layout items
        anim_type = anim_timing = anim_duration = ''
        if item.original_template_id is None:
            layout = Layout.query.filter_by(filename=item.filename, user_id=exhibition.user_id).first()
            if layout:
                anim_type = layout.anim_type or ''
                anim_timing = layout.anim_timing or ''
                anim_duration = layout.anim_duration or ''
        item_data['anim_type'] = anim_type
        item_data['anim_timing'] = anim_timing
        item_data['anim_duration'] = anim_duration
        items.append(item_data)

    return render_template(
        'exhibition.html',
        exhibition=exhibition,
        items=items,
        qr_filename=f"qrcodes/{user.uuid}/{qr_filename}",
        user_uuid=user.uuid
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

    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', current_user.uuid)
    qr_filename = f"{exhibition.id}_qr.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    if os.path.exists(qr_path):
        os.remove(qr_path)

    exhibition_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'exhibitions', current_user.uuid, str(exhibition.id))
    if os.path.exists(exhibition_dir):
        shutil.rmtree(exhibition_dir)

    db.session.delete(exhibition)
    db.session.commit()
    flash('Выставка удалена')
    return redirect(url_for('main.manage_exhibitions'))


@bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# Route to upload images pasted or dropped in the editor
@bp.route('/editor/upload_image', methods=['POST'])
@login_required
def upload_image():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify(success=False, error='No file provided'), 400
    # Generate secure, unique filename
    original = secure_filename(file.filename)
    unique = secrets.token_hex(8)
    filename = f"{unique}_{original}"
    images_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', current_user.uuid)
    os.makedirs(images_dir, exist_ok=True)
    file_path = os.path.join(images_dir, filename)
    file.save(file_path)
    url = url_for('main.serve_image', user_uuid=current_user.uuid, filename=filename)
    return jsonify(success=True, url=url)


# Route to serve uploaded images
@bp.route('/images/<user_uuid>/<filename>')
@login_required
def serve_image(user_uuid, filename):
    if user_uuid != current_user.uuid:
        abort(403)
    images_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', user_uuid)
    return send_from_directory(images_dir, filename)