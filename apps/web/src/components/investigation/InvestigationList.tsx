import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { InvestigationCard } from "./InvestigationCard";
import { CreateInvestigationDialog } from "./CreateInvestigationDialog";
import { useInvestigations } from "@/hooks/useInvestigations";

function SkeletonCard() {
  return (
    <Card className="animate-pulse border-[var(--border-subtle)] bg-[var(--bg-elevated)] py-6">
      <div className="flex flex-col gap-4 px-6">
        <div className="h-5 w-2/3 rounded bg-[var(--bg-hover)]" />
        <div className="h-4 w-full rounded bg-[var(--bg-hover)]" />
        <div className="h-4 w-1/3 rounded bg-[var(--bg-hover)]" />
      </div>
    </Card>
  );
}

export function InvestigationList() {
  const { data, isLoading, isError } = useInvestigations();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Header />
        <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col gap-6">
        <Header />
        <div className="flex flex-col items-center gap-2 pt-12 text-center">
          <p className="text-[var(--text-primary)]">
            Failed to load investigations
          </p>
          <p className="text-sm text-[var(--text-secondary)]">
            Check that the backend is running and try again.
          </p>
        </div>
      </div>
    );
  }

  const investigations = data?.items ?? [];

  if (investigations.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <Header />
        <div className="flex flex-col items-center gap-4 pt-12 text-center">
          <p className="text-[var(--text-primary)]">
            Create your first investigation to get started
          </p>
          <CreateInvestigationDialog
            trigger={
              <Button>
                <Plus className="size-4" />
                New Investigation
              </Button>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Header />
      <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4">
        {investigations.map((investigation) => (
          <InvestigationCard
            key={investigation.id}
            investigation={investigation}
          />
        ))}
      </div>
    </div>
  );
}

function Header() {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
        Investigations
      </h2>
      <CreateInvestigationDialog
        trigger={
          <Button>
            <Plus className="size-4" />
            New Investigation
          </Button>
        }
      />
    </div>
  );
}
