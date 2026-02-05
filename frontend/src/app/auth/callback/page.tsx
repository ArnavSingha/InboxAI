'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';

export default function AuthCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        // The backend handles the OAuth callback and sets the cookie.
        // If we land here, something went wrong or we need to wait.
        // The backend should redirect to /dashboard on success.

        // If we're still on this page after a few seconds, redirect to login
        const timeout = setTimeout(() => {
            router.push('/login?error=auth_failed');
        }, 5000);

        return () => clearTimeout(timeout);
    }, [router]);

    return (
        <main className={styles.main}>
            <div className={styles.container}>
                <div className={styles.loader}></div>
                <p className={styles.message}>Completing sign in...</p>
            </div>
        </main>
    );
}
