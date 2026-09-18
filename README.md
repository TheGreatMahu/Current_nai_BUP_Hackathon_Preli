# GridWise LLM - BUP CSE Fest 2026

An LLM-Assisted Smart Campus Energy Optimization API developed for the BUP CSE Fest 2026 Hackathon Preliminary Round.

## System Architecture
- **LLM Engine:** Groq API (Qwen Model) with Few-Shot Prompting.
- **Validation Pipeline:** Custom deterministic Guardrails to ensure 100% schema compliance.
- **API Framework:** FastAPI for high-performance async HTTP requests.

---

## 🚀 Setup & Run Locally

### 1. Requirements
- Python 3.10+
- A valid Groq API Key

### 2. Installation
Clone the repository and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file inside the `app/llm/` directory and add your API key:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the API Server
Start the Uvicorn server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
The API will be available at: http://localhost:8000/

### 5. Run Tests
To verify all 39 mathematical constraint tests and public sample cases:
```bash
pytest
```

---

## 🐳 Run via Docker

You can also easily deploy the project using Docker.

### 1. Build the Docker Image
```bash
docker build -t gridwise-llm .
```

### 2. Run the Container
```bash
docker run -p 8000:8000 gridwise-llm
```

The API endpoints (`GET /health` and `POST /optimize-energy`) will now be accessible via `http://localhost:8000/`.