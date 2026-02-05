'use client';

import Image from 'next/image';
import { User } from '@/types';
import styles from './ChatHeader.module.css';

interface ChatHeaderProps {
    user: User | null;
    onLogout: () => void;
}

/**
 * Header component with app logo, user info, and logout
 */
export default function ChatHeader({ user, onLogout }: ChatHeaderProps) {
    return (
        <header className={styles.header}>
            <div className={styles.brand}>
                <span className={styles.logo}>📬</span>
                <h1 className={styles.title}>InboxAI</h1>
            </div>

            <div className={styles.userSection}>
                {user && (
                    <>
                        <div className={styles.userInfo}>
                            <span className={styles.userName}>{user.name}</span>
                            <span className={styles.userEmail}>{user.email}</span>
                        </div>

                        {user.picture ? (
                            <Image
                                src={user.picture}
                                alt={user.name || 'User'}
                                width={40}
                                height={40}
                                className={styles.avatar}
                            />
                        ) : (
                            <div className={styles.avatarPlaceholder}>
                                {(user.name || user.email || 'U')[0].toUpperCase()}
                            </div>
                        )}
                    </>
                )}

                <button
                    className={styles.logoutButton}
                    onClick={onLogout}
                    title="Logout"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                        <polyline points="16,17 21,12 16,7" />
                        <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                </button>
            </div>
        </header>
    );
}
