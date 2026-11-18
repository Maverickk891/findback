/**
 * FindBack Main Application Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mark notifications as read when clicking the notification trigger
    const notifDropdown = document.getElementById('notifDropdown');
    const notifBadge = document.getElementById('notifBadge');
    
    if (notifDropdown && notifBadge) {
        notifDropdown.addEventListener('show.bs.dropdown', () => {
            fetch('/api/notifications/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    notifBadge.style.display = 'none';
                }
            }).catch(err => console.error('Notification error:', err));
        });
    }

    // 2. Client-side Image Upload Preview
    const photoInput = document.getElementById('photoInput');
    const photoPreview = document.getElementById('photoPreview');
    const photoPreviewContainer = document.getElementById('photoPreviewContainer');

    if (photoInput && photoPreview && photoPreviewContainer) {
        photoInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    photoPreview.src = e.target.result;
                    photoPreviewContainer.classList.remove('d-none');
                }
                reader.readAsDataURL(file);
            } else {
                photoPreviewContainer.classList.add('d-none');
            }
        });
    }

    // 3. Print QR Code Action
    const printQrBtn = document.getElementById('printQrBtn');
    if (printQrBtn) {
        printQrBtn.addEventListener('click', () => {
            window.print();
        });
    }
});
