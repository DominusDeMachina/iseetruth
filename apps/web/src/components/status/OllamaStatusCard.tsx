import { CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { statusConfig } from "./status-config";
import type { ServiceStatus } from "@/hooks/useHealthStatus";
import { cn } from "@/lib/utils";

interface OllamaStatusCardProps {
  service: ServiceStatus;
}

export function OllamaStatusCard({ service }: OllamaStatusCardProps) {
  const config = statusConfig[service.status];
  const Icon = config.icon;

  return (
    <Card className="bg-[var(--bg-elevated)] border-[var(--border-subtle)] md:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-[var(--text-primary)]">
          Ollama
        </CardTitle>
        <Badge variant="outline" className={cn("text-xs", config.badgeBg)}>
          <Icon className={cn("mr-1 h-3 w-3", config.color)} />
          {config.label}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-[var(--text-secondary)]">{service.detail}</p>
        {service.models && service.models.length > 0 && (
          <>
            <Separator className="bg-[var(--border-subtle)]" />
            <div className="space-y-2">
              <p className="text-xs font-medium text-[var(--text-secondary)]">
                Models
              </p>
              {service.models.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between"
                >
                  <span className="text-xs text-[var(--text-primary)] font-mono">
                    {model.name}
                  </span>
                  <span className="flex items-center gap-1 text-xs">
                    {model.available ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 text-[var(--status-success)]" />
                        <span className="text-[var(--status-success)]">
                          Available
                        </span>
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3 w-3 text-[var(--status-error)]" />
                        <span className="text-[var(--status-error)]">
                          Unavailable
                        </span>
                      </>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
