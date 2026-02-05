'use client';

import { ChatMessage } from '@/types';
import MessageBubble from './MessageBubble';
import EmailCard from './EmailCard';
import ConfirmationCard from './ConfirmationCard';
import styles from './MessageList.module.css';

interface MessageListProps {
    messages: ChatMessage[];
    onQuickAction: (action: 'yes' | 'no') => void;
    isActionLoading?: boolean;
}

/**
 * Message list component that renders different message types
 * 
 * Message Types:
 * - text: Simple text bubble
 * - emails: Email cards with summaries
 * - draft: Reply preview with enhanced confirmation
 * - confirmation: Delete confirmation with enhanced card
 * - categories: Grouped email list
 * - digest: Daily digest summary
 * - error: Error message styling
 */
export default function MessageList({
    messages,
    onQuickAction,
    isActionLoading = false,
}: MessageListProps) {
    // Find if there's a pending action in recent messages
    const pendingMessage = messages.findLast(m => m.pending_action);

    return (
        <div className={styles.list}>
            {messages.map((message) => (
                <div
                    key={message.id}
                    className={`${styles.messageWrapper} ${message.role === 'user' ? styles.user : styles.assistant
                        }`}
                >
                    {/* Email list display */}
                    {message.type === 'emails' && message.data ? (
                        <div className={styles.emailsContainer}>
                            <MessageBubble message={message} />
                            <div className={styles.emailCards}>
                                {(message.data as any[]).map((email, idx) => (
                                    <EmailCard key={email.id || idx} email={email} />
                                ))}
                            </div>
                        </div>
                    ) : /* Send confirmation */ message.type === 'draft' && message.pending_action ? (
                        <div className={styles.confirmationContainer}>
                            <ConfirmationCard
                                type="send"
                                emailInfo={{
                                    sender_name: (message.data as any)?.to?.split('@')[0] || 'Recipient',
                                    sender_email: (message.data as any)?.to,
                                    subject: (message.data as any)?.subject?.replace('Re: ', ''),
                                }}
                                draftBody={(message.data as any)?.body}
                                onConfirm={() => onQuickAction('yes')}
                                onCancel={() => onQuickAction('no')}
                                isLoading={isActionLoading && message.id === pendingMessage?.id}
                            />
                        </div>
                    ) : /* Delete confirmation */ message.type === 'confirmation' && message.pending_action ? (
                        <div className={styles.confirmationContainer}>
                            <ConfirmationCard
                                type="delete"
                                emailInfo={parseEmailFromMessage(message.content)}
                                onConfirm={() => onQuickAction('yes')}
                                onCancel={() => onQuickAction('no')}
                                isLoading={isActionLoading && message.id === pendingMessage?.id}
                            />
                        </div>
                    ) : /* Categories display */ message.type === 'categories' && message.data ? (
                        <div className={styles.categoriesContainer}>
                            <MessageBubble message={message} />
                            {(message.data as any[]).map((category, idx) => (
                                <div key={idx} className={styles.categoryGroup}>
                                    <h4 className={styles.categoryTitle}>
                                        {category.category} ({category.count})
                                    </h4>
                                    <div className={styles.categoryEmails}>
                                        {category.emails?.slice(0, 3).map((email: any, emailIdx: number) => (
                                            <EmailCard key={emailIdx} email={email} compact />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : /* Digest display */ message.type === 'digest' && message.data ? (
                        <div className={styles.digestContainer}>
                            <MessageBubble message={message} />
                            {(message.data as any).suggested_actions?.length > 0 && (
                                <div className={styles.digestActions}>
                                    <h5>Suggested Actions:</h5>
                                    <ul>
                                        {(message.data as any).suggested_actions.map((action: string, idx: number) => (
                                            <li key={idx}>{action}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Default text/error bubble */
                        <MessageBubble message={message} />
                    )}
                </div>
            ))}
        </div>
    );
}

/**
 * Parse email info from confirmation message content
 * Expected format: "**From:** Name <email>\n**Subject:** subject"
 */
function parseEmailFromMessage(content: string): { sender_name?: string; sender_email?: string; subject?: string } {
    const fromMatch = content.match(/\*\*From:\*\*\s*([^<\n]+)(?:<([^>]+)>)?/);
    const subjectMatch = content.match(/\*\*Subject:\*\*\s*(.+)/);

    return {
        sender_name: fromMatch?.[1]?.trim(),
        sender_email: fromMatch?.[2]?.trim(),
        subject: subjectMatch?.[1]?.trim(),
    };
}
