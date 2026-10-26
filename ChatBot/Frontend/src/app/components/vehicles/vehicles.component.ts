import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { VehicleService, Vehicle } from '../../services/vehicle.service';
import { ClientService, Client } from '../../services/client.service';
import { ImageUploadComponent } from '../shared/image-upload/image-upload.component';

@Component({
    selector: 'app-vehicles',
    standalone: true,
    imports: [CommonModule, FormsModule, ImageUploadComponent],
    templateUrl: './vehicles.component.html',
    styleUrls: ['./vehicles.component.css']
})
export class VehiclesComponent implements OnInit {
    vehicles: Vehicle[] = [];
    clients: Client[] = [];
    loading = true;
    loadingClients = false;
    error = '';

    // Modal & Form State
    showAddModal = false;
    isAnalyzing = false;
    isSaving = false;
    modalError = '';
    confidence = 0;

    newVehicle: Vehicle = {
        matricule: '',
        modele: '',
        client_id: 0,
        image_voiture: ''
    };

    selectedImagePreview: string | null = null;

    constructor(
        private vehicleService: VehicleService,
        private clientService: ClientService,
        private router: Router
    ) { }

    ngOnInit() {
        this.loadVehicles();
    }

    // ... (rest of methods)

    navigateToInvoice(vehicle: any) {
        this.router.navigate(['/invoices'], {
            queryParams: {
                clientId: vehicle.client_id,
                vehicleMatricule: vehicle.matricule
            }
        });
    }

    loadVehicles() {
        this.loading = true;
        this.vehicleService.getVehicles().subscribe({
            next: (data) => {
                this.vehicles = data;
                this.loading = false;
            },
            error: (err) => {
                this.error = 'Erreur lors du chargement des véhicules';
                this.loading = false;
                console.error(err);
            }
        });
    }

    openAddModal() {
        this.showAddModal = true;
        this.resetForm();
        this.loadClients();
    }

    loadClients() {
        this.loadingClients = true;
        this.clientService.getClients().subscribe({
            next: (data) => {
                this.clients = data;
                this.loadingClients = false;
            },
            error: (err) => {
                console.error('Error loading clients', err);
                this.loadingClients = false;
            }
        });
    }

    closeAddModal() {
        this.showAddModal = false;
    }

    resetForm() {
        this.newVehicle = { matricule: '', modele: '', client_id: 0, image_voiture: '' };
        this.confidence = 0;
        this.modalError = '';
        this.selectedImagePreview = null;
    }

    // Called when file input changes
    analyzeImage(event: any) {
        const file = event.target.files[0];
        if (!file) return;

        // Create preview
        const reader = new FileReader();
        reader.onload = () => {
            this.selectedImagePreview = reader.result as string;
        };
        reader.readAsDataURL(file);

        this.isAnalyzing = true;
        this.vehicleService.analyzePlate(file).subscribe({
            next: (data) => {
                this.isAnalyzing = false;
                if (data.plate_detected) {
                    this.newVehicle.matricule = data.plate_text;
                    this.confidence = data.yolo_confidence || 0;
                } else {
                    this.modalError = 'Aucune plaque détectée: ' + data.reason;
                }
            },
            error: (err) => {
                this.isAnalyzing = false;
                this.modalError = 'Erreur lors de l\'analyse de l\'image';
                console.error(err);
            }
        });
    }

    saveVehicle() {
        this.isSaving = true;
        this.vehicleService.createVehicle(this.newVehicle).subscribe({
            next: (v) => {
                this.isSaving = false;
                this.vehicles.push(v);
                this.closeAddModal();
            },
            error: (err) => {
                this.isSaving = false;
                this.modalError = 'Erreur lors de la sauvegarde';
                console.error(err);
            }
        });
    }

    // History Modal State
    showHistoryModal = false;
    selectedVehicleHistory: any[] = [];
    selectedVehicleForHistory: Vehicle | null = null;
    loadingHistory = false;

    openHistoryModal(vehicle: Vehicle) {
        this.selectedVehicleForHistory = vehicle;
        this.showHistoryModal = true;
        this.loadingHistory = true;
        this.selectedVehicleHistory = [];

        this.vehicleService.getVehicleHistory(vehicle.matricule).subscribe({
            next: (data) => {
                this.selectedVehicleHistory = data;
                this.loadingHistory = false;
            },
            error: (err) => {
                console.error('Error loading history', err);
                this.loadingHistory = false;
            }
        });
    }

    closeHistoryModal() {
        this.showHistoryModal = false;
        this.selectedVehicleHistory = [];
        this.selectedVehicleForHistory = null;
    }
}
