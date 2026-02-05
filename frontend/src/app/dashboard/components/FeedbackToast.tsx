'use client';

import { useState, useEffect } from 'react';
import styles from './FeedbackToast.module.css';

export type ToastType = 'success' | 'error' | 'info';

interface FeedbackToastProps {
    message: string;
    type: ToastType;
    duration?: number;
    onClose: () => void;
}

/**
 * Feedback toast for showing success/error notifications
 * 
 * Auto-dismisses after duration
 */
export default function FeedbackToast({
    message,
    type,
    duration = 4000,
    onClose,
}: FeedbackToastProps) {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsVisible(false);
            setTimeout(onClose, 300); // Wait for exit animation
        }, duration);

        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
    };

    return (
        <div
            className={`${styles.toast} ${styles[type]} ${isVisible ? styles.visible : styles.hidden}`}
            role="alert"
        >
            <span className={styles.icon}>{icons[type]}</span>
            <span className={styles.message}>{message}</span>
            <button
                className={styles.close}
                onClick={() => {
                    setIsVisible(false);
                    setTimeout(onClose, 300);
                }}
                aria-label="Dismiss"
            >
                ×
            </button>
        </div>
    );
}

/**
 * Hook for managing toasts
 */
export function useToasts() {
    const [toasts, setToasts] = useState<Array<{
        id: string;
        message: string;
        type: ToastType;
    }>>([]);

    const showToast = (message: string, type: ToastType = 'info') => {
        const id = `toast-${Date.now()}`;
        setToasts(prev => [...prev, { id, message, type }]);
    };

    const removeToast = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    const showSuccess = (message: string) => showToast(message, 'success');
    const showError = (message: string) => showToast(message, 'error');
    const showInfo = (message: string) => showToast(message, 'info');

    return {
        toasts,
        showToast,
        showSuccess,
        showError,
        showInfo,
        removeToast,
    };
}
