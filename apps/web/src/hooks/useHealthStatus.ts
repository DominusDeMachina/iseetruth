import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export interface OllamaModel {
  name: string;
  available: boolean;
}

export interface ServiceStatus {
  status: "healthy" | "unhealthy" | "unavailable";
  detail: string;
  models_ready?: boolean;
  models?: OllamaModel[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  services: Record<string, ServiceStatus>;
  warnings: string[];
}

export function useHealthStatus() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/health/");
      if (error) throw error;
      return data as unknown as HealthResponse;
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: true,
  });
}
