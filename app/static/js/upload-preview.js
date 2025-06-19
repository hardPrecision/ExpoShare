document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('exhibition_file');
    const previewContainer = document.getElementById('file-preview');

    if (!fileInput || !previewContainer) return;

    fileInput.addEventListener('change', function (event) {
        previewContainer.innerHTML = '';
        const file = event.target.files[0];
        if (!file) return;

        const ext = file.name.split('.').pop().toLowerCase();
        if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) {
            const img = document.createElement('img');
            img.classList.add('file-preview-image');
            img.src = URL.createObjectURL(file);
            previewContainer.appendChild(img);
        } else {
            const span = document.createElement('span');
            span.textContent = file.name;
            previewContainer.appendChild(span);
        }
    });
});
