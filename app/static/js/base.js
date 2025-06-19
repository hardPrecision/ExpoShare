function showToast(message, type = 'default') {
    const toast = document.getElementById('toast-notification');
    const toastMessage = document.getElementById('toast-message');

    toastMessage.textContent = message;
    toast.className = 'toast-notification';
    if (type === 'success') toast.classList.add('success');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = JSON.parse('{{ get_flashed_messages() | tojson | safe }}');
    if (flashMessages?.length) {
        flashMessages.forEach(message => showToast(message, "success"));
    }
});