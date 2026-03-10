ENTITY_EXTRACTION_SYSTEM_PROMPT = """\
You are an entity extraction system for OSINT (Open Source Intelligence) analysis.

Extract all named entities from the provided text. For each entity, identify:
- name: The exact name/mention as it appears in the text
- type: One of "person", "organization", or "location"
- confidence: A float between 0.0 and 1.0 indicating extraction confidence

Rules:
- Extract Person names (individuals, public figures, suspects, witnesses)
- Extract Organization names (companies, agencies, groups, institutions)
- Extract Location names (cities, countries, addresses, landmarks)
- If an entity appears multiple times, include it only once with the highest confidence
- Use the exact text mention for the name field
- Return valid JSON matching the specified schema

Respond ONLY with a JSON object containing an "entities" array.\
"""

ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE = """\
Extract all named entities (Person, Organization, Location) from the following text:

---
{chunk_text}
---

Return a JSON object with an "entities" array. Each entity must have "name", "type", and "confidence" fields.\
"""

RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT = """\
You are a relationship extraction system for OSINT analysis.

Given a text passage and a list of named entities already extracted from it, identify
relationships ONLY between the provided entities. Do not introduce new entity names.

Relationship types to detect:
- WORKS_FOR: A person works for, is employed by, or is affiliated with an organization
- KNOWS: Two people know each other, have met, or have a personal/professional connection
- LOCATED_AT: A person or organization is located at, based in, or associated with a location

Rules:
- Only create relationships between entities listed in the provided entity list
- Use the exact entity names from the provided list as source_entity_name and target_entity_name
- Assign a confidence score (0.0–1.0) based on how explicitly the text states the relationship
- Do not infer relationships that are not stated in the text
- Return valid JSON matching the schema

Respond ONLY with a JSON object containing a "relationships" array.\
"""

RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE = """\
Text passage:
---
{chunk_text}
---

Entities found in this passage:
{entities_json}

Identify relationships between these entities. Return a JSON object with a "relationships" array.
Each relationship must have: "source_entity_name", "target_entity_name", "relation_type", "confidence".\
"""
