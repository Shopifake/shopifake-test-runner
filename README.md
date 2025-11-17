# Shopifake Test Runner

Python-based test orchestrator for Shopifake microservices. Executes system, load, and chaos tests in different environments.

## Features

- **System Tests**: Health checks and E2E tests for all microservices
- **Load Tests**: Performance testing with Locust (staging only)
- **Chaos Tests**: Chaos engineering tests (staging only)
- **Multi-mode**: Works in PR (local docker-compose) and staging (K8s) environments
- **GitHub Integration**: Automatic PR creation and email notifications

## Architecture

```
shopifake-test-runner/
├── src/
│   ├── cli.py              # CLI entry point (Click)
│   ├── config.py           # Configuration management (Pydantic)
│   ├── orchestrator.py     # Test orchestration logic
│   └── tests/
│       ├── system/         # System/health tests (Pytest)
│       ├── load/           # Load tests (Locust)
│       └── chaos/          # Chaos tests
├── Dockerfile              # Multi-stage production image
├── requirements.txt        # Python dependencies
└── pyproject.toml          # Project configuration
```

## Usage

### CLI Commands

```bash
# Run system tests in PR mode (local docker-compose)
python -m src.cli run --mode pr --suite system

# Run all tests in staging mode (deployed environment)
python -m src.cli run --mode staging --suite all

# Run with custom base URL
python -m src.cli run --mode pr --suite system --base-url http://gateway:8080

# Display version
python -m src.cli version
```

### Docker

```bash
# Build image
docker build -t shopifake-test-runner:latest .

# Run in PR mode
docker run --rm \
  --network compose_default \
  -e MODE=pr \
  -e BASE_URL=http://gateway:8080 \
  shopifake-test-runner:latest \
  run --mode pr --suite system

# Run in staging mode
docker run --rm \
  -e MODE=staging \
  -e BASE_URL=https://staging-api.shopifake.com \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  shopifake-test-runner:latest \
  run --mode staging --suite all
```

### Kubernetes Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: staging-tests
  namespace: shopifake
spec:
  template:
    spec:
      containers:
      - name: test-runner
        image: ghcr.io/shopifake/shopifake-test-runner:latest
        command: ["python", "-m", "src.cli", "run"]
        args: ["--mode", "staging", "--suite", "all"]
        env:
        - name: BASE_URL
          value: "https://staging-api.shopifake.com"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token
              key: token
      restartPolicy: Never
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODE` | Execution mode: `pr` or `staging` | - |
| `BASE_URL` | API Gateway base URL | `http://localhost:8080` (pr), `https://staging-api.shopifake.com` (staging) |
| `TIMEOUT` | Request timeout in seconds | `60` (pr), `300` (staging) |
| `GITHUB_TOKEN` | GitHub API token for PR creation | - |

### Modes

#### PR Mode
- Tests against local docker-compose stack
- System tests only
- Fast execution (~1-2 minutes)
- Exit code indicates success/failure

#### Staging Mode
- Tests against deployed staging environment
- All test suites (system + load + chaos)
- Longer execution (~10-15 minutes)
- Creates promotion PR on success
- Sends email notification on failure

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests locally
pytest src/tests/system -v

# Format code
black src/
ruff check src/
```

### Testing

```bash
# Run system tests against local stack
docker-compose -f compose/system-tests.compose.yml up -d
python -m src.cli run --mode pr --suite system
docker-compose -f compose/system-tests.compose.yml down
```

## CI/CD Integration

### PR Workflow (dev → staging)

```yaml
- name: Run system tests
  run: |
    docker run --rm \
      --network compose_default \
      -e MODE=pr \
      -e BASE_URL=http://localhost:8080 \
      ghcr.io/shopifake/shopifake-test-runner:latest \
      run --mode pr --suite system
```

### Staging Workflow (post-merge)

```yaml
- name: Deploy test job to K8s
  run: |
    kubectl create job staging-tests-$(date +%s) \
      --image=ghcr.io/shopifake/shopifake-test-runner:latest \
      -- run --mode staging --suite all
```

## License

MIT
