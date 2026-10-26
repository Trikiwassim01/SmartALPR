import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface InvoiceItem {
    description: string;
    amount: number;
}

export interface InvoiceRequest {
    historique_id: number;
}

@Injectable({
    providedIn: 'root'
})
export class InvoiceService {
    private apiUrl = 'http://localhost:8000';

    constructor(private http: HttpClient) { }

    generateInvoice(request: InvoiceRequest): Observable<any> {
        return this.http.post(`${this.apiUrl}/generate-invoice`, request);
    }
}
