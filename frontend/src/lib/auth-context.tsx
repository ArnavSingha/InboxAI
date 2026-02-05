/**
 * Authentication Context for InboxAI
 * 
 * Provides auth state across the app:
 * - user: Current user object (null if not logged in)
 * - isLoading: True during initial session check
 * - isAuthenticated: Boolean shorthand
 * - login: Redirect to OAuth
 * - logout: Clear session and redirect
 * - checkSession: Re-verify session status
 */
'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, userApi, ApiError } from '@/lib/api';
import { User } from '@/types';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: () => Promise<void>;
    logout: () => Promise<void>;
    checkSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    /**
     * Check current session and load user profile
     */
    const checkSession = useCallback(async () => {
        try {
            const session = await authApi.getSession();

            if (session.authenticated) {
                // Fetch full user profile
                const profile = await userApi.getProfile();
                setUser(profile);
            } else {
                setUser(null);
            }
        } catch (error) {
            // Session check failed - user not authenticated
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    /**
     * Initiate Google OAuth login
     */
    const login = useCallback(async () => {
        try {
            const { auth_url } = await authApi.getLoginUrl();
            window.location.href = auth_url;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }, []);

    /**
     * Logout and redirect to home
     */
    const logout = useCallback(async () => {
        try {
            await authApi.logout();
        } catch (error) {
            // Ignore logout errors - clear state anyway
            console.error('Logout error:', error);
        } finally {
            setUser(null);
            window.location.href = '/';
        }
    }, []);

    // Check session on mount
    useEffect(() => {
        checkSession();
    }, [checkSession]);

    const value: AuthContextType = {
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        checkSession,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

/**
 * Hook to use auth context
 */
export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

/**
 * Higher-order component for protected routes
 */
export function withAuth<P extends object>(
    Component: React.ComponentType<P>
): React.FC<P> {
    return function AuthenticatedComponent(props: P) {
        const { isAuthenticated, isLoading } = useAuth();

        useEffect(() => {
            if (!isLoading && !isAuthenticated) {
                window.location.href = '/login?error=auth_required';
            }
        }, [isLoading, isAuthenticated]);

        if (isLoading) {
            return (
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100vh'
                }}>
                    <div className="spinner" />
                </div>
            );
        }

        if (!isAuthenticated) {
            return null;
        }

        return <Component {...props} />;
    };
}
