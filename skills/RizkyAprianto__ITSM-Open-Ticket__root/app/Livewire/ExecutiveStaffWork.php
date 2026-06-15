<?php

namespace App\Livewire;

use Livewire\Component;
use Livewire\WithPagination;
use App\Models\Ticket;

class ExecutiveStaffWork extends Component
{
    use WithPagination;

    public $statusFilter = '';
    public $search = '';

    public function updatedSearch()
    {
        $this->resetPage();
    }

    public function render()
    {
        $query = Ticket::with('category')->orderBy('updated_at', 'desc');

        if ($this->statusFilter) {
            $query->where('status', $this->statusFilter);
        }

        if ($this->search) {
            $query->where(function($q) {
                $q->where('title', 'like', '%' . $this->search . '%')
                  ->orWhere('guest_name', 'like', '%' . $this->search . '%')
                  ->orWhere('guest_nim', 'like', '%' . $this->search . '%')
                  ->orWhere('uuid', 'like', '%' . $this->search . '%');
            });
        }

        $tickets = $query->paginate(15);

        return view('livewire.executive-staff-work', [
            'tickets' => $tickets
        ])->layout('components.layouts.executive');
    }
}
