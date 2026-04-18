from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"
sys.path.insert(0, str(AGENT_DIR))

from agent import configure_logging, get_settings, save_memory, search_past_incidents  # noqa: E402

logger = logging.getLogger("seed_memory")


@dataclass(frozen=True)
class IncidentSeed:
    incident_id: str
    category: str
    title: str
    severity: str
    services: list[str]
    description: str
    root_cause: str
    resolution_steps: list[str]
    time_to_resolve: str
    tags: list[str]


INCIDENTS: list[IncidentSeed] = []

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-db-2025-0412-01",
            category="database failures",
            title="Postgres connection pool exhaustion on api-prod-3",
            severity="P1",
            services=["api-gateway", "orders-service", "user-db"],
            description=(
                "Checkout requests timed out across us-east-1 after the orders-service deploy. "
                "api-prod-3 logs showed `psycopg_pool.PoolTimeout: couldn't get a "
                "connection after 30.00 sec`; Postgres emitted `FATAL: remaining "
                "connection slots are reserved for non-replication superuser connections`. "
                "Stack trace ended at `orders/repository.py:88 in create_order -> "
                "await session.execute(stmt)`."
            ),
            root_cause=(
                "A new async worker path opened a transaction before calling the fraud "
                "service and held idle connections during the remote call."
            ),
            resolution_steps=[
                "Set `DB_POOL_MAX=18` and `DB_POOL_TIMEOUT=5s` on orders-service.",
                "Moved the fraud-service call outside the transaction boundary.",
                "Killed 42 idle-in-transaction sessions using `pg_terminate_backend`.",
                "Rolled out orders-service build `2025.04.12.3` to api-prod-3 first.",
            ],
            time_to_resolve="47 minutes",
            tags=["database", "postgres", "connection-pool", "checkout", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-db-2025-0320-02",
            category="database failures",
            title="Aurora writer failover left read replicas serving stale inventory",
            severity="P1",
            services=["inventory-service", "catalog-api", "aurora-inventory"],
            description=(
                "Inventory counts froze for 18 minutes during an Aurora writer failover. "
                "catalog-api returned stale stock while logs showed `SQLSTATE[HY000] "
                "[2006] MySQL server has gone away` and `ReplicaLagMaximum=742`. "
                "Trace: `InventoryClient.reserve -> mysql.connector.cursor_cext.execute "
                "-> OperationalError: 2013`."
            ),
            root_cause=(
                "The app cached the old writer endpoint IP because JVM DNS TTL was still "
                "set to forever in the inventory-service base image."
            ),
            resolution_steps=[
                "Set `networkaddress.cache.ttl=30` in JVM security properties.",
                "Restarted inventory-service pods in batches of 20 percent.",
                "Forced catalog-api to bypass read replicas until lag was below 5 seconds.",
                "Ran inventory reconciliation for affected SKUs.",
            ],
            time_to_resolve="1 hour 12 minutes",
            tags=["database", "aurora", "failover", "replica-lag", "inventory"],
        ),
        IncidentSeed(
            incident_id="inc-db-2025-0118-03",
            category="database failures",
            title="Redis primary memory pressure evicted checkout idempotency keys",
            severity="P2",
            services=["checkout-service", "redis-checkout", "payments-worker"],
            description=(
                "Duplicate payment attempts rose after Redis memory reached 97 percent. "
                "Logs showed `OOM command not allowed when used memory > maxmemory` and "
                "`IdempotencyKeyMissingError: key checkout:idem:pay_7781 not found` from "
                "`payments/idempotency.py:44`. Redis INFO reported `evicted_keys:184229`."
            ),
            root_cause=(
                "A promotion import job wrote large temporary SKU blobs into the same "
                "Redis cluster used for checkout idempotency."
            ),
            resolution_steps=[
                "Stopped the promotion import job and flushed only `promo:tmp:*` keys.",
                "Moved checkout idempotency keys to DB 3 with `volatile-ttl` policy.",
                "Raised Redis maxmemory from 12 GiB to 18 GiB after shard rebalance.",
                "Replayed payments-worker with duplicate guard enabled.",
            ],
            time_to_resolve="39 minutes",
            tags=["database", "redis", "eviction", "payments", "idempotency"],
        ),
        IncidentSeed(
            incident_id="inc-db-2025-0507-04",
            category="database failures",
            title="MongoDB index build saturated profile-service reads",
            severity="P2",
            services=["profile-service", "mongo-users", "web-app"],
            description=(
                "Profile pages p95 jumped to 9.8 seconds after an online index build. "
                "profile-service logs contained `MongoServerError: operation exceeded "
                "time limit` and stack `ProfileRepository.findByAccountId -> "
                "collection.findOne -> TimeoutError`."
            ),
            root_cause=(
                "The migration created a compound index on a 480M document collection "
                "during peak traffic without secondary-first rollout."
            ),
            resolution_steps=[
                "Aborted the active index build using `db.currentOp()` and `db.killOp()`.",
                "Shifted low-priority profile widget reads to the analytics secondary.",
                "Rebuilt the index during maintenance on a hidden secondary first.",
                "Promoted the indexed secondary after replication caught up.",
            ],
            time_to_resolve="58 minutes",
            tags=["database", "mongodb", "index-build", "latency", "profile-service"],
        ),
        IncidentSeed(
            incident_id="inc-db-2025-0226-05",
            category="database failures",
            title="DynamoDB hot partition throttled session writes",
            severity="P2",
            services=["session-service", "auth-service", "dynamodb-sessions"],
            description=(
                "Login success dropped to 91 percent for enterprise SSO tenants. "
                "CloudWatch showed `WriteThrottleEvents=15320` on key `tenant#global`. "
                "Node logs showed `ProvisionedThroughputExceededException: Rate exceeded` "
                "at `SessionStore.putSession (/srv/session/store.ts:119:17)`."
            ),
            root_cause=(
                "A fallback path used `tenant#global` when the tenant ID claim was absent "
                "in SAML assertions, creating a hot partition."
            ),
            resolution_steps=[
                "Patched session-service to derive tenant ID from issuer when claim is absent.",
                "Enabled adaptive capacity alarm paging at 60 percent throttle budget.",
                "Backfilled affected session records to tenant-specific partition keys.",
                "Temporarily doubled write capacity until retries drained.",
            ],
            time_to_resolve="51 minutes",
            tags=["database", "dynamodb", "hot-partition", "sessions", "auth"],
        ),
    ]
)

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-auth-2025-0419-01",
            category="auth service errors",
            title="JWKS cache missed key rotation for auth-service",
            severity="P1",
            services=["auth-service", "api-gateway", "mobile-api"],
            description=(
                "Mobile API returned 401 for valid users after signing key rotation. "
                "Gateway logs showed `JwtVerificationError: kid k-2025-04-19 not found "
                "in JWKS` and stack `JwtMiddleware.verify -> jose.jwtVerify`."
            ),
            root_cause=(
                "api-gateway cached JWKS for 24 hours and ignored the `Cache-Control: "
                "max-age=300` header from auth-service."
            ),
            resolution_steps=[
                "Flushed api-gateway JWKS cache through the admin endpoint.",
                "Rolled gateway patch to honor JWKS cache-control headers.",
                "Temporarily served both old and new signing keys from auth-service.",
                "Added synthetic login test that validates new `kid` after rotation.",
            ],
            time_to_resolve="29 minutes",
            tags=["auth", "jwks", "api-gateway", "key-rotation", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-auth-2025-0325-02",
            category="auth service errors",
            title="SSO callback loop after SameSite cookie change",
            severity="P2",
            services=["auth-service", "web-app", "sso-gateway"],
            description=(
                "Enterprise users looped between `/login` and `/sso/callback`. Browser "
                "console showed `state cookie missing`; auth-service logs had "
                "`InvalidOAuthState: expected cookie oauth_state not present` at "
                "`oauth/callback.py:146 validate_state`."
            ),
            root_cause=(
                "A security hardening change set the OAuth state cookie to `SameSite=Strict`, "
                "so identity-provider redirects did not include it."
            ),
            resolution_steps=[
                "Changed OAuth state cookie to `SameSite=None; Secure` for SSO callbacks.",
                "Rolled auth-service pods in the enterprise region first.",
                "Cleared stale login cookies for affected domains.",
                "Added browser integration test using cross-site IdP redirect.",
            ],
            time_to_resolve="37 minutes",
            tags=["auth", "sso", "cookies", "oauth", "enterprise"],
        ),
        IncidentSeed(
            incident_id="inc-auth-2025-0213-03",
            category="auth service errors",
            title="MFA verification failed after Twilio webhook signature update",
            severity="P2",
            services=["auth-service", "mfa-worker", "twilio-api"],
            description=(
                "MFA SMS verification success fell to 72 percent. mfa-worker logs showed "
                "`WebhookSignatureError: expected sha256 signature header missing` from "
                "`twilio_webhook.py:82 verify_signature`; callbacks used HMAC-SHA256."
            ),
            root_cause=(
                "Twilio upgraded webhook signing for the account, but mfa-worker only "
                "accepted the legacy SHA1 signature header."
            ),
            resolution_steps=[
                "Allowed both SHA1 and HMAC-SHA256 signature validators.",
                "Rotated webhook auth token and redeployed mfa-worker.",
                "Requeued pending MFA callback events from the webhook DLQ.",
                "Added contract test with both Twilio signature algorithms.",
            ],
            time_to_resolve="41 minutes",
            tags=["auth", "mfa", "twilio", "webhook", "signature"],
        ),
        IncidentSeed(
            incident_id="inc-auth-2025-0506-04",
            category="auth service errors",
            title="Password hash migration overloaded auth-db CPU",
            severity="P1",
            services=["auth-service", "auth-db", "login-api"],
            description=(
                "Login p95 reached 14 seconds and error rate hit 16 percent. Postgres "
                "logs showed `duration: 12842 ms execute update_user_hash`; auth-service "
                "stack `PasswordVerifier.verifyAndUpgrade -> UserRepository.saveHash`."
            ),
            root_cause=(
                "The lazy bcrypt-to-argon2 migration upgraded every successful login "
                "during peak traffic with no per-node throttle."
            ),
            resolution_steps=[
                "Disabled inline hash upgrades with `AUTH_HASH_UPGRADE_INLINE=false`.",
                "Moved migration to a background queue capped at 25 writes per second.",
                "Added partial index on users requiring hash upgrade.",
                "Scaled auth-db writer class one size up until queue drained.",
            ],
            time_to_resolve="55 minutes",
            tags=["auth", "database", "password-hash", "cpu", "login"],
        ),
        IncidentSeed(
            incident_id="inc-auth-2025-0122-05",
            category="auth service errors",
            title="API token introspection cache served revoked tokens",
            severity="P2",
            services=["auth-service", "api-gateway", "admin-api"],
            description=(
                "Revoked admin API tokens continued working for up to 20 minutes. Gateway "
                "logs showed `token_introspection_cache_hit=true revoked_at=2025-01-22T09:14Z` "
                "and stack `TokenIntrospector.authorize -> AdminGuard.requireScope`."
            ),
            root_cause=(
                "The positive introspection cache TTL was 20 minutes and revoke events "
                "were published to the wrong Kafka topic after a config rename."
            ),
            resolution_steps=[
                "Flushed api-gateway token introspection cache.",
                "Fixed revoke event topic from `auth.revokes` to `auth.token.revoked`.",
                "Reduced positive cache TTL to 2 minutes for admin scopes.",
                "Added audit query to confirm all revoked token IDs were denied.",
            ],
            time_to_resolve="32 minutes",
            tags=["auth", "token", "cache", "revocation", "admin-api"],
        ),
    ]
)

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-3p-2025-0408-01",
            category="third-party API outages",
            title="Stripe API elevated 500s delayed subscription renewals",
            severity="P1",
            services=["billing-service", "renewal-worker", "stripe-api"],
            description=(
                "Subscription renewals failed for 14 percent of attempts. billing-service "
                "logged `Stripe API error: status=500 request_id=req_7Ts1 latency=29010ms` "
                "and stack `stripe.Invoice.pay -> RenewalProcessor.chargeInvoice`."
            ),
            root_cause=(
                "Stripe had a regional API incident and renewal-worker retried too "
                "aggressively without honoring provider backoff headers."
            ),
            resolution_steps=[
                "Paused non-expiring renewals and kept only grace-window risk invoices.",
                "Enabled exponential backoff honoring `Stripe-Should-Retry`.",
                "Moved renewal-worker traffic to the provider secondary endpoint.",
                "Replayed delayed renewals after Stripe status returned green.",
            ],
            time_to_resolve="1 hour 27 minutes",
            tags=["third-party", "stripe", "billing", "api-outage", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-3p-2025-0306-02",
            category="third-party API outages",
            title="SendGrid rate limit caused password reset email delays",
            severity="P2",
            services=["notification-service", "auth-service", "sendgrid-api"],
            description=(
                "Password reset emails delayed up to 40 minutes. Logs showed "
                "`HTTP 429 Too Many Requests x-ratelimit-remaining=0` and stack "
                "`SendgridClient.sendTemplate -> ResetEmailHandler.handle`."
            ),
            root_cause=(
                "A marketing import used the transactional SendGrid subuser and consumed "
                "the hourly API quota."
            ),
            resolution_steps=[
                "Moved password reset templates to the backup SES provider.",
                "Paused marketing import and rotated it to the marketing-only subuser.",
                "Raised notification priority for auth reset jobs.",
                "Added provider quota partition alerts per subuser.",
            ],
            time_to_resolve="34 minutes",
            tags=["third-party", "sendgrid", "rate-limit", "email", "auth"],
        ),
        IncidentSeed(
            incident_id="inc-3p-2025-0218-03",
            category="third-party API outages",
            title="Maps provider latency broke address validation",
            severity="P3",
            services=["address-service", "checkout-service", "maps-provider"],
            description=(
                "Checkout address validation p95 hit 12 seconds. address-service logs "
                "showed `MapsProviderTimeout: GET /geocode exceeded 8000ms` at "
                "`AddressNormalizer.validate(AddressNormalizer.kt:91)`."
            ),
            root_cause=(
                "The maps provider degraded and address-service had no stale-cache "
                "fallback for previously validated addresses."
            ),
            resolution_steps=[
                "Enabled cached validation fallback for addresses seen in the prior 30 days.",
                "Raised checkout timeout budget only for address validation to 3 seconds.",
                "Skipped geocode enrichment for low-risk domestic addresses.",
                "Backfilled missing lat/lon fields after provider recovery.",
            ],
            time_to_resolve="46 minutes",
            tags=["third-party", "maps", "latency", "checkout", "fallback"],
        ),
        IncidentSeed(
            incident_id="inc-3p-2025-0501-04",
            category="third-party API outages",
            title="Fraud scoring vendor returned malformed JSON",
            severity="P2",
            services=["fraud-service", "orders-service", "fraud-vendor-api"],
            description=(
                "Order approvals dropped after fraud vendor returned HTML error pages "
                "with 200 status. Logs showed `json.decoder.JSONDecodeError: Expecting "
                "value` in `fraud/vendor_client.py:118 score_order`; body began `<html>`."
            ),
            root_cause=(
                "The vendor CDN edge returned branded error HTML with HTTP 200 during "
                "their WAF rules update."
            ),
            resolution_steps=[
                "Treated non-JSON vendor responses as retryable provider failures.",
                "Switched low-risk orders to internal heuristic scoring.",
                "Added content-type validation before JSON parse.",
                "Replayed held orders after vendor confirmed WAF rollback.",
            ],
            time_to_resolve="52 minutes",
            tags=["third-party", "fraud", "malformed-json", "orders", "fallback"],
        ),
        IncidentSeed(
            incident_id="inc-3p-2025-0117-05",
            category="third-party API outages",
            title="CDN purge API outage left stale config active",
            severity="P3",
            services=["edge-config-service", "cdn-provider", "web-app"],
            description=(
                "A bad banner config remained live after rollback. edge-config-service "
                "logged `CDN purge failed status=503 body=service unavailable` from "
                "`cdn_client.rb:58`; clients kept `x-edge-config-version: bad-2`."
            ),
            root_cause=(
                "The CDN purge API had a control-plane outage and rollback assumed purge "
                "completion before writing the config version pointer."
            ),
            resolution_steps=[
                "Changed edge config pointer to a new safe version instead of purging keys.",
                "Lowered banner config TTL from 600 seconds to 60 seconds.",
                "Retried purge after CDN status recovered.",
                "Added rollback path that writes forward to a safe immutable version.",
            ],
            time_to_resolve="31 minutes",
            tags=["third-party", "cdn", "purge", "edge-config", "rollback"],
        ),
    ]
)

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-mem-2025-0424-01",
            category="memory leaks",
            title="Node heap leak in websocket-presence-service",
            severity="P1",
            services=["presence-service", "websocket-gateway", "redis-presence"],
            description=(
                "WebSocket disconnects climbed to 38 percent. Pods restarted with "
                "`FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap "
                "out of memory`; stack contained `PresenceFanout.addSubscriber "
                "(/srv/presence/fanout.ts:142:19)`. Heap snapshots retained SubscriberRef."
            ),
            root_cause=(
                "Disconnected sockets were removed from Redis presence but not from the "
                "in-process fanout map when clients closed during reconnect."
            ),
            resolution_steps=[
                "Rolled presence-service to build `presence-2025.04.24.5` with cleanup.",
                "Lowered pod max connections to 8k during recovery.",
                "Restarted websocket-gateway pods in shards to drain leaked heaps.",
                "Added heap-used-percent alert at 75 percent for 10 minutes.",
            ],
            time_to_resolve="49 minutes",
            tags=["memory-leak", "nodejs", "websocket", "presence", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-mem-2025-0317-02",
            category="memory leaks",
            title="Java Metaspace leak after dynamic rules reload",
            severity="P2",
            services=["risk-engine", "rules-service", "kafka-risk"],
            description=(
                "risk-engine pods OOMKilled every 18 minutes after rules reload. JVM "
                "logs showed `java.lang.OutOfMemoryError: Metaspace` and stack "
                "`DynamicCompiler.compile(DynamicCompiler.java:203)`; nonheap memory rose."
            ),
            root_cause=(
                "Each rules reload created a new URLClassLoader and never closed the "
                "previous loader, retaining generated classes."
            ),
            resolution_steps=[
                "Disabled automatic rules reload and pinned rule bundle `risk-1442`.",
                "Restarted risk-engine deployment with max unavailable 1.",
                "Deployed fix closing old classloaders before swapping bundles.",
                "Reduced rules reload cadence from 5 minutes to 30 minutes.",
            ],
            time_to_resolve="57 minutes",
            tags=["memory-leak", "java", "metaspace", "risk-engine", "rules"],
        ),
        IncidentSeed(
            incident_id="inc-mem-2025-0214-03",
            category="memory leaks",
            title="Python worker leaked pandas frames during export jobs",
            severity="P2",
            services=["report-exporter", "analytics-db", "s3-export"],
            description=(
                "Report export latency crossed 20 minutes and workers were OOMKilled. "
                "Logs showed `MemoryError: Unable to allocate 512 MiB for an array` from "
                "`pandas/core/internals/managers.py`, stack `jobs.py:177 build_report`."
            ),
            root_cause=(
                "The exporter accumulated DataFrames in a global retry list after "
                "successful S3 upload, so completed exports were never released."
            ),
            resolution_steps=[
                "Disabled large-account exports through the feature flag.",
                "Patched exporter to clear retry state after successful upload.",
                "Processed exports in 50k row chunks instead of whole-account frames.",
                "Restarted exporter workers and replayed failed jobs from DLQ.",
            ],
            time_to_resolve="1 hour 4 minutes",
            tags=["memory-leak", "python", "pandas", "exports", "workers"],
        ),
        IncidentSeed(
            incident_id="inc-mem-2025-0502-04",
            category="memory leaks",
            title="Go cache map growth exhausted recommendation-service pods",
            severity="P2",
            services=["recommendation-service", "catalog-api", "redis-recs"],
            description=(
                "recommendation-service RSS grew from 600 MiB to 5.6 GiB. pprof heap "
                "showed `main.(*FeatureCache).Set` retaining 4.1 GiB. Logs before OOM "
                "had `runtime: out of memory` from `feature_cache.go:86`."
            ),
            root_cause=(
                "A new cache key included a request UUID, preventing cache hits and "
                "bypassing the intended LRU eviction path."
            ),
            resolution_steps=[
                "Disabled in-process feature cache with `FEATURE_CACHE_MODE=redis-only`.",
                "Rolled back recommendation-service to `rec-2025.05.01.2`.",
                "Deployed corrected key function using user segment and SKU only.",
                "Added pprof heap-delta alert tied to cache cardinality.",
            ],
            time_to_resolve="45 minutes",
            tags=["memory-leak", "golang", "cache", "recommendations", "oom"],
        ),
        IncidentSeed(
            incident_id="inc-mem-2025-0106-05",
            category="memory leaks",
            title="Nginx ingress buffer leak on large file uploads",
            severity="P3",
            services=["nginx-ingress", "media-upload", "object-storage"],
            description=(
                "Large media uploads failed intermittently with 499 and 502. Ingress "
                "logs showed `upstream prematurely closed connection`; worker stderr had "
                "`malloc() failed (12: Cannot allocate memory) while reading upstream`."
            ),
            root_cause=(
                "The ingress image had a temp-file cleanup bug triggered by cancelled "
                "multipart uploads larger than 250 MiB."
            ),
            resolution_steps=[
                "Rolled nginx-ingress from `1.9.3-company2` to patched `1.9.6-company1`.",
                "Reduced `proxy-body-size` to 200 MiB until direct upload shipped.",
                "Deleted orphaned temp files and restarted ingress pods one AZ at a time.",
                "Moved media-upload clients to direct S3 multipart URLs.",
            ],
            time_to_resolve="38 minutes",
            tags=["memory-leak", "nginx", "uploads", "ingress", "media"],
        ),
    ]
)

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-deploy-2025-0415-01",
            category="deployment rollbacks",
            title="Bad feature flag migration caused account-service 500s",
            severity="P1",
            services=["account-service", "feature-flag-api", "web-app"],
            description=(
                "Account settings page returned 500 after release `acct-2025.04.15`. "
                "Logs showed `TypeError: Cannot read properties of undefined (reading "
                "'rollout')` at `flags/provider.ts:211:28`, followed by Express stack "
                "`AccountController.renderSettings -> FlagProvider.variant`."
            ),
            root_cause=(
                "The release expected the new `settings_v2` flag schema before the "
                "migration job had completed in production."
            ),
            resolution_steps=[
                "Rolled back account-service to `acct-2025.04.14.7` using Argo Rollouts.",
                "Pinned `settings_v2=false` at the global flag layer.",
                "Ran the flag schema migration and verified all rows updated.",
                "Redeployed the new build with preflight schema check enabled.",
            ],
            time_to_resolve="33 minutes",
            tags=["deployment", "rollback", "feature-flags", "account-service", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-deploy-2025-0328-02",
            category="deployment rollbacks",
            title="Canary release of pricing-service miscomputed annual discounts",
            severity="P2",
            services=["pricing-service", "checkout-service", "billing-ui"],
            description=(
                "Canary users saw annual plan discounts doubled. pricing-service logs "
                "showed `discount_basis=annualized annual_multiplier=12 applied_twice=true`. "
                "Stack trace: `PriceCalculator.applyAnnualDiscount -> PromotionEngine.evaluate`."
            ),
            root_cause=(
                "A refactor applied annual normalization in both the promotion engine and "
                "the quote formatter for canary cohort users."
            ),
            resolution_steps=[
                "Paused the canary at 8 percent and promoted stable revision to 100 percent.",
                "Invalidated cached quotes with tag `pricing:annual:v2`.",
                "Added regression test for annual promotion stacking.",
                "Issued corrected quotes for 214 affected checkout sessions.",
            ],
            time_to_resolve="42 minutes",
            tags=["deployment", "rollback", "pricing", "canary", "checkout"],
        ),
        IncidentSeed(
            incident_id="inc-deploy-2025-0209-03",
            category="deployment rollbacks",
            title="Helm chart update removed worker liveness probe",
            severity="P2",
            services=["image-worker", "media-service", "kubernetes"],
            description=(
                "Image processing backlog grew to 1.8M jobs. Pods stayed Running while "
                "logs stopped after `SharpWorker initialized`. Node stack dump showed "
                "`QueueConsumer.poll (/srv/worker/consumer.ts:88:13)` blocked on Redis."
            ),
            root_cause=(
                "The shared worker Helm chart renamed `livenessProbe` to `probes.liveness`, "
                "and image-worker values were not migrated."
            ),
            resolution_steps=[
                "Rolled back chart version from `worker-2.12.0` to `worker-2.11.4`.",
                "Manually restarted stuck image-worker pods.",
                "Replayed image jobs older than 15 minutes with lower concurrency.",
                "Added chart schema validation to CI for worker values files.",
            ],
            time_to_resolve="53 minutes",
            tags=["deployment", "rollback", "helm", "workers", "media"],
        ),
        IncidentSeed(
            incident_id="inc-deploy-2025-0509-04",
            category="deployment rollbacks",
            title="Frontend release served stale API contract to mobile web",
            severity="P3",
            services=["web-app", "api-gateway", "profile-service"],
            description=(
                "Mobile web users could not save profile edits after release `web-8f31c2`. "
                "Browser logs reported `PATCH /v2/profile 400 missing required field "
                "display_name`; server trace showed `ProfileUpdateRequest.kt:39`."
            ),
            root_cause=(
                "A CDN cache rule kept the previous JavaScript bundle while the backend "
                "started enforcing the new profile payload field."
            ),
            resolution_steps=[
                "Purged CDN keys for `/assets/profile-*` and `/index.html`.",
                "Rolled profile-service validation to warn-only for 30 minutes.",
                "Republished web build with content-hashed API client chunk.",
                "Added synthetic mobile-web save test before backend enforcement.",
            ],
            time_to_resolve="26 minutes",
            tags=["deployment", "cdn", "api-contract", "frontend", "rollback"],
        ),
        IncidentSeed(
            incident_id="inc-deploy-2025-0112-05",
            category="deployment rollbacks",
            title="Terraform apply replaced queue security group ingress",
            severity="P2",
            services=["event-ingestor", "sqs-consumer", "terraform", "aws-security-groups"],
            description=(
                "Event ingestion lag hit 72 minutes after infra apply. Consumers logged "
                "`403 AccessDenied: not authorized to perform sqs:ReceiveMessage` and "
                "Terraform output showed `forces replacement` on `queue_consumers`."
            ),
            root_cause=(
                "A Terraform module upgrade changed the IAM role name suffix and the "
                "queue policy still referenced the old exact ARN."
            ),
            resolution_steps=[
                "Rolled back Terraform module to `sqs-consumer-1.8.2`.",
                "Updated queue policy to use role path wildcard for the consumer family.",
                "Replayed event-ingestor backlog with concurrency capped at 50.",
                "Added plan check to block role replacement without queue policy diff.",
            ],
            time_to_resolve="1 hour 8 minutes",
            tags=["deployment", "terraform", "iam", "queue", "rollback"],
        ),
    ]
)

INCIDENTS.extend(
    [
        IncidentSeed(
            incident_id="inc-net-2025-0401-01",
            category="network issues",
            title="Istio sidecar DNS failures broke payments callbacks",
            severity="P1",
            services=["payments-api", "callback-worker", "istio-proxy", "coredns"],
            description=(
                "Payment provider callbacks returned 502 for 22 percent of requests. "
                "Envoy logs showed `upstream connect error or disconnect/reset before "
                "headers` with `DNS resolution failed`. callback-worker emitted "
                "`java.net.UnknownHostException` from `WebhookVerifier.java:74`."
            ),
            root_cause=(
                "An Istio sidecar injection update changed DNS capture behavior, but the "
                "payments namespace still used legacy CoreDNS stub domains."
            ),
            resolution_steps=[
                "Disabled DNS capture for payments namespace using proxy metadata override.",
                "Restarted payments-api and callback-worker pods to reload sidecars.",
                "Added the provider webhook hostname to the mesh ServiceEntry.",
                "Replayed missed callbacks from the provider dashboard.",
            ],
            time_to_resolve="44 minutes",
            tags=["networking", "dns", "istio", "payments", "webhooks"],
        ),
        IncidentSeed(
            incident_id="inc-net-2025-0303-02",
            category="network issues",
            title="NAT gateway port exhaustion blocked outbound email delivery",
            severity="P2",
            services=["notification-service", "email-worker", "aws-nat-gateway"],
            description=(
                "Transactional emails queued for 31 minutes. Worker logs showed "
                "`connect ETIMEDOUT 52.14.88.22:443` and `SMTP provider API request "
                "failed after 3 retries`. VPC metrics had `ErrorPortAllocation=2841` "
                "and `PacketsDropCount` climbing on nat-az-a."
            ),
            root_cause=(
                "A newsletter backfill opened short-lived HTTPS connections without "
                "keepalive, exhausting ephemeral ports on the single NAT gateway in az-a."
            ),
            resolution_steps=[
                "Paused the newsletter backfill queue.",
                "Spread notification-service pods across three availability zones.",
                "Enabled HTTP keepalive with max 200 sockets per worker.",
                "Provisioned a NAT gateway per AZ and updated private route tables.",
            ],
            time_to_resolve="1 hour 6 minutes",
            tags=["networking", "nat-gateway", "email", "timeouts", "aws"],
        ),
        IncidentSeed(
            incident_id="inc-net-2025-0211-03",
            category="network issues",
            title="Internal ALB target health flapped for search-api",
            severity="P2",
            services=["search-api", "internal-alb", "recommendations-service"],
            description=(
                "Recommendations timed out when calling search-api. ALB logs showed "
                "`target_status_code=- elb_status_code=504`, while pods logged "
                "`BrokenPipeError: [Errno 32] Broken pipe`. Target health alternated "
                "between healthy and unhealthy every 90 seconds."
            ),
            root_cause=(
                "The health check path performed an Elasticsearch ping and exceeded the "
                "new 2 second timeout during normal cluster merge activity."
            ),
            resolution_steps=[
                "Changed ALB health check to `/healthz/live` without downstream checks.",
                "Kept `/healthz/ready` for Kubernetes readiness only.",
                "Raised ALB unhealthy threshold from 2 to 5 during rollout.",
                "Restarted search-api pods to clear half-open sockets.",
            ],
            time_to_resolve="36 minutes",
            tags=["networking", "alb", "health-check", "search", "timeouts"],
        ),
        IncidentSeed(
            incident_id="inc-net-2025-0504-04",
            category="network issues",
            title="Regional packet loss between api-gateway and billing-service",
            severity="P1",
            services=["api-gateway", "billing-service", "linkerd", "vpc-peering"],
            description=(
                "Invoice creation failed for eu-west customers. Linkerd metrics showed "
                "`tcp_open_errors_total` up 18x and gateway logs had `read: connection "
                "reset by peer` in Go stack `net/http.(*persistConn).roundTrip`."
            ),
            root_cause=(
                "A provider route table change sent eu-west billing traffic over a "
                "degraded peering link with 12 percent packet loss."
            ),
            resolution_steps=[
                "Shifted eu-west billing traffic to the secondary region through weighted DNS.",
                "Disabled HTTP/2 reuse in api-gateway for billing-service until loss cleared.",
                "Pinned route table to the healthy peering attachment.",
                "Replayed failed invoice creation jobs from the durable queue.",
            ],
            time_to_resolve="1 hour 19 minutes",
            tags=["networking", "packet-loss", "billing", "regional-failover", "p1"],
        ),
        IncidentSeed(
            incident_id="inc-net-2025-0129-05",
            category="network issues",
            title="Kubernetes NetworkPolicy blocked metrics ingestion",
            severity="P3",
            services=["metrics-agent", "prometheus", "observability-gateway"],
            description=(
                "Prometheus scrape coverage dropped from 98 percent to 63 percent. "
                "metrics-agent logged `dial tcp 10.43.18.22:9090: i/o timeout`; "
                "Prometheus targets showed `context deadline exceeded`."
            ),
            root_cause=(
                "The new default-deny NetworkPolicy omitted egress from metrics-agent to "
                "the observability-gateway namespace."
            ),
            resolution_steps=[
                "Added explicit egress allow rule for TCP 9090 and 4317.",
                "Applied the policy first to staging and then production.",
                "Restarted metrics-agent daemonset to refresh conntrack state.",
                "Backfilled dashboards from remote-write buffer.",
            ],
            time_to_resolve="28 minutes",
            tags=["networking", "networkpolicy", "observability", "prometheus", "kubernetes"],
        ),
    ]
)



INCIDENTS.extend([
        IncidentSeed(
            incident_id="inc-2024-204",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-204)",
            severity="P2",
            services=['billing-worker', 'orders-service', 'recommendations-db'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="37 minutes",
            tags=['auth-service-errors', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-551",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-551)",
            severity="P2",
            services=['search-api', 'frontend-node', 'auth-service'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="81 minutes",
            tags=['network-issues', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-943",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-943)",
            severity="P1",
            services=['search-api', 'recommendations-db', 'auth-service'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="27 minutes",
            tags=['network-issues', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-800",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2024-800)",
            severity="P3",
            services=['api-gateway', 'user-db'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="73 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-583",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-583)",
            severity="P3",
            services=['billing-worker', 'auth-service'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="60 minutes",
            tags=['auth-service-errors', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-324",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-324)",
            severity="P1",
            services=['search-api', 'billing-worker', 'auth-service'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="64 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-380",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-380)",
            severity="P1",
            services=['billing-worker', 'media-uploader', 'api-gateway', 'search-api'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="37 minutes",
            tags=['network-issues', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-694",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2025-694)",
            severity="P1",
            services=['media-uploader', 'search-api', 'auth-service', 'recommendations-db'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="30 minutes",
            tags=['memory-leaks', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-246",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2025-246)",
            severity="P3",
            services=['frontend-node', 'recommendations-db', 'media-uploader', 'billing-worker'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="23 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-735",
            category="database failures",
            title="Synthetic simulated database failures (inc-2024-735)",
            severity="P2",
            services=['auth-service', 'media-uploader'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="96 minutes",
            tags=['database-failures', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-133",
            category="third-party API outages",
            title="Synthetic simulated third-party API outages (inc-2024-133)",
            severity="P3",
            services=['orders-service', 'search-api'],
            description="Simulated outage in third-party API outages. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="55 minutes",
            tags=['third-party-API-outages', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-215",
            category="third-party API outages",
            title="Synthetic simulated third-party API outages (inc-2024-215)",
            severity="P1",
            services=['billing-worker', 'recommendations-db', 'orders-service', 'frontend-node'],
            description="Simulated outage in third-party API outages. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="101 minutes",
            tags=['third-party-API-outages', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-495",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-495)",
            severity="P2",
            services=['api-gateway', 'user-db', 'orders-service', 'frontend-node'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="91 minutes",
            tags=['network-issues', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-788",
            category="third-party API outages",
            title="Synthetic simulated third-party API outages (inc-2025-788)",
            severity="P1",
            services=['user-db', 'recommendations-db'],
            description="Simulated outage in third-party API outages. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="64 minutes",
            tags=['third-party-API-outages', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-566",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-566)",
            severity="P1",
            services=['orders-service', 'auth-service'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="114 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-834",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-834)",
            severity="P1",
            services=['recommendations-db', 'media-uploader', 'billing-worker', 'api-gateway'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="91 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-414",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-414)",
            severity="P3",
            services=['auth-service', 'recommendations-db', 'media-uploader', 'frontend-node'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="44 minutes",
            tags=['auth-service-errors', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-399",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-399)",
            severity="P2",
            services=['search-api', 'recommendations-db', 'orders-service', 'api-gateway'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="33 minutes",
            tags=['network-issues', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-621",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-621)",
            severity="P3",
            services=['recommendations-db', 'user-db', 'api-gateway'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="104 minutes",
            tags=['auth-service-errors', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-321",
            category="database failures",
            title="Synthetic simulated database failures (inc-2024-321)",
            severity="P2",
            services=['frontend-node', 'search-api', 'media-uploader'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="89 minutes",
            tags=['database-failures', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-614",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-614)",
            severity="P1",
            services=['frontend-node', 'api-gateway', 'auth-service', 'media-uploader'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="46 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-792",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-792)",
            severity="P1",
            services=['auth-service', 'recommendations-db', 'user-db', 'media-uploader'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="55 minutes",
            tags=['network-issues', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-392",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2024-392)",
            severity="P3",
            services=['frontend-node', 'recommendations-db', 'billing-worker', 'auth-service'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="97 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-988",
            category="database failures",
            title="Synthetic simulated database failures (inc-2025-988)",
            severity="P1",
            services=['recommendations-db', 'auth-service', 'media-uploader', 'api-gateway'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="96 minutes",
            tags=['database-failures', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-629",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2024-629)",
            severity="P3",
            services=['frontend-node', 'auth-service', 'api-gateway'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="41 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-993",
            category="deployment rollbacks",
            title="Synthetic simulated deployment rollbacks (inc-2025-993)",
            severity="P3",
            services=['media-uploader', 'billing-worker', 'api-gateway', 'search-api'],
            description="Simulated outage in deployment rollbacks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="54 minutes",
            tags=['deployment-rollbacks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-649",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-649)",
            severity="P3",
            services=['frontend-node', 'search-api', 'api-gateway'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="48 minutes",
            tags=['network-issues', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-334",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2024-334)",
            severity="P1",
            services=['user-db', 'recommendations-db', 'api-gateway'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="48 minutes",
            tags=['memory-leaks', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-768",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-768)",
            severity="P1",
            services=['orders-service', 'media-uploader'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="117 minutes",
            tags=['network-issues', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-440",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-440)",
            severity="P2",
            services=['billing-worker', 'orders-service'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="54 minutes",
            tags=['network-issues', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-475",
            category="database failures",
            title="Synthetic simulated database failures (inc-2024-475)",
            severity="P1",
            services=['frontend-node', 'auth-service', 'search-api', 'recommendations-db'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="84 minutes",
            tags=['database-failures', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-637",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-637)",
            severity="P1",
            services=['media-uploader', 'api-gateway', 'recommendations-db', 'user-db'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="79 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-234",
            category="database failures",
            title="Synthetic simulated database failures (inc-2025-234)",
            severity="P1",
            services=['frontend-node', 'search-api', 'billing-worker'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="53 minutes",
            tags=['database-failures', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-835",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2025-835)",
            severity="P3",
            services=['recommendations-db', 'user-db', 'frontend-node', 'search-api'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="87 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-717",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-717)",
            severity="P3",
            services=['search-api', 'recommendations-db'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="21 minutes",
            tags=['network-issues', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-236",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-236)",
            severity="P3",
            services=['user-db', 'orders-service', 'auth-service', 'recommendations-db'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="27 minutes",
            tags=['auth-service-errors', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-770",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-770)",
            severity="P1",
            services=['media-uploader', 'search-api'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="32 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-206",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2025-206)",
            severity="P2",
            services=['search-api', 'api-gateway', 'orders-service'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="117 minutes",
            tags=['memory-leaks', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-985",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-985)",
            severity="P2",
            services=['recommendations-db', 'user-db', 'orders-service'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="40 minutes",
            tags=['auth-service-errors', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-194",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-194)",
            severity="P2",
            services=['search-api', 'orders-service'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="108 minutes",
            tags=['auth-service-errors', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-956",
            category="database failures",
            title="Synthetic simulated database failures (inc-2024-956)",
            severity="P3",
            services=['auth-service', 'recommendations-db'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="102 minutes",
            tags=['database-failures', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-762",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2024-762)",
            severity="P1",
            services=['recommendations-db', 'api-gateway', 'orders-service', 'media-uploader'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="110 minutes",
            tags=['auth-service-errors', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-298",
            category="network issues",
            title="Synthetic simulated network issues (inc-2024-298)",
            severity="P1",
            services=['auth-service', 'user-db', 'media-uploader'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="69 minutes",
            tags=['network-issues', 'p1', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-108",
            category="auth service errors",
            title="Synthetic simulated auth service errors (inc-2025-108)",
            severity="P2",
            services=['auth-service', 'recommendations-db', 'billing-worker'],
            description="Simulated outage in auth service errors. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="53 minutes",
            tags=['auth-service-errors', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-684",
            category="network issues",
            title="Synthetic simulated network issues (inc-2025-684)",
            severity="P2",
            services=['search-api', 'recommendations-db', 'user-db', 'auth-service'],
            description="Simulated outage in network issues. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="101 minutes",
            tags=['network-issues', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-245",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2025-245)",
            severity="P2",
            services=['auth-service', 'api-gateway', 'media-uploader', 'search-api'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="80 minutes",
            tags=['memory-leaks', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-777",
            category="third-party API outages",
            title="Synthetic simulated third-party API outages (inc-2025-777)",
            severity="P2",
            services=['frontend-node', 'search-api'],
            description="Simulated outage in third-party API outages. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="68 minutes",
            tags=['third-party-API-outages', 'p2', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2024-585",
            category="memory leaks",
            title="Synthetic simulated memory leaks (inc-2024-585)",
            severity="P3",
            services=['media-uploader', 'billing-worker', 'recommendations-db', 'search-api'],
            description="Simulated outage in memory leaks. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="80 minutes",
            tags=['memory-leaks', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-905",
            category="database failures",
            title="Synthetic simulated database failures (inc-2025-905)",
            severity="P3",
            services=['search-api', 'frontend-node', 'user-db'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="52 minutes",
            tags=['database-failures', 'p3', 'synthetic']
        ),

        IncidentSeed(
            incident_id="inc-2025-981",
            category="database failures",
            title="Synthetic simulated database failures (inc-2025-981)",
            severity="P2",
            services=['api-gateway', 'user-db'],
            description="Simulated outage in database failures. Traffic impacted. CPU spiked to 100%.",
            root_cause="Automated simulation found configuration error.",
            resolution_steps=["Rolled back to previous version.", "Restarted impacted pods.", "Cleared cache."],
            time_to_resolve="109 minutes",
            tags=['database-failures', 'p2', 'synthetic']
        ),
])

def render_incident(incident: IncidentSeed) -> str:
    """Render one incident as the structured memory document saved to Hindsight."""

    resolution = "\n".join(
        f"{index}. {step}" for index, step in enumerate(incident.resolution_steps, start=1)
    )
    return f"""incident_id: {incident.incident_id}
category: {incident.category}
title: {incident.title}
severity: {incident.severity}
services_affected: {", ".join(incident.services)}
description:
{incident.description}
root_cause_found: {incident.root_cause}
exact_resolution_steps_that_worked:
{resolution}
time_to_resolve: {incident.time_to_resolve}
tags: [{", ".join(incident.tags)}]
status: resolved
source: production incident runbook seed
"""


def seed_incidents() -> None:
    """Save all incident memories to Hindsight."""

    logger.info("Seeding %s production incidents into Hindsight", len(INCIDENTS))
    for incident in INCIDENTS:
        context = (
            f"seed_incident category={incident.category} severity={incident.severity} "
            f"tags={','.join(incident.tags)}"
        )
        memory_id = save_memory(render_incident(incident), context=context)
        logger.info("Seeded %s as %s - %s", incident.incident_id, memory_id, incident.title)


def verify_seed() -> None:
    """Verify database incident recall returns at least three results."""

    logger.info("Verifying seeded memory with query: database connection error")
    result = search_past_incidents.invoke("database connection error")
    result_text = str(result)
    hits = result_text.count("Past incident ")

    print('\nVerification query: search_past_incidents("database connection error")')
    print(result_text)

    if hits < 3:
        raise RuntimeError(
            "Expected at least 3 recalled database incidents, "
            f"but search_past_incidents returned {hits}."
        )
    logger.info("Verification passed with %s recalled incidents", hits)


def main() -> None:
    configure_logging()
    if not get_settings().hindsight_api_key:
        raise RuntimeError(
            "HINDSIGHT_API_KEY is required. Set it in .env or the current shell before "
            "running `py -m scripts.seed_memory`."
        )

    seed_incidents()
    verify_seed()


if __name__ == "__main__":
    main()
