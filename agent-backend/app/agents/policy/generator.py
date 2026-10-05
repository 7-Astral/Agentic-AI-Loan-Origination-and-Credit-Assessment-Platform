from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import as_text, get_llm
from app.models.policy import PolicyChunk

NO_EVIDENCE = "I could not find relevant policy evidence for this bank and loan type."

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


async def generate_policy_answer(question: str, chunks: list[PolicyChunk]) -> str:
    if not chunks:
        return NO_EVIDENCE

    response = await get_llm("interaction").ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT.format(context=build_context(chunks))),
            HumanMessage(content=question),
        ]
    )
    return as_text(response)
