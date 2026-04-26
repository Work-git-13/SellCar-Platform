
// Загрузка информации о пользователе
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user');
        const userInfo = await response.json();
        
        if (userInfo.authenticated) {
            // ВАЖНАЯ СТРОКА: сохраняем данные в глобальную переменную
            window.currentUser = userInfo; 

            document.querySelectorAll('.user-name').forEach(element => {
                let userName = userInfo.first_name;
                if (userInfo.last_name) {
                    userName += ' ' + userInfo.last_name;
                }
                element.textContent = userName;
            });
            
            document.querySelectorAll('.user-avatar').forEach(avatar => {
                if (userInfo.avatar_url) {
                    avatar.src = userInfo.avatar_url;
                }
            });
            
            return userInfo;
        }
        return null;
    } catch (error) {
        console.error('Error loading user info:', error);
        return null;
    }
}

// Функция для выхода из системы
async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            // Ждем чуть-чуть, чтобы кука удалилась, и переходим на логин
            setTimeout(() => {
                window.location.reload();
            }, 100);
        }
    } catch (error) {
        console.error('Ошибка выхода:', error);
    }
}

// Показать уведомление
function showNotification(message, isSuccess = true) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        max-width: 300px;
        background-color: ${isSuccess ? '#10b981' : '#ef4444'};
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 4000);
}

// Инициализация на всех страницах
document.addEventListener('DOMContentLoaded', function() {
    loadUserInfo();
    
    // Добавляем обработчик для кнопки выхода
    document.querySelectorAll('.logout-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
});