import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { AuthProvider } from '@/lib/auth-context'
import './globals.css'

const inter = Inter({
    subsets: ['latin'],
    display: 'swap',
    variable: '--font-inter',
})

export const metadata: Metadata = {
    title: 'InboxAI - AI Email Assistant',
    description: 'AI-powered email assistant with natural language commands. Manage your Gmail inbox through simple conversation.',
    keywords: ['email', 'AI', 'assistant', 'Gmail', 'productivity'],
    authors: [{ name: 'InboxAI' }],
    openGraph: {
        title: 'InboxAI - AI Email Assistant',
        description: 'Manage your Gmail inbox with natural language.',
        type: 'website',
    },
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className={inter.variable}>
            <body>
                <AuthProvider>
                    {children}
                </AuthProvider>
            </body>
        </html>
    )
}
