import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ClientService, Client } from '../../services/client.service';

@Component({
    selector: 'app-clients',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './clients.component.html',
    styleUrls: ['./clients.component.css']
})
export class ClientsComponent implements OnInit {
    clients: Client[] = [];
    loading = true;
    error = '';

    constructor(private clientService: ClientService) { }

    ngOnInit() {
        this.loadClients();
    }

    loadClients() {
        this.loading = true;
        this.clientService.getClients().subscribe({
            next: (data) => {
                this.clients = data;
                this.loading = false;
            },
            error: (err) => {
                this.error = 'Erreur lors du chargement des clients';
                this.loading = false;
                console.error(err);
            }
        });
    }

    deleteClient(id: number) {
        if (confirm('Êtes-vous sûr de vouloir supprimer ce client ?')) {
            this.clientService.deleteClient(id).subscribe(() => {
                this.loadClients(); // Refresh list
            });
        }
    }
}
