/**
 * TypeScript types for the InboxAI application.
 */

// User types
export interface User {
    email: string;
    name: string;
    picture?: string;
}

// Email types
export interface EmailSummary {
    id: string;
    index: number;
    sender_name: string;
    sender_email: string;
    subject: string;
    summary: string;
    date: string;
}

export interface CategoryGroup {
    category: string;
    emails: EmailSummary[];
    count: number;
}

export interface DigestSummary {
    summary: string;
    key_emails: EmailSummary[];
    suggested_actions: string[];
}

export interface DraftReply {
    email_id: string;
    to: string;
    subject: string;
    body: string;
}

// Chat types
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    type: 'text' | 'emails' | 'categories' | 'digest' | 'draft' | 'confirmation' | 'error';
    data?: EmailSummary[] | CategoryGroup[] | DigestSummary | DraftReply | null;
    pending_action?: 'send' | 'delete' | null;
    timestamp: Date;
}

export interface ChatRequest {
    message: string;
}

export interface ChatResponse {
    message: string;
    type: 'text' | 'emails' | 'categories' | 'digest' | 'draft' | 'confirmation' | 'error';
    data?: EmailSummary[] | CategoryGroup[] | DigestSummary | DraftReply | null;
    pending_action?: 'send' | 'delete' | null;
}

// API types
export interface ApiError {
    error: boolean;
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

// Auth types
export interface AuthResponse {
    auth_url: string;
}
