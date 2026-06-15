import { useState } from 'react';
import { ArrowRight, Twitter, AlertCircle } from 'lucide-react';
import { useAccount } from 'wagmi';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useMutation } from '@tanstack/react-query';
import { PageShell } from '../components/layout/PageShell';
import { PageHeader } from '../components/layout/PageHeader';
import { GlassPanel } from '../components/layout/GlassPanel';
import { Button } from '../components/ui/Button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { createCampaign, getAgentByAddress, createAgent } from '../lib/api';
import { cn } from '@/lib/utils';

interface FormErrors {
  title?: string;
  description?: string;
  goal?: string;
  duration?: string;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="mb-2 block text-xs uppercase tracking-widest text-muted-foreground">
      {children}
    </label>
  );
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-2 flex items-center gap-1 text-xs text-foreground/80">
      <AlertCircle className="h-3 w-3 shrink-0" />
      {message}
    </p>
  );
}

export function CreateCampaignPage() {
  const { isConnected, address } = useAccount();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: '',
    description: '',
    goal: '',
    duration: '30',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const createCampaignMutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: (campaign) => {
      toast.success('Campaign created successfully!');
      navigate(`/campaign/${campaign.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create campaign');
    },
  });

  const validate = (field?: string): FormErrors => {
    const newErrors: FormErrors = {};

    if (!field || field === 'title') {
      if (!form.title.trim()) newErrors.title = 'Title is required';
      else if (form.title.length < 3) newErrors.title = 'At least 3 characters';
      else if (form.title.length > 100) newErrors.title = 'Under 100 characters';
    }

    if (!field || field === 'description') {
      if (form.description.length > 2000) newErrors.description = 'Under 2000 characters';
    }

    if (!field || field === 'goal') {
      if (!form.goal) newErrors.goal = 'Goal is required';
      else {
        const n = parseFloat(form.goal);
        if (isNaN(n) || n <= 0) newErrors.goal = 'Enter a valid amount';
        else if (n > 10000000) newErrors.goal = 'Maximum $10M';
      }
    }

    if (!field || field === 'duration') {
      const n = parseInt(form.duration);
      if (isNaN(n) || n < 1) newErrors.duration = 'Minimum 1 day';
      else if (n > 365) newErrors.duration = 'Maximum 365 days';
    }

    return newErrors;
  };

  const handleBlur = (field: string) => {
    setTouched((t) => ({ ...t, [field]: true }));
    setErrors((prev) => ({ ...prev, ...validate(field) }));
  };

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address) {
      toast.error('Connect your wallet first');
      return;
    }

    setTouched({ title: true, description: true, goal: true, duration: true });
    const allErrors = validate();
    setErrors(allErrors);
    if (Object.keys(allErrors).length > 0) return;

    try {
      let agent;
      try {
        agent = await getAgentByAddress(address);
      } catch {
        agent = await createAgent({
          address,
          name: `Agent ${address.slice(0, 6)}...${address.slice(-4)}`,
          description: 'Auto-created agent',
        });
      }

      const durDays = parseInt(form.duration) || 30;
      const deadline = new Date();
      deadline.setDate(deadline.getDate() + durDays);

      createCampaignMutation.mutate({
        agentId: agent.id,
        title: form.title,
        description: form.description,
        goal: parseFloat(form.goal),
        deadline: deadline.toISOString(),
      });
    } catch (error) {
      toast.error('Failed to create campaign');
      console.error(error);
    }
  };

  return (
    <PageShell>
      <div className="container max-w-2xl">
        <PageHeader
          kicker="Launch"
          title={
            <>
              Create a <em className="not-italic text-muted-foreground">campaign</em>
            </>
          }
          description="Tweet your mission or fill the form below. No Midjourney required: your page ships with the same cinematic video as the home hero."
        />

        <GlassPanel className="mb-8 p-6">
          <div className="mb-4 flex items-center gap-3">
            <Twitter className="h-5 w-5 text-foreground" />
            <p className="text-sm text-foreground">Quick launch via X</p>
          </div>
          <p className="rounded-xl border border-border/60 bg-secondary/30 px-4 py-3 text-sm text-muted-foreground">
            Tweet: &ldquo;Hey @break_whileloop I need $500 for API costs&rdquo;
          </p>
        </GlassPanel>

        <p className="mb-8 text-center text-xs uppercase tracking-widest text-muted-foreground">
          or use the form
        </p>

        <GlassPanel className="p-6 md:p-8">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            <div>
              <FieldLabel>Campaign title *</FieldLabel>
              <Input
                value={form.title}
                onChange={(e) => handleChange('title', e.target.value)}
                onBlur={() => handleBlur('title')}
                placeholder="My AI project"
                className={cn(touched.title && errors.title && 'border-foreground/40')}
              />
              {touched.title && <FieldError message={errors.title} />}
              <p className="mt-1 text-xs text-muted-foreground">{form.title.length}/100</p>
            </div>

            <div>
              <FieldLabel>Description</FieldLabel>
              <Textarea
                value={form.description}
                onChange={(e) => handleChange('description', e.target.value)}
                onBlur={() => handleBlur('description')}
                placeholder="What are you building?"
              />
              {touched.description && <FieldError message={errors.description} />}
              <p className="mt-1 text-xs text-muted-foreground">{form.description.length}/2000</p>
            </div>

            <div>
              <FieldLabel>Goal (USD) *</FieldLabel>
              <Input
                type="number"
                value={form.goal}
                onChange={(e) => handleChange('goal', e.target.value)}
                onBlur={() => handleBlur('goal')}
                placeholder="5000"
                min="1"
              />
              {touched.goal && <FieldError message={errors.goal} />}
            </div>

            <div>
              <FieldLabel>Duration (days) *</FieldLabel>
              <Input
                type="number"
                value={form.duration}
                onChange={(e) => handleChange('duration', e.target.value)}
                onBlur={() => handleBlur('duration')}
                min="1"
                max="365"
              />
              {touched.duration && <FieldError message={errors.duration} />}
              <p className="mt-1 text-xs text-muted-foreground">
                Ends in {form.duration || 0} days
              </p>
            </div>

            {isConnected ? (
              <Button type="submit" className="w-full" isLoading={createCampaignMutation.isPending}>
                Launch campaign
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <div className="text-center">
                <p className="mb-4 text-sm text-muted-foreground">Connect wallet to create</p>
                <Button type="button" variant="secondary" className="w-full" disabled>
                  Wallet not connected
                </Button>
              </div>
            )}
          </form>
        </GlassPanel>
      </div>
    </PageShell>
  );
}
