# Mini AI Health Coach

A WhatsApp-like AI health coaching chat application with persistent conversation history, long-term memory, and protocol-based responses.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (for PostgreSQL and Redis)

### 1. Start Database Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your API key
# For OpenAI:
#   LLM_PROVIDER=openai
#   OPENAI_API_KEY=sk-your-key-here
#
# For Anthropic:
#   LLM_PROVIDER=anthropic
#   ANTHROPIC_API_KEY=sk-ant-your-key-here

# Seed the database with protocols
python -m app.seed_data

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Open the App

Navigate to [http://localhost:5173](http://localhost:5173)

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/health_coach` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | LLM provider: `openai` or `anthropic` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) | - |
| `LLM_MODEL` | Model name | `gpt-4-turbo-preview` |
| `MAX_CONTEXT_TOKENS` | Max tokens for context window | `8000` |
| `MAX_RESPONSE_TOKENS` | Max tokens for response | `1000` |

---

## Architecture Overview

![Architecture Diagram](./architechture.png)


### Key Design Decisions

1. **Cursor-Based Pagination**: Uses timestamps instead of offset for efficient infinite scroll. Handles real-time message additions without duplicates.

2. **Strategy Pattern for LLM**: Swappable providers (OpenAI/Claude) via config. Easy to add new providers.

3. **Token Budget Management**: Automatically truncates older messages to fit context window. Reserves tokens for system prompt, protocols, and memories.

4. **Background Memory Extraction**: Memories are extracted asynchronously after each exchange to avoid blocking the response.

5. **Single Session Design**: One user, one continuous conversation (like WhatsApp). No session management complexity.

---

## API Endpoints

### `GET /api/chat/init`
Initialize chat session. Creates user if new, returns onboarding greeting.

### `GET /api/chat/history?cursor=<timestamp>&limit=20`
Cursor-based pagination for chat history. Scroll up to load older messages.

### `POST /api/chat/send`
Send message and get AI response. Body: `{ "content": "message text" }`

### `GET /api/chat/typing`
Poll for typing indicator status.

---

## LLM Notes

### Provider Selection
Set `LLM_PROVIDER` in `.env`:
- `openai` (default) - Uses GPT-4 Turbo
- `anthropic` - Uses Claude 3 Sonnet

### Prompting Strategy

The system prompt is built dynamically with:

1. **Base Personality**: Friendly, WhatsApp-like conversational style
2. **Safety Guidelines**: Never diagnose, recommend emergency services when needed
3. **Matched Protocols**: Injected when keywords match (fever, headache, etc.)
4. **User Memories**: Previous facts about the user
5. **Onboarding Mode**: Extra instructions for new users

### Context Window Management

```
┌────────────────────────────────────────┐
│          MAX_CONTEXT_TOKENS            │
│  ┌──────────────────────────────────┐  │
│  │ System Prompt (~500 tokens)      │  │
│  ├──────────────────────────────────┤  │
│  │ Matched Protocols (~500 tokens)  │  │
│  ├──────────────────────────────────┤  │
│  │ User Memories (~200 tokens)      │  │
│  ├──────────────────────────────────┤  │
│  │ Chat History (remaining budget)  │  │  ← Oldest messages truncated first
│  ├──────────────────────────────────┤  │
│  │ Current Message                  │  │
│  └──────────────────────────────────┘  │
│  Reserved: MAX_RESPONSE_TOKENS         │
└────────────────────────────────────────┘
```

---

## Trade-offs & "If I Had More Time..."

### Current Trade-offs

| Decision | Trade-off | Rationale |
|----------|-----------|-----------|
| Keyword-based protocol matching | Less accurate than embeddings | Simpler, no vector DB needed |
| Keyword-based memory retrieval | May miss semantic matches | Avoids embedding costs per query |
| Polling for typing indicator | More requests than WebSocket | Simpler implementation |
| Single user session | No multi-user support | Matches assignment requirement |
| Synchronous LLM calls | Blocks until response | Simpler than streaming |

### If I Had More Time...

1. **Streaming Responses**: Use SSE/WebSocket to stream LLM responses token-by-token for better UX.

2. **Vector Search for Memories**: Add pgvector embeddings for semantic memory retrieval instead of keyword matching.

3. **WebSocket for Real-time**: Replace polling with WebSocket for typing indicators and instant message delivery.

4. **Message Read Receipts**: Track when messages are read (blue ticks like WhatsApp).

5. **Rate Limiting**: Add rate limiting to prevent abuse.

6. **User Authentication**: Add proper JWT-based auth for multi-user support.

7. **Message Reactions**: Allow emoji reactions to messages.

8. **Voice Messages**: Support audio input/output.

9. **Conversation Summarization**: Periodically summarize old conversations to compress context.

10. **Caching Layer**: Cache protocol matches and recent context in Redis.

11. **Observability**: Add structured logging, metrics, and tracing.

12. **Testing**: Add unit tests, integration tests, and E2E tests.

---

## Troubleshooting

### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker-compose ps
docker-compose logs db
```

### Redis Connection Failed
```bash
# Check if Redis is running
docker-compose logs redis
```

### LLM API Errors
- Verify your API key in `.env`
- Check you have credits/quota with your provider
- Ensure `LLM_PROVIDER` matches your API key

### Frontend Can't Connect to Backend
- Ensure backend is running on port 8000
- Check CORS settings if running on different ports
- Verify the Vite proxy config in `vite.config.ts`

# Health-Coach-FE
