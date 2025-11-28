# Use an official Python runtime as a parent image
# 3.11-slim is chosen for a balance between size and compatibility
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Install system dependencies if necessary (e.g., for SQLite or build tools)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8501 for Streamlit
EXPOSE 8501

# Healthcheck to ensure the container is ready
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Binded 0.0.0.0 to make the service accessible outside the container
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0"]