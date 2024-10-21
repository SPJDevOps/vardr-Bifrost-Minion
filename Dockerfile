# Step 1: Use an official Python runtime as a base image
FROM python:3.11-slim

# Step 2: Set environment variables to ensure Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Step 3: Install Node.js and NPM (to ensure NPM is available)
# Use curl to fetch and install Node.js and NPM
RUN apt-get update && apt-get install -y curl gnupg2 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && apt-get install -y maven \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Step 4: Set the working directory in the container
WORKDIR /app

# Step 5: Copy the requirements file and install dependencies
COPY requirements.txt /app/

# Install dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Copy the entire application code into the working directory
COPY . /app/

# Step 7: Expose the port FastAPI will be running on (adjust if you're using a different port)
EXPOSE 8000

# Step 8: Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]