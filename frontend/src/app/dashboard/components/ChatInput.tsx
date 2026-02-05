'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import styles from './ChatInput.module.css';

interface ChatInputProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

/**
 * Chat input component with send button
 * 
 * Features:
 * - Auto-grow textarea
 * - Enter to send, Shift+Enter for newline
 * - Send button with loading state
 * - Placeholder suggestions
 */
export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
    const [value, setValue] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        }
    }, [value]);

    // Focus input on mount
    useEffect(() => {
        textareaRef.current?.focus();
    }, []);

    const handleSend = () => {
        if (!value.trim() || disabled) return;

        onSend(value.trim());
        setValue('');

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        // Enter to send, Shift+Enter for newline
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const placeholders = [
        'Show my emails...',
        'Reply to #1...',
        'Delete the spam...',
        'Organize my inbox...',
        'What\'s important today?',
    ];

    const [placeholder, setPlaceholder] = useState(placeholders[0]);

    // Rotate placeholder suggestions
    useEffect(() => {
        const interval = setInterval(() => {
            setPlaceholder(prev => {
                const currentIndex = placeholders.indexOf(prev);
                return placeholders[(currentIndex + 1) % placeholders.length];
            });
        }, 4000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className={styles.container}>
            <div className={styles.inputWrapper}>
                <textarea
                    ref={textareaRef}
                    className={styles.textarea}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    disabled={disabled}
                    rows={1}
                />

                <button
                    className={styles.sendButton}
                    onClick={handleSend}
                    disabled={!value.trim() || disabled}
                    title="Send message (Enter)"
                >
                    {disabled ? (
                        <span className={styles.spinner}></span>
                    ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <path
                                d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                        </svg>
                    )}
                </button>
            </div>

            <p className={styles.hint}>
                Press <kbd>Enter</kbd> to send, <kbd>Shift + Enter</kbd> for new line
            </p>
        </div>
    );
}
