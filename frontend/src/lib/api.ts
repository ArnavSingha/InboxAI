/**
 * API client for InboxAI backend.
 * 
 * This module provides typed API calls to the FastAPI backend,
 * handles authentication via cookies, and manages error states.
 */
import { ChatResponse, User } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
    code: string;
    status: number;

    constructor(message: string, code: string = 'UNKNOWN', status: number = 500) {
        super(message);
        this.code = code;
        this.status = status;
        this.name = 'ApiError';
    }
}

/**
 * Fetch wrapper with credentials and error handling.
 * 
 * - Includes cookies for session auth
 * - Handles 401 by redirecting to login
 * - Parses error responses
 */
async function fetchApi<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_URL}${endpoint}`;

    try {
        const response = await fetch(url, {
            ...options,
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        // Handle auth errors - redirect to login
        if (response.status === 401) {
            if (typeof window !== 'undefined') {
                window.location.href = '/login?error=session_expired';
            }
            throw new ApiError('Session expired', 'SESSION_EXPIRED', 401);
        }

        // Parse error responses
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                message: 'An error occurred',
                code: 'UNKNOWN',
            }));

            throw new ApiError(
                errorData.message || errorData.detail?.message || 'Request failed',
                errorData.code || errorData.detail?.code || 'UNKNOWN',
                response.status
            );
        }

        // Handle empty responses
        if (response.status === 204) {
            return {} as T;
        }

        return response.json();
    } catch (error) {
        // Re-throw ApiError as-is
        if (error instanceof ApiError) {
            throw error;
        }

        // Handle network errors
        console.error('API request failed:', error);
        throw new ApiError('Unable to connect to server', 'NETWORK_ERROR', 0);
    }
}

// =============================================================================
// AUTH API
// =============================================================================

export const authApi = {
    /**
     * Get Google OAuth login URL
     */
    getLoginUrl: () =>
        fetchApi<{ auth_url: string }>('/api/auth/login'),

    /**
     * Check current session status
     */
    getSession: () =>
        fetchApi<{ authenticated: boolean; email?: string; name?: string }>('/api/auth/session'),

    /**
     * Logout and clear session
     */
    logout: () =>
        fetchApi<{ success: boolean }>('/api/auth/logout', {
            method: 'POST',
        }),

    /**
     * Refresh session token
     */
    refresh: () =>
        fetchApi<{ refreshed: boolean; valid: boolean }>('/api/auth/refresh'),
};

// =============================================================================
// USER API
// =============================================================================

export const userApi = {
    /**
     * Get current user profile
     */
    getProfile: () =>
        fetchApi<User>('/api/user'),
};

// =============================================================================
// CHAT API
// =============================================================================

export const chatApi = {
    /**
     * Send a chat message and get AI response
     * 
     * @param message - Natural language input
     * @returns ChatResponse with message, type, data, pending_action
     */
    sendMessage: (message: string) =>
        fetchApi<ChatResponse>('/api/chat', {
            method: 'POST',
            body: JSON.stringify({ message }),
        }),

    /**
     * Get current chat state (pending actions, cached emails)
     */
    getStatus: () =>
        fetchApi<{
            pending_action: string | null;
            has_pending: boolean;
            cached_email_count: number;
        }>('/api/chat/status'),

    /**
     * Clear pending action without executing
     */
    clearPending: () =>
        fetchApi<{ success: boolean }>('/api/chat/pending', {
            method: 'DELETE',
        }),
};

// =============================================================================
// HEALTH API
// =============================================================================

export const healthApi = {
    /**
     * Check if backend is healthy
     */
    check: () =>
        fetchApi<{ status: string; timestamp: string; version: string }>('/api/health'),
};
