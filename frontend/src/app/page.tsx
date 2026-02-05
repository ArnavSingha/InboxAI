'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import styles from './page.module.css';

/**
 * Landing Page - Entry point for unauthenticated users
 * 
 * Auth Flow:
 * 1. User clicks "Sign in with Google"
 * 2. Frontend calls GET /api/auth/login to get OAuth URL
 * 3. Frontend redirects to Google consent screen
 * 4. User grants permissions
 * 5. Google redirects to backend /api/auth/callback
 * 6. Backend exchanges code for tokens, creates session
 * 7. Backend sets HTTP-only session cookie
 * 8. Backend redirects to /dashboard
 * 9. Dashboard loads and displays chat interface
 */
export default function LandingPage() {
    const { isAuthenticated, isLoading, login } = useAuth();
    const router = useRouter();
    const [isRedirecting, setIsRedirecting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Redirect authenticated users to dashboard
    useEffect(() => {
        if (!isLoading && isAuthenticated) {
            router.push('/dashboard');
        }
    }, [isLoading, isAuthenticated, router]);

    const handleLogin = async () => {
        setIsRedirecting(true);
        setError(null);

        try {
            await login();
        } catch (err) {
            setError('Failed to start login. Please try again.');
            setIsRedirecting(false);
        }
    };

    // Show loading while checking auth
    if (isLoading) {
        return (
            <main className={styles.main}>
                <div className={styles.loadingContainer}>
                    <div className={styles.spinner}></div>
                </div>
            </main>
        );
    }

    return (
        <main className={styles.main}>
            <div className={styles.container}>
                {/* Hero section */}
                <div className={styles.hero}>
                    <div className={styles.logoContainer}>
                        <span className={styles.logoIcon}>📬</span>
                        <h1 className={styles.logo}>InboxAI</h1>
                    </div>

                    <p className={styles.tagline}>
                        Your AI-powered email assistant
                    </p>

                    <p className={styles.description}>
                        Manage your Gmail inbox with natural language. Read emails, draft replies,
                        and organize your inbox — all through simple conversation.
                    </p>

                    {error && (
                        <div className={styles.error}>
                            {error}
                        </div>
                    )}

                    <button
                        className={`btn btn-google ${styles.loginButton}`}
                        onClick={handleLogin}
                        disabled={isRedirecting}
                    >
                        {isRedirecting ? (
                            <span className={styles.spinner}></span>
                        ) : (
                            <>
                                <svg width="20" height="20" viewBox="0 0 24 24">
                                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                                Sign in with Google
                            </>
                        )}
                    </button>

                    <p className={styles.permissions}>
                        We'll request access to read, send, and manage your Gmail.
                    </p>
                </div>

                {/* Features section */}
                <div className={styles.features}>
                    <div className={styles.feature}>
                        <span className={styles.featureIcon}>💬</span>
                        <h3>Natural Language</h3>
                        <p>Just type what you want. "Show my emails" or "Reply to John."</p>
                    </div>

                    <div className={styles.feature}>
                        <span className={styles.featureIcon}>🤖</span>
                        <h3>AI Summaries</h3>
                        <p>Get AI-generated summaries of your emails instantly.</p>
                    </div>

                    <div className={styles.feature}>
                        <span className={styles.featureIcon}>📊</span>
                        <h3>Smart Organization</h3>
                        <p>Categorize your inbox and get daily digests.</p>
                    </div>
                </div>
            </div>
        </main>
    );
}
