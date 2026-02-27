/**
 * Toast Notification System & Confirmation Modal
 * A beautiful, reusable notification and confirmation system for the application
 */

// Confirmation Modal System
function showConfirm(message, title = 'Xác nhận', options = {}) {
    return new Promise((resolve) => {
        // Default options
        const defaultOptions = {
            confirmText: 'Xác nhận',
            cancelText: 'Hủy',
            type: 'warning', // warning, danger, info
            confirmClass: 'btn-primary',
            cancelClass: 'btn-outline'
        };
        
        const opts = { ...defaultOptions, ...options };
        
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.className = 'confirm-modal-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.2s;
        `;
        
        // Create modal dialog
        const modal = document.createElement('div');
        modal.className = 'confirm-modal';
        modal.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 0;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            transform: scale(0.9);
            transition: transform 0.2s;
        `;
        
        // Icon based on type
        const icons = {
            warning: { icon: '⚠️', color: '#f59e0b' },
            danger: { icon: '🗑️', color: '#ef4444' },
            info: { icon: 'ℹ️', color: '#3b82f6' }
        };
        
        const iconData = icons[opts.type] || icons.warning;
        
        modal.innerHTML = `
            <div style="padding: 24px; text-align: center;">
                <div style="font-size: 48px; margin-bottom: 16px;">${iconData.icon}</div>
                <h3 style="margin: 0 0 12px 0; font-size: 20px; font-weight: 600; color: #1f2937;">${title}</h3>
                <p style="margin: 0; font-size: 14px; color: #6b7280; line-height: 1.5;">${message}</p>
            </div>
            <div style="display: flex; gap: 12px; padding: 16px 24px; background: #f9fafb; border-top: 1px solid #e5e7eb; border-radius: 0 0 12px 12px;">
                <button class="confirm-cancel-btn" style="
                    flex: 1;
                    padding: 10px 20px;
                    border: 1px solid #d1d5db;
                    background: white;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    color: #374151;
                    cursor: pointer;
                    transition: all 0.2s;
                ">${opts.cancelText}</button>
                <button class="confirm-ok-btn" style="
                    flex: 1;
                    padding: 10px 20px;
                    border: none;
                    background: ${opts.type === 'danger' ? '#ef4444' : '#3b82f6'};
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    color: white;
                    cursor: pointer;
                    transition: all 0.2s;
                ">${opts.confirmText}</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        // Trigger animation
        setTimeout(() => {
            overlay.style.opacity = '1';
            modal.style.transform = 'scale(1)';
        }, 10);
        
        // Handle button clicks
        const closeModal = (confirmed) => {
            overlay.style.opacity = '0';
            modal.style.transform = 'scale(0.9)';
            setTimeout(() => {
                overlay.remove();
                resolve(confirmed);
            }, 200);
        };
        
        modal.querySelector('.confirm-ok-btn').onclick = () => closeModal(true);
        modal.querySelector('.confirm-cancel-btn').onclick = () => closeModal(false);
        overlay.onclick = (e) => {
            if (e.target === overlay) closeModal(false);
        };
        
        // Handle ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal(false);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        
        // Add hover effects
        const cancelBtn = modal.querySelector('.confirm-cancel-btn');
        const okBtn = modal.querySelector('.confirm-ok-btn');
        
        cancelBtn.onmouseover = () => cancelBtn.style.background = '#f3f4f6';
        cancelBtn.onmouseout = () => cancelBtn.style.background = 'white';
        
        okBtn.onmouseover = () => okBtn.style.background = opts.type === 'danger' ? '#dc2626' : '#2563eb';
        okBtn.onmouseout = () => okBtn.style.background = opts.type === 'danger' ? '#ef4444' : '#3b82f6';
    });
}

// Toast notification system
function showToast(message, type = 'success', duration = 4000) {
    // Create container if it doesn't exist
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Icon based on type
    const icons = {
        success: '✓',
        error: '✕',
        info: 'i',
        warning: '⚠'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-content">
            <p class="toast-message">${message}</p>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Ensure styles are loaded
if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        /* Toast Notification Styles */
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        }

        .toast {
            background: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            transform: translateX(450px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            border-left: 4px solid;
            min-width: 300px;
        }

        .toast.show {
            transform: translateX(0);
            opacity: 1;
        }

        .toast.success {
            border-left-color: #10b981;
        }

        .toast.error {
            border-left-color: #ef4444;
        }

        .toast.info {
            border-left-color: #3b82f6;
        }

        .toast.warning {
            border-left-color: #f59e0b;
        }

        .toast-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 14px;
        }

        .toast.success .toast-icon {
            background: #d1fae5;
            color: #10b981;
        }

        .toast.error .toast-icon {
            background: #fee2e2;
            color: #ef4444;
        }

        .toast.info .toast-icon {
            background: #dbeafe;
            color: #3b82f6;
        }

        .toast.warning .toast-icon {
            background: #fef3c7;
            color: #f59e0b;
        }

        .toast-content {
            flex: 1;
        }

        .toast-message {
            margin: 0;
            font-size: 14px;
            font-weight: 500;
            color: #1f2937;
            line-height: 1.4;
        }

        .toast-close {
            background: none;
            border: none;
            color: #9ca3af;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .toast-close:hover {
            background: #f3f4f6;
            color: #4b5563;
        }

        @media (max-width: 768px) {
            .toast-container {
                right: 10px;
                left: 10px;
                max-width: none;
            }
            
            .toast {
                min-width: auto;
            }
        }
    `;
    document.head.appendChild(style);
}
