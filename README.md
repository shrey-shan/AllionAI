# AllionAI – Voice Agent Setup

This project runs a LiveKit-based voice agent in two modes:

- **Console Mode** → Local testing in your terminal  
- **Dev/Web Mode** → Connect to the hosted frontend: [AllionAI Web App](https://agent-starter-react-sigma.vercel.app/)

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
OPENAI_BASE_URL=<base_url_if_using_openrouter>
```

---

## 5. Download Required Files
```bash
python src/<voice_agent_file>.py download-files
```

---

## 6. Run in Console Mode (Local Testing)
```bash
python src/<voice_agent_file>.py console
```
- Use your microphone to talk to the agent in the terminal.  
- Ideal for quick debugging and testing.

---

## 7. Run in Dev Mode (Connect to Web App)
```bash
python src/voice_agent.py dev
```
- Starts the LiveKit agent worker and joins the specified room.  
- Go to the frontend web app:  
  👉 [https://agent-starter-react-sigma.vercel.app/](https://agent-starter-react-sigma.vercel.app/)  
- Enter the same room name as in `.env` (`LIVEKIT_ROOM`) to interact with your agent via browser.
