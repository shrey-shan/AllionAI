# AllionAI – Voice Agent Setup

This project runs a LiveKit-based voice agent in two modes:

- **Console Mode** → Local testing in your terminal  
- **Dev/Web Mode** → Connect to the hosted frontend: [AllionAI Web App](https://agent-starter-react-sigma.vercel.app/)

```bash
AllionAI/
├── docs/pdf_source/
├── src/
│   ├── configs/
│   │   ├── __init__.py
│   │   └── rag_config.py
│   ├── assistant_core.py
│   ├── rag_capabilities.py
│   └── vision_capabilities.py
├── scripts/
│   ├── setup_rag.py
│   └── test_rag.py
└── requirements.txt
└── requirements_rag.txt
```
---

## 1. Clone the Repository
```bash
git clone https://github.com/shrey-shan/AllionAI.git
cd AllionAI
```

---

## 2. Create a Virtual Environment and Activate It
**Windows**
```bash
python -m venv allion
allion\Scripts\activate
```
**macOS / Linux**
```bash
python -m venv allion
source allion/bin/activate
```

---

## 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_rag.txt
```

---

## 4. Setup Environment Variables
Create a `.env` file in the project root:

```env
# LiveKit Connection
LIVEKIT_URL=wss://<your_project_id>.livekit.cloud
LIVEKIT_API_KEY=<your_api_key>
LIVEKIT_API_SECRET=<your_api_secret>

# Agent Settings
LIVEKIT_ROOM=my-test-room
AGENT_ID=agent1

# Model Provider
OPENAI_API_KEY=<your_openai_or_openrouter_key>
```

---

## 5. Setup RAG Vector Store (One-Time)
If you plan to use the RAG (Retrieval-Augmented Generation) capabilities with your own PDF documents, run this script once to process them and create the local vector database.

```bash
python scripts/setup_rag.py
```
- Place your PDF files in the `docs/pdf_source/` directory before running.

---

## 6. Download Required Files
```bash
python -m src.multilingual_agent download-files
```

---

## 6. Run in Console Mode (Local Testing)
```bash
python -m src.multilingual_agent en console
```
- Use your microphone to talk to the agent in the terminal.  
- Ideal for quick debugging and testing.

---

## 7. Run in Dev Mode (Connect to Web App)
```bash
python -m src.multilingual_agent dev
```
- Starts the LiveKit agent worker and joins the specified room.  
- Go to the frontend web app:  
  👉Custom  : [https://agent-starter-react-custom.vercel.app/](http://agent-starter-react-custom.vercel.app/)
- Enter the same room name as in `.env` (`LIVEKIT_ROOM`) to interact with your agent via browser.
