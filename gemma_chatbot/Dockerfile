FROM python:3.11-slim
# Set the working directory
WORKDIR /app
# Copy the requirements file
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add the directory where pip installs command-line scripts to the PATH
ENV PATH="/root/.local/bin:${PATH}"
# Copy the application code
COPY . .
# Expose the port the app runs on
EXPOSE 8000
# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]