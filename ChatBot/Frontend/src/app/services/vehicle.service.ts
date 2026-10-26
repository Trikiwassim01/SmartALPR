import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Vehicle {
    id?: number; // matricule is usually key, but let's check
    matricule: string;
    modele: string;
    image_voiture?: string;
    client_id: number;
}

@Injectable({
    providedIn: 'root'
})
export class VehicleService {
    private apiUrl = 'http://localhost:8000/voitures';

    constructor(private http: HttpClient) { }

    getVehicles(): Observable<Vehicle[]> {
        return this.http.get<Vehicle[]>(this.apiUrl);
    }

    getVehiclebyClient(clientId: number): Observable<Vehicle[]> {
        // Assuming backend supports filtering or we filter frontend
        // Ideally: GET /voitures/?client_id=X
        return this.http.get<Vehicle[]>(`${this.apiUrl}/?client_id=${clientId}`);
    }

    createVehicle(vehicle: Vehicle): Observable<Vehicle> {
        return this.http.post<Vehicle>(this.apiUrl, vehicle);
    }

    analyzePlate(image: File): Observable<any> {
        const formData = new FormData();
        formData.append('file', image);
        // Note: The backend endpoint is defined in routes/voitures.py with prefix /voitures
        // so it should be available at /voitures/analyze-plate
        // Assuming this.apiUrl is http://localhost:8000/voitures
        return this.http.post<any>(`${this.apiUrl}/analyze-plate`, formData);
    }

    getVehicleHistory(matricule: string): Observable<any[]> {
        return this.http.get<any[]>(`${this.apiUrl}/${matricule}/historiques`);
    }
}
