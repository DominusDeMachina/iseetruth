import { useQuery } from "@tanstack/react-query";

export interface InvestigationEntityInfo {
  investigation_id: string;
  investigation_name: string;
  entity_id: string;
  relationship_count: number;
  confidence_score: number;
}

export interface CrossInvestigationMatch {
  entity_name: string;
  entity_type: string;
  match_confidence: number;
  match_type: string;
  source_entity_id: string;
  source_relationship_count: number;
  source_confidence_score: number;
  investigations: InvestigationEntityInfo[];
}

export interface CrossInvestigationResponse {
  matches: CrossInvestigationMatch[];
  total_matches: number;
  query_duration_ms: number;
}

export function useCrossInvestigation(investigationId: string, enabled = true) {
  return useQuery<CrossInvestigationResponse>({
    queryKey: ["cross-investigation", investigationId],
    queryFn: async () => {
      const resp = await fetch(
        `/api/v1/investigations/${investigationId}/cross-links/`,
      );
      if (!resp.ok) {
        throw new Error(`Cross-investigation query failed: ${resp.status}`);
      }
      return resp.json();
    },
    enabled: !!investigationId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
