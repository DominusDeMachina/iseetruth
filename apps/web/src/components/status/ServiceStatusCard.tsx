import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { statusConfig } from "./status-config";
import type { ServiceStatus } from "@/hooks/useHealthStatus";
import { cn } from "@/lib/utils";

interface ServiceStatusCardProps {
  name: string;
  service: ServiceStatus;
}

export function ServiceStatusCard({ name, service }: ServiceStatusCardProps) {
  const config = statusConfig[service.status];
  const Icon = config.icon;

  return (
    <Card className="bg-[var(--bg-elevated)] border-[var(--border-subtle)]">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium capitalize text-[var(--text-primary)]">
          {name}
        </CardTitle>
        <Badge variant="outline" className={cn("text-xs", config.badgeBg)}>
          <Icon className={cn("mr-1 h-3 w-3", config.color)} />
          {config.label}
        </Badge>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-[var(--text-secondary)]">{service.detail}</p>
      </CardContent>
    </Card>
  );
}
