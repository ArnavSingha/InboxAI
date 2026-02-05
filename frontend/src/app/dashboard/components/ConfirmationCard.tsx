'use client';

import styles from './ConfirmationCard.module.css';

interface ConfirmationCardProps {
    type: 'send' | 'delete';
    emailInfo: {
        sender_name?: string;
        sender_email?: string;
        subject?: string;
    };
    draftBody?: string;
    onConfirm: () => void;
    onCancel: () => void;
    isLoading?: boolean;
}

/**
 * Enhanced Confirmation Card for destructive/important actions
 * 
 * Shows clear context and requires explicit user confirmation
 */
export default function ConfirmationCard({
    type,
    emailInfo,
    draftBody,
    onConfirm,
    onCancel,
    isLoading = false,
}: ConfirmationCardProps) {
    const isSend = type === 'send';
    const isDelete = type === 'delete';

    return (
        <div className={`${styles.card} ${isDelete ? styles.danger : styles.primary}`}>
            {/* Header with icon */}
            <div className={styles.header}>
                <span className={styles.icon}>
                    {isSend ? '✉️' : '🗑️'}
                </span>
                <h4 className={styles.title}>
                    {isSend ? 'Send this reply?' : 'Delete this email?'}
                </h4>
            </div>

            {/* Email context */}
            <div className={styles.context}>
                <div className={styles.recipient}>
                    <span className={styles.label}>
                        {isSend ? 'To:' : 'From:'}
                    </span>
                    <span className={styles.value}>
                        {emailInfo.sender_name || 'Unknown'}
                        {emailInfo.sender_email && (
                            <span className={styles.email}> &lt;{emailInfo.sender_email}&gt;</span>
                        )}
                    </span>
                </div>

                {emailInfo.subject && (
                    <div className={styles.subject}>
                        <span className={styles.label}>Subject:</span>
                        <span className={styles.value}>
                            {isSend ? `Re: ${emailInfo.subject}` : emailInfo.subject}
                        </span>
                    </div>
                )}
            </div>

            {/* Draft preview for send */}
            {isSend && draftBody && (
                <div className={styles.preview}>
                    <div className={styles.previewLabel}>Message:</div>
                    <div className={styles.previewContent}>{draftBody}</div>
                </div>
            )}

            {/* Warning for delete */}
            {isDelete && (
                <div className={styles.warning}>
                    <span className={styles.warningIcon}>⚠️</span>
                    <span>This email will be moved to trash.</span>
                </div>
            )}

            {/* Action buttons */}
            <div className={styles.actions}>
                <button
                    className={`${styles.button} ${styles.cancel}`}
                    onClick={onCancel}
                    disabled={isLoading}
                >
                    Cancel
                </button>
                <button
                    className={`${styles.button} ${isSend ? styles.confirm : styles.delete}`}
                    onClick={onConfirm}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <span className={styles.spinner}></span>
                    ) : (
                        <>
                            {isSend ? '✓ Send' : '🗑️ Delete'}
                        </>
                    )}
                </button>
            </div>

            {/* Keyboard hint */}
            <p className={styles.hint}>
                Type <kbd>yes</kbd> to confirm or <kbd>no</kbd> to cancel
            </p>
        </div>
    );
}
