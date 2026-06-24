FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We use an entrypoint script to launch both servers
RUN echo '#!/bin/bash\n\n# Start the FastMCP SSE Server in background\npython mcp_server.py &\n\n# Start the FastAPI Web UI\nuvicorn api:app --host 0.0.0.0 --port 8000\n' > start.sh
RUN chmod +x start.sh

CMD ["./start.sh"]
