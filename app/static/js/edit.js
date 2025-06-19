document.getElementById('exhibition_file').addEventListener('change', function(event) {
    const previewContainer = document.getElementById('file-preview');
    previewContainer.innerHTML = '';
    const file = event.target.files[0];
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) {
        const img = document.createElement('img');
        img.className = 'file-preview-image';
        img.src = URL.createObjectURL(file);
        previewContainer.appendChild(img);
    } else {
        const span = document.createElement('span');
        span.textContent = file.name;
        previewContainer.appendChild(span);
    }
});