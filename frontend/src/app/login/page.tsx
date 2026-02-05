'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import styles from './page.module.css';

function LoginContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const error = searchParams.get('error');

    const errorMessages: Record<string, string> = {
        session_expired: 'Your session has expired. Please sign in again.',
        permission_revoked: 'Gmail access was revoked. Please sign in and grant permissions again.',
        auth_failed: 'Sign in failed. Please try again.',
        oauth_denied: 'You denied the permission request. Please try again.',
        missing_code: 'Authentication incomplete. Please try again.',
    };

    const message = error ? errorMessages[error] || 'An error occurred. Please try again.' : null;

    const handleRetry = () => {
        router.push('/');
    };

    return (
        <div className={styles.card}>
            <span className={styles.icon}>🔐</span>
            <h1 className={styles.title}>Sign In Required</h1>

            {message ? (
                <p className={styles.error}>{message}</p>
            ) : (
                <p className={styles.message}>Please sign in to access your email assistant.</p>
            )}

            <button className="btn btn-primary" onClick={handleRetry}>
                Go to Sign In
            </button>
        </div>
    );
}

export default function LoginPage() {
    return (
        <main className={styles.main}>
            <div className={styles.container}>
                <Suspense fallback={<div className={styles.card}>Loading...</div>}>
                    <LoginContent />
                </Suspense>
            </div>
        </main>
    );
}
