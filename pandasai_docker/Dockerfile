FROM python:3.9

LABEL image_name="pandasai-sandbox"

# Install required Python packages
RUN pip install pandas==2.2.3 numpy matplotlib seaborn plotly

# Set the working directory inside the container
WORKDIR /app

# Default command keeps the container running (useful for testing or debugging)
CMD ["sleep", "infinity"]