# Architecture Diagrams

Enterprise-style diagrams rendered with **Mermaid** (renders natively on GitHub —
no image files to maintain). For prose detail see
[solution-architecture.md](solution-architecture.md) and
[architecture.md](architecture.md).

## System flow

```mermaid
flowchart TD
    U([Customer]) -->|message| CX[Dialogflow CX<br/>NLU · intents · entities]
    CX -->|WebhookRequest| WH[Webhook<br/>/dialogflow/webhook]
    WH --> API[FastAPI<br/>orchestration]
    API --> KB[(Knowledge Base<br/>Markdown → chunks)]
    KB --> EMB[Vertex AI Embeddings<br/>cosine retrieval]
    EMB --> GEM[Gemini 2.5 Flash<br/>grounded generation]
    GEM -->|answer + sources + confidence| API
    API -->|WebhookResponse| CX
    CX -->|response| U

    API -.->|low confidence / 'human'| HO[Human Handoff<br/>create ticket]
    HO --> Q[[Escalation Queue]]
    API -.->|log every turn| AN[(Analytics<br/>SQLite)]
    AN --> DASH[Analytics Dashboard]

    classDef google fill:#4285F4,stroke:#1a73e8,color:#fff;
    classDef svc fill:#1f2330,stroke:#2a2f3d,color:#e7e9ee;
    classDef store fill:#34c759,stroke:#1e9e46,color:#062a12;
    class CX,EMB,GEM google;
    class WH,API,HO,DASH svc;
    class KB,AN,Q,store store;
```

## Request sequence (one grounded turn)

```mermaid
sequenceDiagram
    actor Customer
    participant CX as Dialogflow CX
    participant WH as FastAPI Webhook
    participant KB as Knowledge Base
    participant EMB as Vertex AI Embeddings
    participant GEM as Gemini

    Customer->>CX: "What's your refund policy?"
    CX->>CX: Detect intent + entities
    CX->>WH: WebhookRequest(intent, params, text)
    WH->>EMB: embed(query)
    EMB->>KB: cosine search (top-k chunks)
    KB-->>WH: relevant passages
    WH->>GEM: generate(answer | context only)
    GEM-->>WH: grounded answer
    WH-->>CX: answer + sources + confidence
    CX-->>Customer: response
    WH->>WH: log turn → analytics
```

## Deployment topology

```mermaid
flowchart LR
    subgraph Client
      FE[Static Frontend<br/>Vercel / Netlify]
    end
    subgraph Backend["Cloud Run / Render (Docker, autoscale)"]
      APP[FastAPI app]
    end
    subgraph Google["Google Cloud"]
      DCX[Dialogflow CX]
      VAI[Vertex AI<br/>Embeddings + Gemini]
    end
    FE -->|HTTPS| APP
    DCX -->|webhook| APP
    APP --> VAI
    APP --> DB[(SQLite / Cloud SQL)]
```
