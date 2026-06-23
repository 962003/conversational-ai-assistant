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

## Deployment topology (current)

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

## Target production architecture (Google Cloud)

The same code scales onto a full Google Cloud Contact Center AI stack. New pieces
vs. the current build are marked **(target)**.

```mermaid
flowchart LR
    U([Customer]) --> CH{{Channels<br/>web · voice/telephony target}}
    CH --> DCX[Dialogflow CX]
    DCX -->|webhook| CR[Cloud Run<br/>FastAPI fulfillment]
    CR --> VAI[Vertex AI<br/>embeddings + Gemini]
    CR --> VS[(Vertex AI Vector Search<br/>target)]
    CR --> PS[[Pub/Sub<br/>async events · target]]
    PS --> BQ[(BigQuery<br/>analytics warehouse · target)]
    CR --> AN[(SQLite / Cloud SQL<br/>turns + tickets)]
    AN --> BQ
    BQ --> LK[Looker Studio<br/>dashboards · target]
    CR -.->|tickets| CRM[(CRM / ITSM<br/>connector · target)]

    classDef g fill:#4285F4,stroke:#1a73e8,color:#fff;
    classDef t fill:#1f2330,stroke:#4285F4,color:#9ec1ff,stroke-dasharray:4 3;
    class DCX,VAI,CR g;
    class VS,PS,BQ,LK,CRM t;
```

- **Pub/Sub** decouples slow work (ticket creation, CRM sync, transcript export)
  from the synchronous webhook path.
- **BigQuery** is the analytics warehouse for conversation logs → **Looker Studio**
  dashboards (the in-app dashboard is the lightweight version of this).
- **Vertex AI Vector Search** replaces the in-memory cosine index for large KBs.
- **Voice** via the CCAI telephony connector — see
  [customer-journey-design.md](customer-journey-design.md#voice--contact-center-ai).
