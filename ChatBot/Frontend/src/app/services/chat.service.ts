import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { HttpClient } from '@angular/common/http';

export interface ChatMessage {
    content: string;
    role: 'user' | 'assistant' | 'system';
    timestamp?: number;
    type?: 'text' | 'image' | 'sql' | 'error';
    imageUrl?: string;
    sqlQuery?: string;
}

@Injectable({
    providedIn: 'root'
})
export class ChatService {
    private socket: WebSocket | undefined;
    private messageSubject = new Subject<ChatMessage>();
    private statusSubject = new Subject<string>();
    private sessionIdSubject = new Subject<string>();

    private apiUrl = 'http://localhost:8000';
    private wsUrl = 'ws://localhost:8000/ws';
    private clientId = 'client-' + Math.random().toString(36).substr(2, 9);

    constructor(private http: HttpClient) {
        // Generate or retrieve session ID
        this.clientId = this.getSessionId();
        this.connect();
    }

    getSessionId(): string {
        let id = localStorage.getItem('chat_session_id');
        if (!id) {
            id = 'client-' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('chat_session_id', id);
        }
        return id;
    }

    setSessionId(id: string) {
        this.clientId = id;
        localStorage.setItem('chat_session_id', id);
        this.sessionIdSubject.next(id);
        if (this.socket) {
            this.socket.close();
        }
        this.connect();
    }

    getSessionIdObservable(): Observable<string> {
        return this.sessionIdSubject.asObservable();
    }

    createNewSession() {
        const id = 'client-' + Math.random().toString(36).substr(2, 9);
        this.setSessionId(id);
        return id;
    }

    private connect() {
        this.statusSubject.next('Connecting...');
        this.socket = new WebSocket(`${this.wsUrl}/${this.clientId}`);

        this.socket.onopen = (event) => {
            console.log('WebSocket Connected');
            this.statusSubject.next('Connected');
        };

        this.socket.onmessage = (event) => {
            const data = event.data;
            // Handle different message types if needed
            this.messageSubject.next({
                content: data,
                role: 'assistant',
                timestamp: Date.now()
            });
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket Closed', event);
            this.statusSubject.next('Disconnected');
            // Reconnect logic could go here
            // setTimeout(() => this.connect(), 5000); 
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket Error', error);
            this.statusSubject.next('Error');
        };
    }

    sendMessage(message: string) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(message);
        } else {
            console.error('WebSocket is not connected');
            // Fallback to HTTP for simple Q&A if WS fails? 
            // For now, retry connection
            this.connect();
        }
    }

    // HTTP fallback / Alternative for structured data
    askUnknown(question: string): Observable<any> {
        return this.http.post(`${this.apiUrl}/ask`, {
            session_id: this.clientId,
            question: question
        });
    }

    uploadImage(file: File): Observable<any> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post(`${this.apiUrl}/upload-image`, formData);
    }

    getMessages(): Observable<ChatMessage> {
        return this.messageSubject.asObservable();
    }

    getStatus(): Observable<string> {
        return this.statusSubject.asObservable();
    }

    getSessions(): Observable<any> {
        return this.http.get(`${this.apiUrl}/sessions`);
    }

    getHistory(sessionId: string): Observable<any> {
        return this.http.get(`${this.apiUrl}/memory/${sessionId}`);
    }

    deleteSession(sessionId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/memory/${sessionId}`);
    }

    private sessionsRefreshSubject = new Subject<void>();

    getSessionsRefreshObservable(): Observable<void> {
        return this.sessionsRefreshSubject.asObservable();
    }

    triggerSessionRefresh() {
        this.sessionsRefreshSubject.next();
    }
}
