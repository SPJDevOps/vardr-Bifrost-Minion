# Application README

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Creating a Virtual Environment](#creating-a-virtual-environment)
  - [Installing Dependencies](#installing-dependencies)
- [Development](#development)
  - [Running the Application Locally](#running-the-application-locally)
- [Docker](#docker)
  - [Building the Docker Image](#building-the-docker-image)
  - [Running the Docker Container](#running-the-docker-container)
- [Application Structure](#application-structure)
  - [Processors](#processors)
  - [RabbitMQ Queues](#rabbitmq-queues)
- [Usage](#usage)
- [Additional Notes](#additional-notes)
- [License](#license)

---

## Introduction

This application is designed to process various types of dependencies such as Docker images, Maven artifacts, Python packages, NPM packages, Helm charts, and files from URLs. It follows a consistent three-step processing pattern:

1. **Download Step**: Fetch the dependency.
2. **Packaging Step**: Package the dependency into a tarball.
3. **Sending Step**: Send the tarball to a specified HTTP endpoint.

The application utilizes RabbitMQ for message queuing, allowing processors to handle tasks asynchronously.

---

## Prerequisites

Before setting up and running the application, ensure you have the following installed on your system:

- **Python 3.11** or higher
- **Docker** and **Docker Compose**
- **RabbitMQ** (if not using Docker for RabbitMQ)
- **Node.js** and **NPM** (for NPM package processing)
- **Helm** (for Helm chart processing)
- **Git** (for version control)

---

## Setup

### Creating a Virtual Environment

It's recommended to use a Python virtual environment to manage dependencies and isolate the project environment.

1. **Create a virtual environment**:

   ```bash
   python3.11 -m venv env
   ```

2. **Activate the virtual environment**:

   - On **Linux/macOS**:

     ```bash
     source env/bin/activate
     ```

   - On **Windows**:

     ```bash
     .\env\Scripts\activate
     ```

### Installing Dependencies

1. **Upgrade `pip`**:

   ```bash
   pip install --upgrade pip
   ```

2. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js and NPM dependencies** (if not already installed):

   - **Linux/macOS**:

     ```bash
     # Install Node.js and NPM
     curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
     sudo apt-get install -y nodejs
     ```

   - **Windows**:

     Download and install Node.js from the [official website](https://nodejs.org/).

4. **Install Helm** (for Helm chart processing):

   Follow the installation instructions from the [Helm official documentation](https://helm.sh/docs/intro/install/).

---

## Development

### Running the Application Locally

To run the application for development purposes:

1. **Ensure RabbitMQ is running**:

   - If you have RabbitMQ installed locally, start the service.
   - Alternatively, you can run RabbitMQ using Docker:

     ```bash
     docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 rabbitmq:3
     ```

2. **Set environment variables** (if needed):

   You can configure your application using environment variables or a `.env` file.

3. **Start the application**:

   ```bash
   uvicorn app.main:app --reload
   ```

   The `--reload` flag enables auto-reloading on code changes, which is useful during development.

---

## Docker

### Building the Docker Image

To containerize the application using Docker:

1. **Build the Docker image**:

   ```bash
   docker build -t my-application .
   ```

   This command builds an image with the tag `my-application` using the `Dockerfile` in the current directory.

### Running the Docker Container

1. **Run the Docker container**:

   ```bash
   docker run -d \
       --name my-application-container \
       -p 8000:8000 \
       -v /var/run/docker.sock:/var/run/docker.sock \
       my-application
   ```

   - `-p 8000:8000`: Maps port 8000 of the container to port 8000 on the host.
   - `-v /var/run/docker.sock:/var/run/docker.sock`: Mounts the Docker socket to enable Docker operations within the container.

2. **Verify the container is running**:

   ```bash
   docker ps
   ```

   You should see `my-application-container` listed and running.

---

## Application Structure

### Processors

The application uses processors to handle different types of dependencies. Each processor follows the same three-step pattern:

1. **Download Step**: Handles the downloading of the specified dependency.
2. **Packaging Step**: Packages the downloaded files into a tarball.
3. **Sending Step**: Sends the tarball to an HTTP endpoint.

#### Available Processors

- **DockerProcessor**: Handles Docker images.
- **MavenProcessor**: Handles Maven artifacts.
- **PythonPackageProcessor**: Handles Python packages.
- **NpmPackageProcessor**: Handles NPM packages.
- **FileDownloadProcessor**: Handles file downloads from URLs.
- **HelmChartProcessor**: Handles Helm charts.

### RabbitMQ Queues

The application uses RabbitMQ for message passing between components.

#### Queues

- **request_queue**: Receives new `HyperloopDownload` tasks.
- **status_queue**: Receives status updates from processors.

#### Message Flow

1. **Producer**: Sends `HyperloopDownload` messages to `request_queue`.
2. **Consumer**: Listens to `request_queue` and dispatches tasks to the appropriate processor based on the `type` field.
3. **Processor**: Processes the task and sends status updates to `status_queue`.

---

## Usage

To use the application:

1. **Send a `HyperloopDownload` task**:

   Send a message to `request_queue` or make an HTTP POST request to the `/downloads` endpoint (if available) with a JSON payload:

   ```json
   {
     "type": "DOCKER",
     "dependency": "nginx:latest"
   }
   ```

2. **Monitor the status**:

   Listen to `status_queue` to receive status updates or check logs for processing details.

3. **Processing Steps**:

   The processor will:

   - Download the specified dependency.
   - Package it into a tarball.
   - Send the tarball to the configured HTTP endpoint.

---

## Additional Notes

- **Docker-in-Docker**:

  - The application needs to interact with the Docker daemon to pull Docker images.
  - We mount the Docker socket from the host into the container using `-v /var/run/docker.sock:/var/run/docker.sock`.
  - Be aware of the security implications of this approach.

- **Environment Variables**:

  - Configure your application using environment variables or a `.env` file.
  - Common variables include RabbitMQ connection details and HTTP endpoint URLs.

- **Security Considerations**:

  - Ensure that sensitive information is not hardcoded or exposed.
  - Use proper authentication and authorization mechanisms where necessary.

- **Logging**:

  - The application prints logs to the console.
  - Consider integrating a logging framework for better log management.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support, please open an issue or contact the maintainers.

# Acknowledgments

Thank you for using this application. Contributions are welcome!

# Download Minion

A FastStream-based download processing service that handles various types of dependencies and packages.

## Architecture

This application uses **FastStream** with **RabbitMQ** for message processing, which provides:

- **Simplified Message Handling**: No need for manual RabbitMQ connection management
- **Automatic Message Routing**: FastStream handles message routing and processing
- **Built-in Error Handling**: Automatic retry and error handling mechanisms
- **Async/Await Support**: Full async support for better performance
- **Smart Error Handling**: Different error types are handled appropriately (reject vs retry)
- **Clean Architecture**: BaseProcessor pattern eliminates code duplication

## Features

The service can process the following types of downloads:

- **DOCKER**: Docker images (pulls, saves as tarball)
- **MAVEN**: Maven artifacts and dependencies
- **PYTHON**: Python packages and wheels
- **NPM**: NPM packages and dependencies
- **FILE**: Direct file downloads from URLs
- **HELM**: Helm charts with Docker image extraction
- **WEBSITE**: Website to PDF conversion

## Clean Architecture

The application uses a **BaseProcessor** pattern to eliminate code duplication:

### BaseProcessor Class
```python
class BaseProcessor(ABC):
    """Base class for all download processors with common functionality"""
    
    async def process(self, download):
        # Common processing pipeline for all processors
        await self.download_step(download)
        await self.packaging_step(download)
        await self.sending_step(download)
        self.cleanup_temp_files(download)
    
    @abstractmethod
    async def _download_dependency(self, download):
        # Each processor implements its specific download logic
        pass
```

### Benefits of BaseProcessor Pattern
- **🔄 Consistent Processing**: All processors follow the same 3-step pipeline
- **📦 Automatic Packaging**: Base class handles tarball creation
- **📤 Automatic Sending**: Base class handles NiFi upload
- **🧹 Automatic Cleanup**: Base class handles file cleanup
- **📊 Status Updates**: Base class handles status publishing
- **🎯 Error Handling**: Base class handles common error scenarios

### Processor Implementation
Each processor only needs to implement its specific download logic:

```python
class DockerProcessor(BaseProcessor):
    async def _download_dependency(self, download):
        # Only Docker-specific logic here
        docker_image = download.dependency
        self.docker_client.images.pull(docker_image)
        # Save as tarball...
```

## Error Handling

The application implements intelligent error handling with different strategies:

### Message Rejection (No Retry)
Messages are **rejected** (not retried) for:
- **Invalid download type**: Unknown processor type
- **Invalid input format**: Malformed Maven coordinates, invalid URLs
- **Dependency not found**: Non-existent Docker images, Maven artifacts, etc.

### Message Retry (Negative Acknowledgment)
Messages are **retried** for:
- **Network errors**: Connection timeouts, temporary network issues
- **Service errors**: Docker API errors, Maven repository issues
- **Internal errors**: Unexpected exceptions, system errors

### Error Types

```python
# Reject immediately (no retry)
class UserInputError(Exception):
    """Invalid user input - reject message"""

class DependencyNotFoundError(Exception):
    """Dependency doesn't exist - reject message"""

# Retry later
class InternalError(Exception):
    """Internal processing error - retry message"""
```

## Setup

### Prerequisites

- Python 3.8+
- RabbitMQ server
- Docker (for Docker image processing)
- Node.js/npm (for NPM package processing)
- Maven (for Maven artifact processing)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export RABBITMQ_HOST="amqp://guest:guest@localhost:5672/"
export RABBITMQ_DOWNLOAD_REQUEST_QUEUE="private.hyperloop.download_requests"
export RABBITMQ_DOWNLOAD_STATUS_QUEUE="private.hyperloop.download_status"
```

## Running the Application

### Method 1: Using the run script
```bash
python run.py
```

### Method 2: Using FastStream CLI
```bash
faststream run app.main:app --host 0.0.0.0 --port 8000
```

### Method 3: Using Uvicorn directly
```bash
uvicorn app.main:fastapi_app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

- `GET /`: Health check endpoint
- `POST /publish`: Publish a message to the download request queue

## Message Format

Send messages to the download request queue in this format:

```json
{
  "id": 1,
  "type": "DOCKER",
  "dependency": "nginx:latest",
  "status": "STARTED",
  "date": "2024-01-01T00:00:00"
}
```

## Queue Structure

- **Download Request Queue**: Receives download requests
- **Download Status Queue**: Publishes status updates

## Processing Flow

1. Message received on download request queue
2. FastStream automatically routes to appropriate processor
3. Processor downloads and packages the dependency
4. Status updates published to status queue
5. Final tarball sent to NiFi endpoint

## Testing Error Handling

Run the test script to see how different error scenarios are handled:

```bash
python test_error_handling.py
```

This will demonstrate:
- ✅ Valid messages (processed successfully)
- ❌ User input errors (rejected immediately)
- ❌ Dependency not found errors (rejected immediately)
- ⚠️ Internal errors (retried later)

## Benefits of FastStream + BaseProcessor

- **Reduced Code**: Eliminated ~200 lines of manual RabbitMQ setup
- **Eliminated Duplication**: BaseProcessor pattern reduces processor code by ~80%
- **Better Error Handling**: Automatic retry and dead letter queues
- **Type Safety**: Better type hints and validation
- **Simplified Testing**: Easier to test with FastStream's testing utilities
- **Performance**: Optimized async processing
- **Smart Error Handling**: Different strategies for different error types
- **Maintainability**: Single place to change common logic

## Development

The application structure is now much cleaner:

```
app/
├── main.py                    # FastStream app configuration
├── processors/
│   ├── base_processor.py      # Base class with common functionality
│   ├── download_router.py     # FastStream router with error handling
│   ├── docker_processor.py    # Only Docker-specific logic (~30 lines)
│   ├── maven_processor.py     # Only Maven-specific logic (~30 lines)
│   ├── python_package_processor.py
│   ├── npm_package_processor.py
│   ├── file_download_processor.py
│   ├── helm_chart_processor.py
│   └── website_pdf_processor.py
├── models/
│   ├── download_status.py
│   └── hyperloop_download.py
└── helpers/
    └── nifi_uploader.py
```

## Code Reduction

### Before (Original Processors)
- **Docker Processor**: ~112 lines
- **Maven Processor**: ~177 lines
- **Python Processor**: ~121 lines
- **Total**: ~410 lines with lots of duplication

### After (BaseProcessor Pattern)
- **BaseProcessor**: ~120 lines (shared functionality)
- **Docker Processor**: ~45 lines (only Docker-specific logic)
- **Maven Processor**: ~35 lines (only Maven-specific logic)
- **Python Processor**: ~25 lines (only Python-specific logic)
- **Total**: ~225 lines (45% reduction, no duplication)

## Monitoring

FastStream provides built-in monitoring and observability features. Check the logs for processing status and any errors.

### Error Logging

The application logs different error types with appropriate actions:
- `User input error - rejecting message`: Message rejected, no retry
- `Internal error - will retry`: Message will be retried later
- `Unexpected error - will retry`: Message will be retried later