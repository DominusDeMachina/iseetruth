import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

// --- Story 10.2: Entity detail types ---

export interface EntityRelationshipInfo {
  type: string;
  target_name: string | null;
  target_type: string | null;
  confidence_score: number;
}

export interface EntityDocumentInfo {
  document_id: string;
  filename: string;
  mention_count: number;
}

export interface InvestigationPresence {
  investigation_id: string;
  investigation_name: string;
  entity_id: string;
  relationships: EntityRelationshipInfo[];
  source_documents: EntityDocumentInfo[];
  relationship_count: number;
  confidence_score: number;
}

export interface CrossInvestigationEntityDetailResponse {
  entity_name: string;
  entity_type: string;
  investigations: InvestigationPresence[];
  total_investigations: number;
}

// --- Story 10.2: Search types ---

export interface CrossInvestigationSearchResultInvestigation {
  investigation_id: string;
  investigation_name: string;
  entity_id: string;
  relationship_count: number;
}

export interface CrossInvestigationSearchResult {
  entity_name: string;
  entity_type: string;
  investigation_count: number;
  investigations: CrossInvestigationSearchResultInvestigation[];
  match_score: number;
}

export interface CrossInvestigationSearchResponse {
  results: CrossInvestigationSearchResult[];
  total_results: number;
  query_duration_ms: number;
}

// --- Hooks ---

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

export function useCrossInvestigationEntityDetail(
  entityName: string,
  entityType: string,
  enabled = true,
) {
  return useQuery<CrossInvestigationEntityDetailResponse>({
    queryKey: ["cross-investigation-detail", entityName, entityType],
    queryFn: async () => {
      const params = new URLSearchParams({
        entity_name: entityName,
        entity_type: entityType,
      });
      const resp = await fetch(`/api/v1/cross-links/entity-detail/?${params}`);
      if (!resp.ok) {
        throw new Error(`Entity detail query failed: ${resp.status}`);
      }
      return resp.json();
    },
    enabled: !!entityName && !!entityType && enabled,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCrossInvestigationSearch(query: string, enabled = true) {
  return useQuery<CrossInvestigationSearchResponse>({
    queryKey: ["cross-investigation-search", query],
    queryFn: async () => {
      const params = new URLSearchParams({ q: query });
      const resp = await fetch(`/api/v1/cross-links/search/?${params}`);
      if (!resp.ok) {
        throw new Error(`Cross-investigation search failed: ${resp.status}`);
      }
      return resp.json();
    },
    enabled: !!query && query.length >= 2 && enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useDismissCrossMatch(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    void,
    Error,
    { entityName: string; entityType: string; targetInvestigationId: string }
  >({
    mutationFn: async ({ entityName, entityType, targetInvestigationId }) => {
      const resp = await fetch(
        `/api/v1/investigations/${investigationId}/cross-links/dismiss`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            entity_name: entityName,
            entity_type: entityType,
            target_investigation_id: targetInvestigationId,
          }),
        },
      );
      if (!resp.ok && resp.status !== 409) {
        throw new Error(`Dismiss failed: ${resp.status}`);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["cross-investigation", investigationId],
      });
    },
  });
}

export function useUndismissCrossMatch(investigationId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    void,
    Error,
    { entityName: string; entityType: string; targetInvestigationId: string }
  >({
    mutationFn: async ({ entityName, entityType, targetInvestigationId }) => {
      const resp = await fetch(
        `/api/v1/investigations/${investigationId}/cross-links/dismiss`,
        {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            entity_name: entityName,
            entity_type: entityType,
            target_investigation_id: targetInvestigationId,
          }),
        },
      );
      if (!resp.ok) {
        throw new Error(`Undismiss failed: ${resp.status}`);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["cross-investigation", investigationId],
      });
    },
  });
}
