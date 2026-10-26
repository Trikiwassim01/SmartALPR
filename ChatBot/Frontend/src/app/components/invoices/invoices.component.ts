import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { InvoiceService, InvoiceRequest } from '../../services/invoice.service';
import { ClientService, Client } from '../../services/client.service';
import { VehicleService, Vehicle } from '../../services/vehicle.service';

@Component({
    selector: 'app-invoices',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './invoices.component.html',
    styleUrls: ['./invoices.component.css']
})
export class InvoicesComponent {
    historyList: any[] = [];
    selectedHistory: any = null;
    selectedHistoriqueId: number | null = null;

    selectedClientId: number | null = null;
    selectedVehicleMatricule: string | null = null;

    vehicleInfo: any = null;
    clientInfo: any = null;

    loadingHistory = false;
    generating = false;

    generatedUrl: SafeResourceUrl | null = null;
    generatedTotal: number = 0;
    invoiceNumber: string = '';

    clients: Client[] = [];
    vehicles: Vehicle[] = [];

    constructor(
        private invoiceService: InvoiceService,
        private clientService: ClientService,
        private vehicleService: VehicleService,
        private route: ActivatedRoute,
        private sanitizer: DomSanitizer
    ) { }

    ngOnInit() {
        this.route.queryParams.subscribe((params: any) => {
            if (params['clientId'] && params['vehicleMatricule']) {
                this.selectedClientId = +params['clientId'];
                this.selectedVehicleMatricule = params['vehicleMatricule'];

                // Charger les infos et l'historique
                this.loadHistory();
            }
        });
    }

    loadHistory() {
        if (!this.selectedVehicleMatricule || !this.selectedClientId) return;

        // Charger info client
        this.clientService.getClients().subscribe(clients => {
            this.clientInfo = clients.find(c => c.id === this.selectedClientId);
        });

        // Charger info véhicule
        this.vehicleService.getVehiclebyClient(this.selectedClientId).subscribe(vehicles => {
            this.vehicleInfo = vehicles.find(v => v.matricule === this.selectedVehicleMatricule);
        });

        // Charger historique
        this.loadingHistory = true;
        this.vehicleService.getVehicleHistory(this.selectedVehicleMatricule).subscribe({
            next: (history: any[]) => {
                this.historyList = history;
                this.loadingHistory = false;

                // Auto-sélectionner la dernière intervention
                if (history && history.length > 0) {
                    this.selectedHistory = history[0];
                    this.selectedHistoriqueId = history[0].id;
                }
            },
            error: (err) => {
                console.error('Error loading history', err);
                this.loadingHistory = false;
                this.historyList = [];
            }
        });
    }

    generate() {
        if (!this.selectedHistoriqueId) {
            alert('Aucune intervention sélectionnée');
            return;
        }

        this.generating = true;
        const request: InvoiceRequest = {
            historique_id: this.selectedHistoriqueId
        };

        this.invoiceService.generateInvoice(request).subscribe({
            next: (res) => {
                this.generatedUrl = this.sanitizer.bypassSecurityTrustResourceUrl(`http://localhost:8000${res.url}`);
                this.generatedTotal = res.total;
                this.invoiceNumber = res.invoice_number || '';
                this.generating = false;
            },
            error: (err) => {
                console.error('Erreur génération facture:', err);
                alert('Erreur lors de la génération de la facture. Voir console.');
                this.generating = false;
            }
        });
    }
}
