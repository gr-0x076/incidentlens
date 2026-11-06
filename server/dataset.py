"""
IncidentLens Synthetic Microservices Incident Corpus
Modeled on real-world SRE post-mortems (Cloudflare, Monzo, GitLab, Uber, Stripe).

Microservices Topology:
- checkout-api (Go 1.22): Core ingress orchestrator
- payment-gw (Java 21 / Spring Boot): Interacts with external bank APIs and shared Redis
- auth-service (Node.js / Express): JWT validation and session cache
- inventory-service (Python / FastAPI): Stock reservation and DB locking
- shared-redis-cluster: Shared caching and rate limiting tier
- aurora-postgres-cluster: Persistent relational data store
"""

from typing import List, Dict, Any

INCIDENTS: List[Dict[str, Any]] = [
    # Cluster 1: Redis Connection Pool Starvation (Incidents 1-4)
    {
        "id": "INC-101",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-09-12T03:14:22Z",
        "title": "Payment gateway HTTP 502 with JedisConnectionException",
        "symptoms": "Spike in 502 Bad Gateway responses during checkout. Upstream latency jumped from 45ms to 12,000ms. Error logs show JedisConnectionException: Could not get a resource from the pool.",
        "stack_trace": "redis.clients.jedis.exceptions.JedisConnectionException: Could not get a resource from the pool\n  at redis.clients.jedis.util.Pool.getResource(Pool.java:59)\n  at com.company.payment.cache.RedisSessionCache.getSession(RedisSessionCache.java:42)",
        "deployment_context": "auth-service canary deploy v2.4.1 completed 45 minutes prior.",
        "root_cause": "auth-service canary deployed a leaky connection loop that failed to release Jedis connections on token timeout, exhausting the shared Redis pool.",
        "attempted_mitigations": [
            {"action": "Restarted payment-gw pods", "status": "FAILED", "notes": "New pods exhausted connection pool within 90 seconds of booting."},
            {"action": "Rolled back auth-service to v2.4.0 and restarted Redis client leases", "status": "WORKED", "notes": "Pool recovered immediately, 502 error rate dropped to zero."}
        ],
        "verified_fix": "Rollback auth-service deploy v2.4.1; do not restart payment-gw."
    },
    {
        "id": "INC-102",
        "service": "auth-service",
        "severity": "P2",
        "timestamp": "2026-09-18T14:20:10Z",
        "title": "JWT validation latency degradation and Redis socket timeout",
        "symptoms": "P99 latency on /v1/auth/verify exceeded 2500ms. Intermittent Redis timeout errors logged across 6 worker processes.",
        "stack_trace": "Error: Redis connection lost: ETIMEDOUT\n  at Socket.<anonymous> (/app/node_modules/ioredis/lib/redis/event_handler.js:182:17)\n  at TCP.onStreamRead (node:internal/stream_base_commons:217:20)",
        "deployment_context": "No recent deployment. Traffic increased 40% due to marketing push.",
        "root_cause": "Redis maxclients limit reached (default 10,000). Active idle connections were not closing due to missing keepalive headers.",
        "attempted_mitigations": [
            {"action": "Increased auth-service pod replica count from 8 to 16", "status": "FAILED", "notes": "Doubling pods doubled active connections, making Redis maxclients saturation worse."},
            {"action": "Enabled client-side connection pooling with 30s idle timeout", "status": "WORKED", "notes": "Active connections dropped from 9,800 to 1,400."}
        ],
        "verified_fix": "Tune client-side connection pooling and idle timeout; avoid scaling pod count during connection pool saturation."
    },
    {
        "id": "INC-103",
        "service": "checkout-api",
        "severity": "P1",
        "timestamp": "2026-09-24T09:45:00Z",
        "title": "Checkout ingress dropping requests: Upstream auth service unreachable",
        "symptoms": "Ingress controller reports 504 Gateway Timeout. Checkout-api fails to validate bearer tokens from auth-service. Error: context deadline exceeded.",
        "stack_trace": "goroutine 14201 [running]:\nmain.validateToken(0xc00045e000, {0x7fff, 0x1f})\n\t/src/auth_client.go:88 +0x245\nmain.handleCheckout(...)\n\t/src/handlers.go:124 +0x489",
        "deployment_context": "ConfigMap update applied to auth-service ingress 15m ago.",
        "root_cause": "Misconfigured gRPC keepalive in auth-service ConfigMap caused HTTP/2 connection hang under high concurrency.",
        "attempted_mitigations": [
            {"action": "Rolled back auth-service ConfigMap and triggered rolling restart", "status": "WORKED", "notes": "TCP RST frames cleared, gRPC channels re-established instantly."}
        ],
        "verified_fix": "Revert ConfigMap gRPC keepalive parameters and rolling restart auth-service."
    },
    {
        "id": "INC-104",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-10-02T11:10:00Z",
        "title": "Payment-gw Redis connection pool exhaustion after flash sale spike",
        "symptoms": "Redis connection pool empty. Checkout payments failing with 500 Internal Server Error. Logs match JedisConnectionException from September.",
        "stack_trace": "redis.clients.jedis.exceptions.JedisConnectionException: Could not get a resource from the pool: Timeout waiting for idle object\n  at org.apache.commons.pool2.impl.GenericObjectPool.borrowObject(GenericObjectPool.java:449)",
        "deployment_context": "Marketing flash sale triggered 3x normal traffic burst.",
        "root_cause": "Payment-gw redis client connection pool size fixed at 50, insufficient for 3x traffic burst.",
        "attempted_mitigations": [
            {"action": "Restarted payment-gw pods", "status": "FAILED", "notes": "Temporary relief for 2 minutes before exhaustion recurred."},
            {"action": "Increased Jedis maxTotal from 50 to 200 via Helm values and applied HPA", "status": "WORKED", "notes": "Pool headroom stabilized at 45% utilization."}
        ],
        "verified_fix": "Increase Jedis pool maxTotal and enable horizontal pod autoscaler."
    },

    # Cluster 2: Database Row-Lock Contention & Deadlocks (Incidents 5-8)
    {
        "id": "INC-201",
        "service": "inventory-service",
        "severity": "P1",
        "timestamp": "2026-10-08T18:05:30Z",
        "title": "Postgres deadlock detected during concurrent stock reservation",
        "symptoms": "Inventory reservations timing out. Database CPU at 98%. Active locks table shows 140+ blocked queries waiting on relation stock_items.",
        "stack_trace": "asyncpg.exceptions.DeadlockDetectedError: deadlock detected\nDETAIL: Process 1482 waits for ExclusiveLock on tuple (14, 2) of relation 'stock_items'; blocked by process 1490.\nProcess 1490 waits for ExclusiveLock on tuple (14, 3); blocked by process 1482.",
        "deployment_context": "New batch reservation endpoint deployed in inventory-service v1.8.0.",
        "root_cause": "Batch reservation query updated inventory items in unordered sequence, causing cyclic lock waits between concurrent checkout transactions.",
        "attempted_mitigations": [
            {"action": "Killed blocking Postgres queries manually", "status": "FAILED", "notes": "Blocked queries immediately piled back up within seconds."},
            {"action": "Enforced sorted item ID locking (SELECT ... ORDER BY item_id FOR UPDATE) in PR #312", "status": "WORKED", "notes": "Completely eliminated lock cycle contention. Active locks dropped to normal."}
        ],
        "verified_fix": "Enforce sorted ID ordering in multi-row SELECT FOR UPDATE queries to prevent cyclic lock dependency."
    },
    {
        "id": "INC-202",
        "service": "inventory-service",
        "severity": "P2",
        "timestamp": "2026-10-14T20:30:15Z",
        "title": "Lock wait timeout exceeded on warehouse allocation updates",
        "symptoms": "504 Gateway Timeouts on /v1/inventory/allocate. Postgres pg_stat_activity shows multiple sessions in 'idle in transaction' state.",
        "stack_trace": "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) ERROR: lock timeout exceeded\nCONTEXT: while updating tuple (88, 12) in relation 'warehouse_allocations'",
        "deployment_context": "No code changes. Third-party logistics API experiencing elevated response times.",
        "root_cause": "inventory-service held DB transaction open while awaiting external HTTP call to logistics provider.",
        "attempted_mitigations": [
            {"action": "Increased postgres lock_timeout from 10s to 30s", "status": "FAILED", "notes": "Exacerbated connection starvation by holding locks longer."},
            {"action": "Moved external HTTP call outside database transaction block", "status": "WORKED", "notes": "Transaction duration fell from 8.2s to 12ms. Lock contention vanished."}
        ],
        "verified_fix": "Never hold database transactions open during external network calls; move HTTP RPCs outside transaction boundaries."
    },
    {
        "id": "INC-203",
        "service": "checkout-api",
        "severity": "P1",
        "timestamp": "2026-10-19T02:15:00Z",
        "title": "Postgres active connection pool saturation causing global checkout failure",
        "symptoms": "Checkout-api unable to acquire Postgres connection from PgBouncer. Error: remaining connection slots are reserved for non-replication superuser connections.",
        "stack_trace": "FATAL: remaining connection slots are reserved for non-replication superuser connections\n  at database/sql.OpenConn(sql.go:1284)",
        "deployment_context": "Cron job for analytics export ran simultaneously with scheduled nightly DB backup.",
        "root_cause": "Analytics ETL job bypassed PgBouncer and opened 150 direct unpooled connections to Aurora writer node.",
        "attempted_mitigations": [
            {"action": "Increased Aurora max_connections parameter", "status": "FAILED", "notes": "Triggered database memory pressure and swap usage."},
            {"action": "Rerouted analytics job to Aurora read-replica through dedicated PgBouncer pool", "status": "WORKED", "notes": "Primary connection pool stabilized under 20% capacity."}
        ],
        "verified_fix": "Route all batch/ETL jobs to read-replicas; enforce connection pooling through PgBouncer."
    },
    {
        "id": "INC-204",
        "service": "inventory-service",
        "severity": "P2",
        "timestamp": "2026-10-23T16:40:00Z",
        "title": "Deadlock in stock decrement on flash sale SKU",
        "symptoms": "Deadlock detected error logged 85 times in 5 minutes. High transaction rollback rate.",
        "stack_trace": "asyncpg.exceptions.DeadlockDetectedError: deadlock detected on relation 'stock_items'",
        "deployment_context": "Flash sale launched on iPhone 16 SKU.",
        "root_cause": "Unsorted multi-item cart reservations attempting lock acquisitions in opposite order.",
        "attempted_mitigations": [
            {"action": "Applied sorted ID locking rule verified in INC-201", "status": "WORKED", "notes": "Verified past mitigation applied successfully. Deadlocks dropped to 0."}
        ],
        "verified_fix": "Apply sorted item_id locking pattern in SQL reservation query."
    },

    # Cluster 3: Stale DNS & JVM Cache Drift (Incidents 9-12)
    {
        "id": "INC-301",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-10-26T08:12:00Z",
        "title": "Payment-gw connecting to old RDS replica IP after failover",
        "symptoms": "Database writes failing with ReadOnlySQLException. Aurora failover completed successfully 30 minutes ago, but payment-gw continues routing writes to the former primary.",
        "stack_trace": "org.postgresql.util.PSQLException: ERROR: cannot execute INSERT in a read-only transaction\n  at org.postgresql.core.v3.QueryExecutorImpl.receiveErrorResponse(QueryExecutorImpl.java:2553)\n  at com.company.payment.repo.OrderRepo.insert(OrderRepo.java:82)",
        "deployment_context": "AWS Aurora primary node maintenance failover triggered at 07:45 UTC.",
        "root_cause": "Java JVM default security policy caches DNS lookups forever (networkaddress.cache.ttl = -1), ignoring DNS record updates.",
        "attempted_mitigations": [
            {"action": "Promoted read replica back to primary", "status": "FAILED", "notes": "Did not address stale DNS resolution on application nodes."},
            {"action": "Set -Dnetworkaddress.cache.ttl=10 JVM option and performed rolling restart", "status": "WORKED", "notes": "Pods refreshed DNS within 10s and routed to new primary writer node."}
        ],
        "verified_fix": "Configure JVM DNS cache TTL to 10 seconds (-Dnetworkaddress.cache.ttl=10); perform rolling restart."
    },
    {
        "id": "INC-302",
        "service": "checkout-api",
        "severity": "P2",
        "timestamp": "2026-10-28T19:00:20Z",
        "title": "Checkout-api CoreDNS lookup timeout after node drain",
        "symptoms": "Intermittent dial tcp: i/o timeout when resolving payment-gw.production.svc.cluster.local.",
        "stack_trace": "net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)\n  dial tcp: lookup payment-gw.production.svc.cluster.local on 10.96.0.10:53: i/o timeout",
        "deployment_context": "Kubernetes worker node upgrade drained node hosting CoreDNS replica.",
        "root_cause": "checkout-api pods lacked local DNS caching (NodeLocal DNSCache), overwhelming remaining CoreDNS pods with UDP traffic.",
        "attempted_mitigations": [
            {"action": "Scaled CoreDNS deployment from 2 to 6 replicas", "status": "FAILED", "notes": "UDP packet drops at node conntrack level persisted."},
            {"action": "Deployed NodeLocal DNSCache DaemonSet and enabled ndots:2 in pod dnsConfig", "status": "WORKED", "notes": "DNS resolution latency dropped from 450ms to 0.4ms."}
        ],
        "verified_fix": "Deploy NodeLocal DNSCache and optimize ndots:2 in Kubernetes dnsConfig."
    },
    {
        "id": "INC-303",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-10-31T04:22:10Z",
        "title": "Payment-gw ReadOnlySQLException following Aurora cluster upgrade",
        "symptoms": "Write operations failing with read-only transaction errors after minor engine version upgrade.",
        "stack_trace": "org.postgresql.util.PSQLException: ERROR: cannot execute UPDATE in a read-only transaction",
        "deployment_context": "Aurora PostgreSQL minor version patch applied during scheduled maintenance.",
        "root_cause": "JVM DNS caching resolved Aurora cluster endpoint to stale writer IP.",
        "attempted_mitigations": [
            {"action": "Applied verified fix from INC-301 (-Dnetworkaddress.cache.ttl=10 and rolling restart)", "status": "WORKED", "notes": "Known verified fix confirmed effective. Reconnected to active writer within 10 seconds."}
        ],
        "verified_fix": "Set JVM networkaddress.cache.ttl=10 and execute rolling pod restart."
    },
    {
        "id": "INC-304",
        "service": "inventory-service",
        "severity": "P2",
        "timestamp": "2026-11-01T13:15:00Z",
        "title": "Stale DNS resolution to read replica following cluster failover",
        "symptoms": "FastAPI database connection pool pointing to decommissioned replica IP.",
        "stack_trace": "asyncpg.exceptions.CannotConnectNowError: the database system is shutting down",
        "deployment_context": "Aurora replica replacement after hardware degradation.",
        "root_cause": "asyncpg connection pool did not refresh DNS hostnames without recycling pool connections.",
        "attempted_mitigations": [
            {"action": "Configured max_inactive_connection_lifetime=300s in asyncpg pool", "status": "WORKED", "notes": "Pool automatically recycles and resolves fresh IP addresses."}
        ],
        "verified_fix": "Configure max_inactive_connection_lifetime in connection pool to ensure DNS refresh."
    },

    # Cluster 4: Kafka Rebalance Storms & Poison Pills (Incidents 13-16)
    {
        "id": "INC-401",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-11-02T10:05:00Z",
        "title": "Kafka consumer group rebalance loop on payment-events topic",
        "symptoms": "Payment processing halted. Kafka consumer group constantly rebalancing; consumer lag climbing by 5,000 msgs/min. Offset commits failing.",
        "stack_trace": "org.apache.kafka.clients.consumer.CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member.\n  at org.apache.kafka.clients.consumer.internals.ConsumerCoordinator.sendOffsetCommitRequest(ConsumerCoordinator.java:1120)",
        "deployment_context": "Release of new fraud check micro-filter inside consumer loop.",
        "root_cause": "Fraud check RPC took 45s on large payload, exceeding max.poll.interval.ms (30,000ms), causing Kafka coordinator to evict consumer.",
        "attempted_mitigations": [
            {"action": "Increased consumer replica pods from 4 to 8", "status": "FAILED", "notes": "Added more consumers to an already thrashing rebalance loop, worsening downtime."},
            {"action": "Increased max.poll.interval.ms to 300000ms and reduced max.poll.records to 50", "status": "WORKED", "notes": "Consumers stopped missing heartbeats; rebalance stabilized and lag cleared in 6 minutes."}
        ],
        "verified_fix": "Increase max.poll.interval.ms and decrease max.poll.records; do NOT scale consumer count during rebalance storm."
    },
    {
        "id": "INC-402",
        "service": "checkout-api",
        "severity": "P2",
        "timestamp": "2026-11-03T02:18:00Z",
        "title": "Order event consumer pod crash loop on malformed JSON payload",
        "symptoms": "Order fulfillment worker crashing with SIGSEGV/panic on topic order-created. Unhandled nil pointer on missing currency field.",
        "stack_trace": "panic: runtime error: invalid memory address or nil pointer dereference\n[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x8f2a1b]\n  at main.parseOrderPayload(order_consumer.go:142)",
        "deployment_context": "External partner sent unversioned test webhook with omitted currency field.",
        "root_cause": "Poison pill message without currency field crashes consumer, stays uncommitted, and crashes next assigned consumer repeatedly.",
        "attempted_mitigations": [
            {"action": "Restarted consumer deployment", "status": "FAILED", "notes": "Immediately crashed again upon reading poison pill message at offset 491024."},
            {"action": "Configured Dead Letter Queue (DLQ) with schema validation and skipped poison offset", "status": "WORKED", "notes": "Poison pill routed to DLQ; consumer processing resumed normally."}
        ],
        "verified_fix": "Route malformed payloads to Dead Letter Queue (DLQ); do not blindly restart consumers on unhandled panic."
    },
    {
        "id": "INC-403",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-11-03T17:40:00Z",
        "title": "Payment consumer group evicted during external fraud API timeout",
        "symptoms": "Kafka consumer lag exceeding 20,000 events. Logs show CommitFailedException identical to INC-401.",
        "stack_trace": "org.apache.kafka.clients.consumer.CommitFailedException: Commit cannot be completed since the group has already rebalanced",
        "deployment_context": "Third-party fraud scoring API latency elevated to 35 seconds.",
        "root_cause": "Processing time exceeded max.poll.interval.ms due to unconstrained external HTTP call.",
        "attempted_mitigations": [
            {"action": "Applied verified fix from INC-401: tuned max.poll.interval.ms and wrapped external call with 5s timeout", "status": "WORKED", "notes": "Verified fix confirmed. Consumers maintained heartbeats and lag drained."}
        ],
        "verified_fix": "Enforce strict HTTP client timeout (5s) and tune max.poll.interval.ms."
    },
    {
        "id": "INC-404",
        "service": "inventory-service",
        "severity": "P2",
        "timestamp": "2026-11-04T07:11:00Z",
        "title": "Inventory sync consumer lag growing during catalog re-indexing",
        "symptoms": "Consumer group stock-sync falling behind by 12,000 messages. Event processing time 4,500ms per batch.",
        "stack_trace": "INFO org.apache.kafka.clients.consumer.internals.ConsumerCoordinator - [Consumer clientId=stock-1, groupId=stock-sync] Resetting generation due to timeout",
        "deployment_context": "Catalog re-indexing triggered large burst of inventory sync events.",
        "root_cause": "Batch size too large for database upsert throughput.",
        "attempted_mitigations": [
            {"action": "Decreased max.poll.records to 25 and tuned batch upsert chunking", "status": "WORKED", "notes": "Batch commit latency fell to 210ms; consumer remained stable."}
        ],
        "verified_fix": "Reduce max.poll.records to fit database write throughput limits."
    },

    # Cluster 5: Downstream Throttling & Upstream Retry Cascades (Incidents 17-20)
    {
        "id": "INC-501",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-11-04T19:30:00Z",
        "title": "Bank upstream HTTP 429 throttling causing cascading thread exhaustion",
        "symptoms": "Card payment success rate dropped to 12%. Upstream bank API returning HTTP 429 Too Many Requests. Tomcat active worker threads saturated at 200/200.",
        "stack_trace": "feign.FeignException$TooManyRequests: [429 Too Many Requests] during [POST] to [https://api.partnerbank.com/v2/charges]\n  at feign.FeignException.errorStatus(FeignException.java:220)\n  at com.company.payment.client.BankClient.charge(BankClient.java:31)",
        "deployment_context": "Marketing promo push drove 2.5x payment volume.",
        "root_cause": "Upstream bank enforces hard rate limit of 150 RPS. Payment-gw retried failed 429s immediately without backoff, worsening the throttle.",
        "attempted_mitigations": [
            {"action": "Increased Tomcat thread pool from 200 to 500", "status": "FAILED", "notes": "Caused OutOfMemoryError: unable to create new native thread; crashed pod."},
            {"action": "Enabled Resilience4j circuit breaker with exponential backoff and jitter, and activated client-side rate limiter at 140 RPS", "status": "WORKED", "notes": "Upstream 429 errors stopped. Payments queued gracefully; success rate restored to 99.4%."}
        ],
        "verified_fix": "Enable circuit breaker with exponential backoff + jitter; cap outbound rate limiter below upstream threshold (140 RPS); do NOT increase thread pool."
    },
    {
        "id": "INC-502",
        "service": "checkout-api",
        "severity": "P1",
        "timestamp": "2026-11-05T04:10:00Z",
        "title": "Checkout-api goroutine leak on hung downstream payment calls",
        "symptoms": "checkout-api memory climbed to 2.1GB until OOMKilled by Kubernetes. Goroutine count spiked from 400 to 32,000.",
        "stack_trace": "runtime.gopark(0x10a2b40, 0x0, 0x14, 0x18)\n  net/http.(*persistConn).roundTrip(0xc00028a000, 0xc00034a000)\n  net/http.(*Transport).roundTrip(0x13c2f00, 0xc00034a000)",
        "deployment_context": "payment-gw experiencing elevated latencies due to upstream bank throttling.",
        "root_cause": "checkout-api HTTP client lacked Request.Context deadline; hung payment requests leaked goroutines indefinitely.",
        "attempted_mitigations": [
            {"action": "Increased pod memory limit from 2Gi to 4Gi", "status": "FAILED", "notes": "Delayed OOMKill by 12 minutes but goroutine leak continued unbounded."},
            {"action": "Configured strict 3.5s context timeout on outbound HTTP client transport", "status": "WORKED", "notes": "Goroutine count stabilized under 800. Fast failure prevented memory leak."}
        ],
        "verified_fix": "Enforce strict HTTP context deadline on outbound client; never raise memory limits to paper over goroutine leaks."
    },
    {
        "id": "INC-503",
        "service": "payment-gw",
        "severity": "P1",
        "timestamp": "2026-11-05T15:00:00Z",
        "title": "Payment provider 429 cascade recurring on peak traffic window",
        "symptoms": "Upstream bank API returning HTTP 429 Too Many Requests. Latency climbing across checkout flow.",
        "stack_trace": "feign.FeignException$TooManyRequests: [429 Too Many Requests] during [POST] to [https://api.partnerbank.com/v2/charges]",
        "deployment_context": "Friday evening traffic surge.",
        "root_cause": "Bank rate limit exceeded by unthrottled retry storm.",
        "attempted_mitigations": [
            {"action": "Applied verified fix from INC-501: Resilience4j circuit breaker with 140 RPS rate limit", "status": "WORKED", "notes": "Verified past mitigation applied. Zero 429s, payments queued cleanly."}
        ],
        "verified_fix": "Apply client-side rate limiter (140 RPS) and exponential backoff circuit breaker."
    },
    {
        "id": "INC-504",
        "service": "auth-service",
        "severity": "P2",
        "timestamp": "2026-11-05T20:45:00Z",
        "title": "Cross-service policy conflict: Thread/worker scaling failure",
        "symptoms": "auth-service Node.js cluster processes maxing out CPU under burst auth requests.",
        "stack_trace": "Error: Worker process 4821 terminated with exit code 137 (OOM)",
        "deployment_context": "Attempted to apply thread scaling policy that succeeded on inventory-service.",
        "root_cause": "Node.js single-threaded event loop architecture does not benefit from thread-pool expansion; worker process memory limit hit.",
        "attempted_mitigations": [
            {"action": "Increased worker threads inside Node process", "status": "FAILED", "notes": "Triggered memory bloat and event-loop lag. Proved policy conflict with Python/FastAPI service."},
            {"action": "Implemented Redis-backed token cache with 60s TTL to absorb 80% of crypto verification compute", "status": "WORKED", "notes": "CPU dropped from 94% to 28%."}
        ],
        "verified_fix": "Cache verified JWT claims in Redis; do NOT attempt thread-pool tuning on Node.js services."
    }
]
