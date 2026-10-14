from langchain_core.messages import HumanMessage, SystemMessage

from app.core import observability
from app.core.llm import as_text, get_llm
from app.core.output_guard import safe_customer_text
from app.models.policy import PolicyChunk

NO_EVIDENCE = "I could not find relevant policy evidence for this bank and loan type."
BLOCKED_ANSWER = (
    "I can explain what the policy says, but I can't say whether an application will be "
    "approved. Bank staff review and decide every application."
)

SYSTEM_PROMPT = """You are the lending policy assistant for an AI loan origination prototype.

Answer the user's question using ONLY the retrieved policy evidence below.

Rules:
- Do not invent lending rules.
- Do not invent eligibility requirements.
- Do not claim the sample data is an official bank policy.
- The current dataset is synthetic/demo policy data.
- If the retrieved evidence is insufficient, say so.
- Explain the answer clearly and concisely.
- Mention the relevant policy category when useful.
- Do not make the final lending decision or say whether the user will be approved.

RETRIEVED POLICY EVIDENCE:

{context}"""


def build_context(chunks: list[PolicyChunk]) -> str:
    return "\n\n".join(
        f"[Policy Evidence {index}]\n{chunk.content}\nSource: {chunk.source}\nData status: {chunk.data_status}"
        for index, chunk in enumerate(chunks, start=1)
    )


@observability.traced("policy.generate-answer", as_type="chain", omit=("chunks",))
async def generate_policy_answer(question: str, chunks: list[PolicyChunk]) -> str:
    if not chunks:
        return NO_EVIDENCE

    response = await get_llm("interaction").ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT.format(context=build_context(chunks))),
            HumanMessage(content=question),
        ]
    )
    return safe_customer_text(as_text(response), "policy") or BLOCKED_ANSWER
