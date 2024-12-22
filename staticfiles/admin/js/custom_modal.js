function openCustomModal(objectId) {
    // Создаем и открываем модальное окно в стиле Unfold
    const url = `./custom-action/`;
    
    // Создаем модальное окно
    const modal = document.createElement('div');
    modal.id = 'customModal';
    modal.className = 'fixed z-50 inset-0 overflow-y-auto';
    modal.innerHTML = `
        <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div class="fixed inset-0 transition-opacity" aria-hidden="true">
                <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                <div id="modalContent" class="animate-pulse bg-gray-100 p-4">
                    Загрузка...
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Загружаем содержимое
    fetch(url)
        .then(response => response.text())
        .then(html => {
            document.getElementById('modalContent').innerHTML = html;
            document.getElementById('modalContent').classList.remove('animate-pulse', 'bg-gray-100');
        });
}

function closeCustomModal() {
    const modal = document.getElementById('customModal');
    if (modal) {
        modal.remove();
    }
}

function submitCustomAction(objectId) {
    fetch(`./custom-action/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            closeCustomModal();
            // Можно добавить обновление страницы или другие действия
        }
    });
}

// Функция для получения CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}