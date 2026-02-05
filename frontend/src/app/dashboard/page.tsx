'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { chatApi, ApiError } from '@/lib/api';
import { ChatMessage, ChatResponse } from '@/types';
import ChatHeader from './components/ChatHeader';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import styles from './page.module.css';

/**
 * Dashboard - Main chat interface
 * 
 * UX Design:
 * - Clean, focused chat experience
 * - Messages flow naturally with timestamps
 * - Email cards for rich content display
 * - Confirmation prompts for dangerous actions
 * - Loading states for async operations
 */
export default function DashboardPage() {
    const { user, isLoading: authLoading, isAuthenticated, logout } = useAuth();
    const router = useRouter();

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Redirect if not authenticated
    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?error=auth_required');
        }
    }, [authLoading, isAuthenticated, router]);

    // Add welcome message on first load
    useEffect(() => {
        if (isAuthenticated && messages.length === 0) {
            const welcomeMessage: ChatMessage = {
                id: 'welcome',
                role: 'assistant',
                content: `Hello${user?.name ? `, ${user.name.split(' ')[0]}` : ''}! 👋 I'm your email assistant. Try saying:\n\n• "Show my emails"\n• "Reply to #1"\n• "Organize my inbox"`,
                type: 'text',
                timestamp: new Date(),
            };
            setMessages([welcomeMessage]);
        }
    }, [isAuthenticated, user, messages.length]);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    /**
     * Send a message to the chat API
     */
    const sendMessage = useCallback(async (content: string) => {
        if (!content.trim() || isLoading) return;

        // Add user message
        const userMessage: ChatMessage = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: content.trim(),
            type: 'text',
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);
        setError(null);

        try {
            // Call chat API
            const response = await chatApi.sendMessage(content);

            // Add assistant response
            const assistantMessage: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: response.message,
                type: response.type as ChatMessage['type'],
                data: response.data,
                pending_action: response.pending_action as ChatMessage['pending_action'],
                timestamp: new Date(),
            };

            setMessages(prev => [...prev, assistantMessage]);

        } catch (err) {
            const errorMessage = err instanceof ApiError
                ? err.message
                : 'Something went wrong. Please try again.';

            setError(errorMessage);

            // Add error message to chat
            const errorChatMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: 'assistant',
                content: errorMessage,
                type: 'error',
                timestamp: new Date(),
            };

            setMessages(prev => [...prev, errorChatMessage]);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading]);

    /**
     * Handle quick action buttons (confirm/cancel)
     */
    const handleQuickAction = useCallback((action: 'yes' | 'no') => {
        sendMessage(action);
    }, [sendMessage]);

    // Show loading while checking auth
    if (authLoading) {
        return (
            <main className={styles.main}>
                <div className={styles.loading}>
                    <div className={styles.spinner}></div>
                    <p>Loading...</p>
                </div>
            </main>
        );
    }

    // Don't render if not authenticated (will redirect)
    if (!isAuthenticated) {
        return null;
    }

    return (
        <main className={styles.main}>
            <div className={styles.container}>
                {/* Header with user info and logout */}
                <ChatHeader user={user} onLogout={logout} />

                {/* Message list */}
                <div className={styles.messagesContainer}>
                    <MessageList
                        messages={messages}
                        onQuickAction={handleQuickAction}
                        isActionLoading={isLoading}
                    />
                    <div ref={messagesEndRef} />

                    {/* Loading indicator */}
                    {isLoading && (
                        <div className={styles.typingIndicator}>
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    )}
                </div>

                {/* Input area */}
                <ChatInput
                    onSend={sendMessage}
                    disabled={isLoading}
                />
            </div>
        </main>
    );
}
