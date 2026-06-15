<?php

namespace App\Events;

use App\Models\Inquiry;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;
use Illuminate\Broadcasting\InteractsWithSockets;

class InquiryCreated implements ShouldBroadcastNow
{
    use Dispatchable;
    use InteractsWithSockets;
    use SerializesModels;

    public Inquiry $inquiry;

    public function __construct(Inquiry $inquiry)
    {
        $this->inquiry = $inquiry->loadMissing('project');
    }

    public function broadcastOn(): array
    {
        $designerId = $this->inquiry->project?->designer_id;

        if (!$designerId) {
            return [];
        }

        return [new PrivateChannel('designer.' . $designerId)];
    }

    public function broadcastAs(): string
    {
        return 'inquiry.created';
    }

    public function broadcastWith(): array
    {
        return [
            'inquiry' => [
                'id' => $this->inquiry->id,
                'project_id' => $this->inquiry->project_id,
                'project_title' => $this->inquiry->project?->title,
                'client_id' => $this->inquiry->client_id,
                'visitor_name' => $this->inquiry->visitor_name,
                'visitor_email' => $this->inquiry->visitor_email,
                'message' => $this->inquiry->message,
                'status' => $this->inquiry->status,
                'created_at' => optional($this->inquiry->created_at)->toIso8601String(),
            ],
        ];
    }
}
