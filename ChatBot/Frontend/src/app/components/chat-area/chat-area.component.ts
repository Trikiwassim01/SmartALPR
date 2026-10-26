import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, ChatMessage } from '../../services/chat.service';
import { ImageUploadComponent } from '../shared/image-upload/image-upload.component';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-chat-area',
  standalone: true,
  imports: [CommonModule, FormsModule, ImageUploadComponent],
  templateUrl: './chat-area.component.html',
  styleUrl: './chat-area.component.css'
})
export class ChatAreaComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  messages: ChatMessage[] = [];
  inputValue = '';
  status = 'Disconnected';
  showUpload = false;

  private msgSub!: Subscription;
  private statusSub!: Subscription;
  private sessionSub!: Subscription;

  constructor(private chatService: ChatService) { }

  ngOnInit() {
    this.msgSub = this.chatService.getMessages().subscribe(msg => {
      this.messages.push(msg);
      this.scrollToBottom();
    });

    this.statusSub = this.chatService.getStatus().subscribe(s => this.status = s);

    // Initial load
    this.loadHistory(this.chatService.getSessionId());

    // Listen for session changes
    this.sessionSub = this.chatService.getSessionIdObservable().subscribe(sessionId => {
      this.messages = []; // Clear current messages
      this.loadHistory(sessionId);
    });
  }

  loadHistory(sessionId: string) {
    this.chatService.getHistory(sessionId).subscribe({
      next: (data: any) => {
        if (data && data.messages) {
          this.messages = data.messages.map((msg: any) => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            type: msg.type || 'text',
            imageUrl: msg.imageUrl // Fixed mapping
          }));
          setTimeout(() => this.scrollToBottom(), 100);
        }
      },
      error: (err) => console.error('Failed to load history', err)
    });
  }

  ngOnDestroy() {
    if (this.msgSub) this.msgSub.unsubscribe();
    if (this.statusSub) this.statusSub.unsubscribe();
    if (this.sessionSub) this.sessionSub.unsubscribe();
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch (err) { }
  }

  sendMessage() {
    if (!this.inputValue.trim()) return;

    const content = this.inputValue;
    this.inputValue = ''; // Clear input immediately

    // Add user message locally
    this.messages.push({
      role: 'user',
      content: content,
      timestamp: Date.now()
    });

    // Send to backend
    this.chatService.sendMessage(content);

    // Trigger session refresh (delay slightly to allow backend processing)
    setTimeout(() => this.chatService.triggerSessionRefresh(), 1000);
  }

  toggleUpload() {
    this.showUpload = !this.showUpload;
  }

  onUploadComplete(event: any) {
    this.showUpload = false;
    // Add image message locally
    this.messages.push({
      role: 'user',
      content: 'Image envoyée',
      type: 'image',
      imageUrl: event.preview,
      timestamp: Date.now()
    });

    // Note: The backend analysis response will come via WebSocket or we can trigger it
    // If upload-image endpoint just returns description, we might want to display it or send it as prompt context
    if (event.description) {
      this.chatService.sendMessage(`[CONTEXTE IMAGE] J'ai uploadé une image: ${event.description}. Peux-tu l'analyser ?`);
    }
  }
}
