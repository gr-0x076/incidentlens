"""
IncidentLens Held-Out Test Incidents (Generalization & Evaluation Benchmark)
These 6 incidents are NEVER seeded into Hindsight memory.
They are used strictly for unbiased holdout evaluation to test generalization,
avoid train-test leakage, and benchmark learning transfer.
"""

from typing import List, Dict, Any

HOLDOUT_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "HOLD-101",
        "service": "checkout-api",
        "severity": "P1",
        "timestamp": "2026-10-02T19:45:00Z",
        "title": "Checkout API Redis pool exhaustion under flash-sale burst",
        "symptoms": "HTTP 500 error spike during promotional launch. Upstream latency jumped from 22ms to 8,400ms. Redis client pool maxTotal=50 saturated.",
        "stack_trace": "redis.clients.jedis.exceptions.JedisConnectionException: Could not get a resource from the pool\n  at redis.clients.jedis.util.Pool.getResource(Pool.java:59)\n  at com.company.checkout.session.SessionStore.acquire(SessionStore.java:88)",
        "deployment_context": "Flash-sale event launched 10 minutes prior. Redis pool size unchanged at 50.",
        "root_cause": "Jedis connection pool undersized for burst traffic; active sessions saturated pool ceiling.",
        "ground_truth_root_cause": "Jedis connection pool undersized for burst traffic; active sessions saturated pool ceiling.",
        "negative_actions": ["Restarted checkout-api pods", "Doubled pod count"],
        "known_failed_actions": ["Restarted checkout-api pods", "Doubled pod count"],
        "verified_fix": "Increase Jedis maxTotal to 200 and enable dynamic pool sizing.",
        "expected_action_type": "SCALE_POOL"
    },
    {
        "id": "HOLD-201",
        "service": "catalog-indexer",
        "severity": "P2",
        "timestamp": "2026-10-15T08:12:00Z",
        "title": "PostgreSQL deadlock during concurrent inventory catalog sync",
        "symptoms": "Batch catalog indexing failed with error code 40P01. Postgres transactions aborted.",
        "stack_trace": "org.postgresql.util.PSQLException: ERROR: deadlock detected\n  Detail: Process 18420 waits for ShareLock on transaction 91823; blocked by process 18429.\n  at org.postgresql.core.v3.QueryExecutorImpl.receiveErrorResponse(QueryExecutorImpl.java:2553)",
        "deployment_context": "Automated morning price catalog sync triggered concurrent batch updates.",
        "root_cause": "Concurrent un-ordered batch row updates acquiring locks in conflicting sequence across worker threads.",
        "ground_truth_root_cause": "Concurrent un-ordered batch row updates acquiring locks in conflicting sequence across worker threads.",
        "negative_actions": ["Increase worker thread pool size", "Increase transaction timeout"],
        "known_failed_actions": ["Increase worker thread pool size", "Increase transaction timeout"],
        "verified_fix": "Sort inventory item IDs before locking and enforce ordered batch updates.",
        "expected_action_type": "SORT_LOCK_ORDER"
    },
    {
        "id": "HOLD-301",
        "service": "billing-service",
        "severity": "P1",
        "timestamp": "2026-10-22T16:04:30Z",
        "title": "Upstream bank partner rate limit exhaustion cascading into billing backlog",
        "symptoms": "HTTP 429 Too Many Requests received from banking webhook partner. Outbound charge queue backed up by 42,000 requests.",
        "stack_trace": "com.company.billing.exception.BankPartnerThrottleException: HTTP 429: Partner rate limit exceeded (100 req/s)\n  at com.company.billing.client.BankApiClient.charge(BankApiClient.java:114)",
        "deployment_context": "Black Friday pre-launch testing triggered high-frequency batch settlement calls.",
        "root_cause": "Lack of client-side token bucket rate limiting and exponential backoff with jitter on bank API calls.",
        "ground_truth_root_cause": "Lack of client-side token bucket rate limiting and exponential backoff with jitter on bank API calls.",
        "negative_actions": ["Scale billing-service pod replicas", "Retry immediately without backoff"],
        "known_failed_actions": ["Scale billing-service pod replicas", "Retry immediately without backoff"],
        "verified_fix": "Enforce client-side token bucket rate limiter at 85 req/s with exponential backoff and jitter.",
        "expected_action_type": "RATE_LIMIT_JITTER"
    },
    {
        "id": "HOLD-401",
        "service": "analytics-worker",
        "severity": "P2",
        "timestamp": "2026-11-01T11:20:00Z",
        "title": "Kafka partition rebalance storm due to oversized batch processing",
        "symptoms": "Consumer group 'analytics-pipeline' flapping. Continuous rebalancing every 5 minutes. CPU usage near 100%.",
        "stack_trace": "org.apache.kafka.clients.consumer.CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member.\n  at org.apache.kafka.clients.consumer.internals.ConsumerCoordinator.sendOffsetCommitRequest(ConsumerCoordinator.java:1120)",
        "deployment_context": "Ingested 10x larger telemetry batch from marketing partner.",
        "root_cause": "Batch processing time exceeded max.poll.interval.ms (300,000ms), causing consumer coordinator to kick worker from group.",
        "ground_truth_root_cause": "Batch processing time exceeded max.poll.interval.ms (300,000ms), causing consumer coordinator to kick worker from group.",
        "negative_actions": ["Restart analytics-worker pods", "Increase number of consumer partitions"],
        "known_failed_actions": ["Restart analytics-worker pods", "Increase number of consumer partitions"],
        "verified_fix": "Increase max.poll.interval.ms to 600000 and reduce max.poll.records from 1000 to 250.",
        "expected_action_type": "TUNE_KAFKA_POLL"
    },
    {
        "id": "HOLD-501",
        "service": "notification-worker",
        "severity": "P1",
        "timestamp": "2026-11-04T04:18:22Z",
        "title": "Metaspace ClassLoader memory leak during dynamic template compiles",
        "symptoms": "Notification pods crashing every 4 hours with java.lang.OutOfMemoryError: Metaspace. JVM heap remains healthy at 40%.",
        "stack_trace": "java.lang.OutOfMemoryError: Metaspace\n  at java.base/java.lang.ClassLoader.defineClass1(Native Method)\n  at java.base/java.lang.ClassLoader.defineClass(ClassLoader.java:1017)\n  at com.company.notification.template.DynamicCompiler.compile(DynamicCompiler.java:73)",
        "deployment_context": "New rich-email template engine deployed v3.1.0.",
        "root_cause": "Dynamic template compiler creating anonymous ClassLoaders for every template without caching or unloading.",
        "ground_truth_root_cause": "Dynamic template compiler creating anonymous ClassLoaders for every template without caching or unloading.",
        "negative_actions": ["Increase JVM heap -Xmx from 2G to 4G", "Restart pods"],
        "known_failed_actions": ["Increase JVM heap -Xmx from 2G to 4G", "Restart pods"],
        "verified_fix": "Enable compiled template ClassLoader caching and configure -XX:MaxMetaspaceSize=512m.",
        "expected_action_type": "CACHE_CLASSLOADER"
    },
    {
        "id": "HOLD-601",
        "service": "document-archiver",
        "severity": "P2",
        "timestamp": "2026-11-06T14:30:00Z",
        "title": "Amazon S3 503 SlowDown throttling during un-prefixed batch export",
        "symptoms": "S3 API returning HTTP 503 SlowDown on PutObject calls. Export throughput dropped from 80MB/s to 4MB/s.",
        "stack_trace": "com.amazonaws.services.s3.model.AmazonS3Exception: Slow Down (Service: Amazon S3; Status Code: 503; Error Code: SlowDown; Request ID: K9182371982)",
        "deployment_context": "Daily invoice archiving job writing 200,000 objects to single bucket prefix /invoices/2026/.",
        "root_cause": "Exceeding S3 request limit of 3,500 PUT/POST requests per second per prefix due to un-partitioned key naming.",
        "ground_truth_root_cause": "Exceeding S3 request limit of 3,500 PUT/POST requests per second per prefix due to un-partitioned key naming.",
        "negative_actions": ["Increase worker concurrency", "Disable HTTP retries"],
        "known_failed_actions": ["Increase worker concurrency", "Disable HTTP retries"],
        "verified_fix": "Introduce randomized hash prefix partitioning for S3 object keys (e.g. /invoices/{hash}/).",
        "expected_action_type": "S3_KEY_PARTITIONING"
    }
]

HOLDOUT_IDS = {inc["id"] for inc in HOLDOUT_INCIDENTS}
