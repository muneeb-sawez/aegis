// AEGIS Neo4j Schema & Constraints (docs/02-CONTRACTS.md §1)
// Apply once on database initialization.

// Uniqueness constraints
CREATE CONSTRAINT service_id_unique IF NOT EXISTS
FOR (s:Service) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT database_id_unique IF NOT EXISTS
FOR (d:Database) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT endpoint_id_unique IF NOT EXISTS
FOR (e:APIEndpoint) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT pod_id_unique IF NOT EXISTS
FOR (p:Pod) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT incident_id_unique IF NOT EXISTS
FOR (i:Incident) REQUIRE i.id IS UNIQUE;

CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (dec:Decision) REQUIRE dec.id IS UNIQUE;

// Indexes for fast lookup
CREATE INDEX service_name_idx IF NOT EXISTS
FOR (s:Service) ON (s.name);

CREATE INDEX incident_timestamp_idx IF NOT EXISTS
FOR (i:Incident) ON (i.timestamp);
