'use client';

import styles from './EmailCard.module.css';

interface EmailCardProps {
    email: {
        id: string;
        index: number;
        sender_name: string;
        sender_email: string;
        subject: string;
        summary: string;
        date: string;
    };
    compact?: boolean;
}

/**
 * Email card component for displaying email summaries
 */
export default function EmailCard({ email, compact = false }: EmailCardProps) {
    // Format date for display
    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

            if (diffDays === 0) {
                return new Intl.DateTimeFormat('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true,
                }).format(date);
            } else if (diffDays === 1) {
                return 'Yesterday';
            } else if (diffDays < 7) {
                return new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date);
            } else {
                return new Intl.DateTimeFormat('en-US', {
                    month: 'short',
                    day: 'numeric',
                }).format(date);
            }
        } catch {
            return dateStr;
        }
    };

    if (compact) {
        return (
            <div className={styles.compactCard}>
                <span className={styles.compactIndex}>#{email.index}</span>
                <span className={styles.compactSender}>{email.sender_name}</span>
                <span className={styles.compactSubject}>{email.subject}</span>
            </div>
        );
    }

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <span className={styles.index}>#{email.index}</span>
                <span className={styles.date}>{formatDate(email.date)}</span>
            </div>

            <div className={styles.sender}>
                <span className={styles.senderName}>{email.sender_name}</span>
                <span className={styles.senderEmail}>{email.sender_email}</span>
            </div>

            <div className={styles.subject}>{email.subject}</div>

            <div className={styles.summary}>{email.summary}</div>

            <div className={styles.actions}>
                <button className={styles.actionHint}>
                    Say "reply to #{email.index}" to respond
                </button>
            </div>
        </div>
    );
}
