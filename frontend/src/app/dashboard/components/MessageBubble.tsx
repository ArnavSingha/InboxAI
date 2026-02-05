'use client';

import { ChatMessage } from '@/types';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
    message: ChatMessage;
}

/**
 * Individual message bubble component
 * 
 * Handles:
 * - User vs assistant styling
 * - Error message styling
 * - Markdown-like formatting for bold, newlines
 */
export default function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user';
    const isError = message.type === 'error';

    // Format message content with basic markdown
    const formatContent = (content: string) => {
        return content
            .split('\n')
            .map((line, i) => (
                <span key={i}>
                    {line.split(/(\*\*[^*]+\*\*)/).map((part, j) => {
                        if (part.startsWith('**') && part.endsWith('**')) {
                            return <strong key={j}>{part.slice(2, -2)}</strong>;
                        }
                        return part;
                    })}
                    {i < content.split('\n').length - 1 && <br />}
                </span>
            ));
    };

    // Format timestamp
    const formatTime = (date: Date) => {
        return new Intl.DateTimeFormat('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        }).format(date);
    };

    return (
        <div
            className={`${styles.bubble} ${isUser ? styles.user : styles.assistant} ${isError ? styles.error : ''}`}
        >
            <div className={styles.content}>
                {formatContent(message.content)}
            </div>
            <span className={styles.timestamp}>
                {formatTime(message.timestamp)}
            </span>
        </div>
    );
}
