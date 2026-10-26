import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterModule, CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent {
  chatHistory: string[] = [];

  constructor(private chatService: ChatService, private router: Router) {
    this.loadSessions();

    // Listen for refresh triggers
    this.chatService.getSessionsRefreshObservable().subscribe(() => {
      this.loadSessions();
    });
  }

  loadSessions() {
    this.chatService.getSessions().subscribe({
      next: (data: any) => {
        if (data && data.sessions) {
          this.chatHistory = data.sessions;
        }
      },
      error: (err: any) => console.error(err)
    });
  }

  selectSession(sessionId: string) {
    this.chatService.setSessionId(sessionId);
    this.router.navigate(['/chat']);
  }

  createNewChat() {
    this.chatService.createNewSession();
    this.router.navigate(['/chat']);
  }

  deleteSession(event: Event, sessionId: string) {
    event.stopPropagation(); // Prevent selecting the session when clicking delete
    if (confirm('Voulez-vous vraiment supprimer cette conversation ?')) {
      this.chatService.deleteSession(sessionId).subscribe({
        next: () => {
          this.loadSessions();
          // If deleted session was active, switch to new one or first available
          if (sessionId === this.chatService.getSessionId()) {
            this.createNewChat();
          }
        },
        error: (err) => console.error('Error deleting session', err)
      });
    }
  }
}
