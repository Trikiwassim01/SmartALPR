import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatService } from '../../../services/chat.service';

@Component({
    selector: 'app-image-upload',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './image-upload.component.html',
    styleUrls: ['./image-upload.component.css']
})
export class ImageUploadComponent {
    @Output() uploadComplete = new EventEmitter<any>();
    selectedFile: File | null = null;
    previewUrl: string | null = null;
    isUploading = false;

    constructor(private chatService: ChatService) { }

    onFileSelected(event: any) {
        const file = event.target.files[0];
        if (file) {
            this.selectedFile = file;

            // Create preview
            const reader = new FileReader();
            reader.onload = () => {
                this.previewUrl = reader.result as string;
            };
            reader.readAsDataURL(file);
        }
    }

    upload() {
        if (!this.selectedFile) return;

        this.isUploading = true;
        this.chatService.uploadImage(this.selectedFile).subscribe({
            next: (response) => {
                this.isUploading = false;
                this.uploadComplete.emit({ ...response, preview: this.previewUrl });
                this.clear();
            },
            error: (err) => {
                console.error(err);
                this.isUploading = false;
            }
        });
    }

    clear() {
        this.selectedFile = null;
        this.previewUrl = null;
    }
}
