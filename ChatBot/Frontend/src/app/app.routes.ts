import { Routes } from '@angular/router';
import { ChatAreaComponent } from './components/chat-area/chat-area.component';
import { ClientsComponent } from './components/clients/clients.component';
import { VehiclesComponent } from './components/vehicles/vehicles.component';
import { InvoicesComponent } from './components/invoices/invoices.component';

export const routes: Routes = [
    { path: '', redirectTo: 'chat', pathMatch: 'full' },
    { path: 'chat', component: ChatAreaComponent },
    { path: 'clients', component: ClientsComponent },
    { path: 'vehicles', component: VehiclesComponent },
    { path: 'invoices', component: InvoicesComponent },
];
