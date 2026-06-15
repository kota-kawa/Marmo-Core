<?php

namespace App\Livewire;

use Livewire\Component;
use App\Models\Ticket;
use Livewire\WithPagination;

class StaffDashboard extends Component
{
    use WithPagination;

    public $search = '';
    public $statusFilter = '';

    public function updateStatus($ticketId, $newStatus)
    {
        $ticket = Ticket::find($ticketId);
        if ($ticket) {
            $ticket->update(['status' => $newStatus]);
            session()->flash('success', 'Status tiket berhasil diperbarui!');
        }
    }

    public function updatedSearch()
    {
        $this->resetPage();
    }

    public function updatedStatusFilter()
    {
        $this->resetPage();
    }

    public function render()
    {
        $query = Ticket::query()->with('category')->latest();

        if ($this->search) {
            $query->where(function($q) {
                $q->where('guest_name', 'like', '%' . $this->search . '%')
                  ->orWhere('guest_nim', 'like', '%' . $this->search . '%')
                  ->orWhere('title', 'like', '%' . $this->search . '%');
            });
        }

        if ($this->statusFilter) {
            $query->where('status', $this->statusFilter);
        }

        $tickets = $query->paginate(10);

        return view('livewire.staff-dashboard', [
            'tickets' => $tickets
        ])->layout('components.layouts.staff');
    }
}
