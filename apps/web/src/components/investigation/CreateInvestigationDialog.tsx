import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateInvestigation } from "@/hooks/useInvestigations";

interface CreateInvestigationDialogProps {
  trigger: React.ReactNode;
}

export function CreateInvestigationDialog({
  trigger,
}: CreateInvestigationDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const navigate = useNavigate();
  const createMutation = useCreateInvestigation();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    createMutation.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: (investigation) => {
          setOpen(false);
          setName("");
          setDescription("");
          navigate({
            to: "/investigations/$id",
            params: { id: investigation.id },
          });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-[420px] bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
        <DialogHeader>
          <DialogTitle className="text-[var(--text-primary)]">
            New Investigation
          </DialogTitle>
          <DialogDescription className="text-[var(--text-secondary)]">
            Create a new investigation workspace to organize your documents.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="name" className="text-[var(--text-secondary)]">
              Name
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Investigation name"
              required
              maxLength={255}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label
              htmlFor="description"
              className="text-[var(--text-secondary)]"
            >
              Description
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              maxLength={2000}
              rows={3}
              className="border-[var(--border-subtle)] bg-[var(--bg-secondary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>
          <Button
            type="submit"
            disabled={!name.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? "Creating..." : "Create Investigation"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
