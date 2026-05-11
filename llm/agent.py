import json

SYSTEM_PROMPT = """You are WealthOS — a senior institutional
investment advisor specializing in Indian capital markets.
You operate at the standard of a CFA-qualified analyst with
deep expertise in NSE/BSE equities, mutual funds, and gold.

IDENTITY:
- You give specific, data-driven investment advice
- You always cite actual numbers from the data provided
- You never give vague answers like "it depends" without
  immediately resolving what it depends on
- You respect Indian tax laws and SEBI regulations
- You always mention key risks alongside recommendations

INDIA-SPECIFIC CONSTANTS YOU MUST USE:
- Risk-free rate: 7.1% (10-year G-Sec)
- Equity risk premium: 6% for Indian markets
- LTCG tax: 12.5% above ₹1.25 lakh
- STCG tax: 20%
- Nifty 50 long-term CAGR: 11-13%
- FD returns: 6.5-7.5%

RESPONSE FORMAT — ALWAYS USE THIS STRUCTURE:

ASSESSMENT
[2-3 sentences summarizing the current situation based on data]

KEY METRICS
[List the most important numbers from the analysis]

RECOMMENDATION
Verdict: [BUY / HOLD / TRIM / EXIT / ACCUMULATE / AVOID]
Confidence: [HIGH / MEDIUM / LOW]
Reasoning: [2-3 sentences with specific data points]

RISKS
[2-3 specific risks to this recommendation]

NEXT ACTION
[One concrete step the investor should take]

DISCLAIMER
This is AI-generated analysis for educational purposes only.
Not SEBI-registered investment advice. Consult a SEBI-registered
advisor before making investment decisions."""

TOOL_SELECTION_PROMPT = """You are a financial data assistant.
Given a user question, decide which tools to call to gather
the necessary data. Output ONLY a JSON array of tool calls.

Available tools:
{tool_descriptions}

User question: {question}

Rules:
1. For stock questions: always include get_stock_context first
2. For portfolio questions: call get_stock_context for each stock
3. For MF questions: call search_mutual_fund then get_mf_analysis
4. For gold questions: call get_gold_analysis
5. For macro/market questions: call get_macro_context
6. Maximum 4 tool calls total
7. Output ONLY valid JSON, nothing else

Output format:
[
  {{"tool": "tool_name", "input": "input_string"}},
  {{"tool": "tool_name", "input": "input_string"}}
]

If no tools are needed (general knowledge question):
[]"""


def _select_tools(llm, question: str, tools: list) -> list:
    try:
        tool_descriptions = "\n".join([
            f"- {t.name}: {t.description}"
            for t in tools
        ])

        prompt = TOOL_SELECTION_PROMPT.format(
            tool_descriptions=tool_descriptions,
            question=question
        )

        from llm.llm_loader import generate
        response = generate(
            llm=llm,
            system_prompt="You are a JSON-only tool selector. Output valid JSON arrays only.",
            user_message=prompt,
            max_tokens=256,
            temperature=0.0
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

        tool_calls = json.loads(cleaned)
        if not isinstance(tool_calls, list):
            return []
        return tool_calls[:4]

    except json.JSONDecodeError:
        print(f"[Agent] Warning — could not parse tool selection: {response[:100]}")
        return []
    except Exception as e:
        print(f"[Agent] Warning — tool selection failed: {e}")
        return []


def _execute_tools(tool_calls: list, tools: list) -> str:
    try:
        tool_map = {t.name: t for t in tools}

        results = []
        for call in tool_calls:
            tool_name  = call.get("tool", "")
            tool_input = call.get("input", "")

            if tool_name not in tool_map:
                results.append(f"[{tool_name}]: Tool not found")
                continue

            print(f"[Agent] Calling tool: {tool_name}({tool_input[:50]})")
            result = tool_map[tool_name].run(tool_input)
            results.append(f"[DATA FROM {tool_name.upper()}]\n{result}")

        return "\n\n".join(results)

    except Exception as e:
        return f"Tool execution error: {str(e)}"


def run_agent(llm, question: str, tools: list, verbose: bool = True) -> str:
    try:
        if verbose:
            print(f"[Agent] Question: {question}")

        tool_calls = _select_tools(llm, question, tools)
        if verbose:
            print(f"[Agent] Selected {len(tool_calls)} tool(s):")
            for call in tool_calls:
                print(f"  \u2192 {call.get('tool')}({call.get('input', '')[:40]})")

        if tool_calls:
            tool_results = _execute_tools(tool_calls, tools)
        else:
            tool_results = "No external data needed for this question."

        if tool_results:
            user_message = (
                f"Question: {question}\n\n"
                f"Data gathered from market analysis tools:\n"
                f"{tool_results}\n\n"
                f"Based on the above data, provide your investment advisory response "
                f"following the required format exactly."
            )
        else:
            user_message = (
                f"Question: {question}\n\n"
                f"Provide your investment advisory response following the required "
                f"format exactly."
            )

        if verbose:
            print("[Agent] Generating advisory response...")

        from llm.llm_loader import generate
        answer = generate(
            llm=llm,
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=1024,
            temperature=0.1
        )

        if verbose:
            print(f"[Agent] Response generated ({len(answer)} chars)")

        return answer

    except Exception as e:
        print(f"[Agent] Error: {e}")
        return f"Agent error: {str(e)}"


def ask_wealthos(llm, question: str, verbose: bool = True) -> str:
    try:
        from llm.tools import ALL_TOOLS
        return run_agent(llm, question, ALL_TOOLS, verbose)
    except Exception as e:
        return f"WealthOS Error: {str(e)}"
