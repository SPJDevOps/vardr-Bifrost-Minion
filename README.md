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