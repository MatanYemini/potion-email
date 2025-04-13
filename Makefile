.PHONY: setup check run neo4j-start neo4j-stop neo4j-logs test-gemini help clean

# Check for docker-compose vs docker compose command format
DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null || echo "docker compose")

# Default target
help:
	@echo "Potion Email Security - Makefile Help"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup         Set up the environment (venv, dependencies)"
	@echo "  make check         Run prerequisites check"
	@echo "  make run           Run the main email analysis"
	@echo "  make neo4j-start   Start Neo4j container"
	@echo "  make neo4j-stop    Stop Neo4j container"
	@echo "  make neo4j-logs    View Neo4j container logs"
	@echo "  make test-gemini   Test Gemini API integration"
	@echo "  make clean         Clean up temporary files"
	@echo ""
	@echo "Using Docker Compose command: $(DOCKER_COMPOSE)"
	@echo ""

# Set up the environment
setup:
	@echo "Setting up environment..."
	./setup.sh

# Check prerequisites
check:
	@echo "Checking prerequisites..."
	./check_prereqs.py

# Run the main analysis
run:
	@echo "Running main analysis..."
	python main.py

# Start Neo4j
neo4j-start:
	@echo "Starting Neo4j container..."
	$(DOCKER_COMPOSE) up -d neo4j

# Stop Neo4j
neo4j-stop:
	@echo "Stopping Neo4j container..."
	$(DOCKER_COMPOSE) stop neo4j

# View Neo4j logs
neo4j-logs:
	@echo "Viewing Neo4j container logs..."
	$(DOCKER_COMPOSE) logs -f neo4j

# Test Gemini API integration
test-gemini:
	@echo "Testing Gemini API integration..."
	./test_gemini.py

# Clean up
clean:
	@echo "Cleaning up temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	@echo "Clean complete!" 