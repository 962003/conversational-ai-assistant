#!/usr/bin/env python3
"""Provision the Dialogflow CX agent as code.

Creates (or augments) a CX agent with the entity types, intents, a fulfillment
webhook, and Start-Flow routes for the Enterprise Customer Support AI — so the
"User → Dialogflow CX → Webhook → FastAPI → KB → Gemini" path is reproducible
without hand-clicking the console.

Usage:
    pip install google-cloud-dialogflow-cx
    gcloud auth application-default login        # or set GOOGLE_APPLICATION_CREDENTIALS

    python dialogflow/provision_agent.py \
        --project YOUR_PROJECT_ID \
        --location global \
        --agent-name "Acme Support AI" \
        --webhook-url https://YOUR-BACKEND/dialogflow/webhook

Prints the created agent id; put it in backend/.env as DIALOGFLOW_AGENT_ID.

Docs: https://cloud.google.com/dialogflow/cx/docs/reference/library/python
"""
from __future__ import annotations

import argparse

from google.api_core.client_options import ClientOptions
from google.cloud import dialogflowcx_v3 as cx


# --- Training data ---------------------------------------------------------
# A part tuple is (text, parameter_id_or_None). Plain strings become a single
# unannotated part. Annotated parts teach CX to extract entities.
def tp(*parts):
    tphrase_parts = []
    for p in parts:
        if isinstance(p, tuple):
            text, pid = p
            tphrase_parts.append(cx.Intent.TrainingPhrase.Part(text=text, parameter_id=pid))
        else:
            tphrase_parts.append(cx.Intent.TrainingPhrase.Part(text=p))
    return cx.Intent.TrainingPhrase(parts=tphrase_parts, repeat_count=1)


ENTITY_TYPES = [
    dict(
        display_name="order_number",
        kind=cx.EntityType.Kind.KIND_REGEXP,
        entities=[cx.EntityType.Entity(value="[0-9]{4,7}", synonyms=["[0-9]{4,7}"])],
    ),
    dict(
        display_name="email",
        kind=cx.EntityType.Kind.KIND_REGEXP,
        entities=[cx.EntityType.Entity(
            value=r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            synonyms=[r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"],
        )],
    ),
    dict(
        display_name="product_name",
        kind=cx.EntityType.Kind.KIND_MAP,
        entities=[
            cx.EntityType.Entity(value="Acme Assistant Hub",
                                 synonyms=["Acme Assistant Hub", "assistant hub", "AAH-100"]),
            cx.EntityType.Entity(value="Acme Voice Gateway",
                                 synonyms=["Acme Voice Gateway", "voice gateway", "AVG-200"]),
            cx.EntityType.Entity(value="Acme Insights",
                                 synonyms=["Acme Insights", "insights", "AIN-300"]),
            cx.EntityType.Entity(value="Acme Connectors",
                                 synonyms=["Acme Connectors", "connectors", "ACN-400"]),
        ],
    ),
]


def build_intents(order_et: str, product_et: str):
    """Return intent specs. `*_et` are entity-type resource names for parameters."""
    return [
        dict(
            display_name="order_status",
            training_phrases=[
                tp("Where is my order ", ("12345", "order_id"), "?"),
                tp("Track order ", ("98765", "order_id")),
                tp("Has my package shipped yet?"),
                tp("What's the status of my order?"),
            ],
            parameters=[cx.Intent.Parameter(id="order_id", entity_type=order_et)],
        ),
        dict(
            display_name="refund_policy",
            training_phrases=[
                tp("What is your refund policy?"),
                tp("How do I return an item?"),
                tp("Can I get my money back?"),
                tp("How long do refunds take?"),
            ],
        ),
        dict(
            display_name="pricing",
            training_phrases=[
                tp("How much does the Pro plan cost?"),
                tp("What are your prices?"),
                tp("Do you offer a free trial?"),
                tp("What's included in the Business plan?"),
            ],
        ),
        dict(
            display_name="product_information",
            training_phrases=[
                tp("Tell me about ", ("Acme Voice Gateway", "product")),
                tp("What does ", ("Acme Insights", "product"), " do?"),
                tp("What products do you offer?"),
                tp("Do you have CRM integrations?"),
            ],
            parameters=[cx.Intent.Parameter(id="product", entity_type=product_et)],
        ),
        dict(
            display_name="human_agent",
            training_phrases=[
                tp("I want to talk to a human"),
                tp("Connect me to an agent"),
                tp("Can I speak to a representative?"),
                tp("Live agent please"),
            ],
        ),
        dict(
            display_name="general_question",
            training_phrases=[
                tp("How do I reset my password?"),
                tp("Is my data secure?"),
                tp("What are your support hours?"),
                tp("Can I use it in multiple languages?"),
            ],
        ),
    ]


# --- Helpers ---------------------------------------------------------------
def _client_options(location: str) -> ClientOptions | None:
    if location and location != "global":
        return ClientOptions(api_endpoint=f"{location}-dialogflow.googleapis.com")
    return None


def main():
    ap = argparse.ArgumentParser(description="Provision the Acme Support CX agent")
    ap.add_argument("--project", required=True)
    ap.add_argument("--location", default="global")
    ap.add_argument("--agent-name", default="Acme Support AI")
    ap.add_argument("--language", default="en")
    ap.add_argument("--time-zone", default="America/New_York")
    ap.add_argument("--webhook-url", required=True,
                    help="https://YOUR-BACKEND/dialogflow/webhook")
    ap.add_argument("--webhook-secret", default="",
                    help="optional; sent as X-Webhook-Secret header")
    args = ap.parse_args()

    opts = _client_options(args.location)
    parent = f"projects/{args.project}/locations/{args.location}"

    # 1) Agent
    agents = cx.AgentsClient(client_options=opts)
    agent = agents.create_agent(parent=parent, agent=cx.Agent(
        display_name=args.agent_name,
        default_language_code=args.language,
        time_zone=args.time_zone,
        description="Enterprise Customer Support AI (KB + Gemini via webhook).",
    ))
    print(f"✓ Agent created: {agent.name}")

    # 2) Entity types
    et_client = cx.EntityTypesClient(client_options=opts)
    et_names: dict[str, str] = {}
    for spec in ENTITY_TYPES:
        et = et_client.create_entity_type(parent=agent.name, entity_type=cx.EntityType(
            display_name=spec["display_name"], kind=spec["kind"], entities=spec["entities"],
        ))
        et_names[spec["display_name"]] = et.name
        print(f"  ✓ entity type: {spec['display_name']}")

    # 3) Webhook
    wh_client = cx.WebhooksClient(client_options=opts)
    generic = cx.Webhook.GenericWebService(uri=args.webhook_url)
    if args.webhook_secret:
        generic.request_headers = {"X-Webhook-Secret": args.webhook_secret}
    webhook = wh_client.create_webhook(parent=agent.name, webhook=cx.Webhook(
        display_name="kb-gemini-webhook", generic_web_service=generic,
    ))
    print(f"✓ Webhook created: {webhook.name}")

    # 4) Intents
    intents_client = cx.IntentsClient(client_options=opts)
    intent_names: dict[str, str] = {}
    for spec in build_intents(et_names["order_number"], et_names["product_name"]):
        intent = intents_client.create_intent(parent=agent.name, intent=cx.Intent(
            display_name=spec["display_name"],
            training_phrases=spec["training_phrases"],
            parameters=spec.get("parameters", []),
        ))
        intent_names[spec["display_name"]] = intent.name
        print(f"  ✓ intent: {spec['display_name']}")

    # 5) Wire Start-Flow routes -> webhook fulfillment
    flows_client = cx.FlowsClient(client_options=opts)
    start_flow = None
    for flow in flows_client.list_flows(parent=agent.name):
        if flow.display_name == "Default Start Flow":
            start_flow = flow
            break
    if start_flow is None:
        raise RuntimeError("Default Start Flow not found")

    def route(intent_display: str, tag: str) -> cx.TransitionRoute:
        return cx.TransitionRoute(
            intent=intent_names[intent_display],
            trigger_fulfillment=cx.Fulfillment(webhook=webhook.name, tag=tag),
        )

    routes = [
        route("order_status", "kb_search"),
        route("refund_policy", "kb_search"),
        route("pricing", "kb_search"),
        route("product_information", "kb_search"),
        route("general_question", "kb_search"),
        route("human_agent", "create_ticket"),
    ]
    start_flow.transition_routes = list(start_flow.transition_routes) + routes
    flows_client.update_flow(
        flow=start_flow,
        update_mask={"paths": ["transition_routes"]},
    )
    print(f"✓ Wired {len(routes)} Start-Flow routes to the webhook")

    agent_id = agent.name.split("/")[-1]
    print("\nDone. Add this to backend/.env:")
    print(f"  DIALOGFLOW_PROJECT={args.project}")
    print(f"  DIALOGFLOW_LOCATION={args.location}")
    print(f"  DIALOGFLOW_AGENT_ID={agent_id}")


if __name__ == "__main__":
    main()
