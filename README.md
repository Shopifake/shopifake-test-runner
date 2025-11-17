# Shopifake Test Runner

Dedicated Python-based test runner for Shopifake system tests, load tests, and chaos tests.

## Overview

This test runner is designed to orchestrate comprehensive testing of the Shopifake microservices platform:

- **System Tests**: Health checks and basic API validation through the API Gateway
- **Load Tests**: Performance testing using Locust
- **Chaos Tests**: Resilience testing using Chaos Mesh (staging only)

## Architecture

```
src/
├── cli.py                      # CLI entry point
├── config.py                   # Configuration management (PR vs Staging)
├── orchestrator.py             # Test orchestration logic
└── tests/
    ├── conftest.py             # Pytest configuration for all tests
    ├── system/                 # System tests (PR + Staging)
    │   ├── conftest.py
    │   └── test_health.py      # Health checks for all services
    ├── load/                   # Load tests (Staging only)
    │   ├── locustfile.py       # Locust entry point
    │   └── scenarios/          # Load test scenarios
    │       └── health.py       # Health check scenario
    ├── chaos/                  # Chaos tests (Staging only)
    │   ├── conftest.py         # K8s fixtures
    │   ├── helpers/
    │   │   └── chaos_helper.py # Chaos Mesh wrapper
    │   ├── test_pod_failures.py
    │   ├── test_network_chaos.py
    │   ├── test_stress.py
    │   └── test_combined_load_chaos.py
    └── helpers/
        └── api_client.py       # HTTP client with retry logic
```

## Usage

### CLI

The test runner provides a simple CLI:

```bash
# PR mode - run system tests only
python -m src.cli --mode pr --suite system --verbose

# Staging mode - run all test suites
python -m src.cli --mode staging --suite all --verbose

# Staging mode - run specific suite
python -m src.cli --mode staging --suite chaos
```

### Docker

```bash
# Build image
docker build -t shopifake-test-runner .

# Run in PR mode
docker run --rm \
  -e BASE_URL=http://gateway:8080 \
  shopifake-test-runner \
  --mode pr --suite system --verbose

# Run in Staging mode with Kubernetes access
docker run --rm \
  -v $KUBECONFIG:/root/.kube/config:ro \
  -e BASE_URL=https://staging-api.shopifake.com \
  -e K8S_NAMESPACE=staging \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  shopifake-test-runner \
  --mode staging --suite all --verbose
```

## Test Suites

### System Tests

Health checks for all microservices through the API Gateway:

- Spring Boot services: `/actuator/health` → expects `status: 'UP'`
- Python/FastAPI services: `/health` → expects HTTP 200
- Auth services (Node.js): `/healthz` → expects `status: 'UP'`

**Runs in:** PR and Staging environments

### Load Tests

Performance testing using Locust:

- Configurable via environment variables:
  - `LOCUST_USERS` (default: 10)
  - `LOCUST_SPAWN_RATE` (default: 2)
  - `LOCUST_RUN_TIME` (default: 60s)
- Generates HTML and CSV reports in `reports/`

**Runs in:** Staging environment only

**Current scenarios:**
- Health checks (simple load test)

**To add new scenarios:**
1. Create `src/tests/load/scenarios/your_scenario.py`
2. Implement a class with a `run(self)` method
3. Add it as a `@task` in `locustfile.py`

### Chaos Tests

Resilience testing using Chaos Mesh:

**Prerequisite:** Chaos Mesh must be installed in your Kubernetes cluster. See [CHAOS_MESH_SETUP.md](./CHAOS_MESH_SETUP.md).

**Test types:**
- **Pod Failures:** Kill pods and verify recovery
- **Network Chaos:** Inject latency, packet loss, partitions
- **Stress:** CPU and memory stress testing
- **Combined:** Load testing during chaos injection

**Runs in:** Staging environment only

**Environment variables:**
- `KUBECONFIG`: Path to Kubernetes config
- `K8S_NAMESPACE`: Kubernetes namespace (default: `staging`)

## Configuration

Configuration is managed via `src/config.py` using Pydantic:

### PR Mode
- `BASE_URL`: http://localhost:8080 (Docker Compose)
- Tests: System only
- No PR creation or email notifications

### Staging Mode
- `BASE_URL`: https://staging-api.shopifake.com
- Tests: All suites (system, load, chaos)
- Optional PR creation on success
- Optional email notification on failure

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BASE_URL` | API Gateway URL | Yes | - |
| `K8S_NAMESPACE` | Kubernetes namespace | Staging only | `staging` |
| `KUBECONFIG` | Path to kubeconfig | Staging only | - |
| `GITHUB_TOKEN` | GitHub API token | For PR creation & result posting | - |
| `GITHUB_REPO` | GitHub repo (org/name) | For PR creation & result posting | `shopifake/shopifake-back` |
| `GITHUB_SHA` | Git commit SHA | For posting results to commit | - |
| `POST_RESULTS_TO_GITHUB` | Post test results to GitHub | Staging | `true` |
| `LOCUST_USERS` | Number of concurrent users | Load tests | `10` |
| `LOCUST_SPAWN_RATE` | User spawn rate per second | Load tests | `2` |
| `LOCUST_RUN_TIME` | Load test duration | Load tests | `60s` |

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run system tests locally
python -m src.cli --mode pr --suite system --verbose

# Run specific test file
pytest src/tests/system/test_health.py -v

# Run chaos tests (requires K8s access)
pytest src/tests/chaos/test_pod_failures.py -m chaos -v
```

### Adding New Tests

#### System Tests
1. Create test file in `src/tests/system/`
2. Use `api_client` fixture from `conftest.py`
3. Test via API Gateway (`/api/{service}/...`)

#### Load Tests
1. Create scenario in `src/tests/load/scenarios/`
2. Implement class with `run(self)` method using `self.client`
3. Add as `@task` in `locustfile.py`

#### Chaos Tests
1. Create test file in `src/tests/chaos/`
2. Use `@pytest.mark.chaos` decorator
3. Use fixtures: `k8s_custom_client`, `namespace`, `chaos_mesh_group`, `chaos_mesh_version`
4. Use `ChaosHelper` for creating/deleting chaos experiments

## CI/CD Integration

### PR Workflow (`.github/workflows/pr-dev-tests.yml`)
1. Checkout code
2. Pull all service images
3. Start Docker Compose stack
4. Pull test runner image
5. Run test runner in PR mode: `--mode pr --suite system`

### Staging Workflow (`.github/workflows/merge-staging-tests.yml`)
1. Deploy test runner as Kubernetes Job
2. Job runs: `--mode staging --suite all`
3. Test runner handles:
   - Running all test suites
   - Creating promotion PR on success
   - Sending email notification on failure

## Reports

All test suites generate HTML reports in the `reports/` directory:

- `reports/system.html`: System test results (Pytest HTML)
- `reports/load.html`: Load test results (Locust HTML)
- `reports/load_stats.csv`: Load test statistics
- `reports/chaos.html`: Chaos test results (Pytest HTML)

These reports can be collected as CI artifacts for review.

## Troubleshooting

### System Tests Failing

1. Check service health manually:
   ```bash
   curl http://localhost:8080/actuator/health
   curl http://localhost:8080/api/catalog/actuator/health
   ```

2. Check Docker Compose logs:
   ```bash
   docker compose -f compose/system-tests.compose.yml logs catalog
   ```

### Load Tests Failing

1. Check Locust configuration:
   ```bash
   echo $LOCUST_USERS $LOCUST_SPAWN_RATE $LOCUST_RUN_TIME
   ```

2. Run Locust interactively:
   ```bash
   locust -f src/tests/load/locustfile.py --host http://localhost:8080
   # Open http://localhost:8089
   ```

### Chaos Tests Failing

1. Verify Chaos Mesh installation:
   ```bash
   kubectl get pods -n chaos-mesh
   kubectl get crd | grep chaos-mesh
   ```

2. Check RBAC permissions:
   ```bash
   kubectl auth can-i create podchaos -n staging
   ```

3. Check experiment status:
   ```bash
   kubectl get podchaos,networkchaos,stresschaos -n staging
   ```

4. View experiment details:
   ```bash
   kubectl describe podchaos <name> -n staging
   ```

## License

MIT
