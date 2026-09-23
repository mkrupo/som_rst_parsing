# Try the task in the official Jev playground

This optional page describes the direct TypeSafe Playground. The default
OpenRouter setup for this repository is in [the cold-start guide](cold-start.md).

This is a synthetic smoke example for the task shape used by the runner: one
ordered span pair and two Choice questions evaluated in one request. It uses
the full 34-label relation inventory from
[the project config](../configs/rst_relations.json). The text is invented; it
is not from ArgMicrotexts or part of the benchmark set.

## Sign in and open the playground

Jev is accessed through a TypeSafe account; there is no separate Jev
registration. Open the [official TypeSafe Playground](https://console.typesafe.ai/playground)
and sign in. The current login page offers Google or email verification code.
TypeSafe's [quickstart](https://docs.typesafe.ai/introduction/quickstart)
describes the Playground flow as: paste a state, add a typed question, then
add more questions to evaluate together.

The Playground makes a live model request under your TypeSafe account. Before
you click Run, check the current price and credit balance shown in the
console. TypeSafe accounts may use promotional or purchased credits, so do not
assume an authenticated request is free. The official API reference describes
input token usage as billable; output tokens are currently free
([API reference](https://api.typesafe.ai/docs); [service terms](https://typesafe.ai/legal/mca)).

## Enter the state

If the Playground accepts JSON state, paste this object. If it offers a text
field only, paste the same three fields as readable text.

    {
      "document_context": "The match was abandoned. Heavy rain had flooded the pitch.",
      "span_a": "The match was abandoned.",
      "span_b": "Heavy rain had flooded the pitch."
    }

## Add both Choice questions

Add two questions named relation and nuclearity, each with type Choice. If the
Playground exposes a JSON editor for questions, paste this object as the
questions map (without an outer request wrapper). Otherwise enter the same
instructions and criteria through its question controls. If the UI asks for a
model, select the pinned `jev-1.13` model.

    {
      "relation": {
        "type": "choice",
        "instructions": "Choose exactly one ArgMicrotexts English Part 1 RST relation for the ordered spans span_a and span_b in the supplied document context. Span A precedes span B. Use the supplied relation definitions, prefer the most specific label supported by the text, and use unstated-relation only when no more specific label applies.",
        "criteria": {
          "antithesis": "The nucleus presents the writer's preferred claim; the satellite presents a rejected or dispreferred claim that the writer argues against. This relation is mononuclear and must use NS or SN.",
          "background": "The satellite supplies context that helps the reader understand the nucleus. This relation is mononuclear and must use NS or SN.",
          "circumstance": "The satellite gives the time, place, or situation in which the nucleus holds or occurs. This relation is mononuclear and must use NS or SN.",
          "concession": "The satellite presents a valid or plausible consideration that could count against the nucleus, while the writer still emphasizes the nucleus. This relation is mononuclear and must use NS or SN.",
          "condition": "The satellite describes a hypothetical, future, or unrealized situation on which the nucleus depends. This relation is mononuclear and must use NS or SN.",
          "elaboration": "The satellite adds detail about the situation, event, or proposition in the nucleus. This relation is mononuclear and must use NS or SN.",
          "e-elaboration": "The satellite adds descriptive detail about a specific entity or element mentioned in the nucleus. This relation is mononuclear and must use NS or SN.",
          "enablement": "The satellite makes it easier or possible for the reader to perform the action described in the nucleus. This relation is mononuclear and must use NS or SN.",
          "evaluation-s": "The satellite expresses an evaluation of the situation or proposition in the nucleus. This relation is mononuclear and must use NS or SN.",
          "evidence": "The satellite provides relatively objective evidence that supports the reader's belief in the nucleus. This relation is mononuclear and must use NS or SN.",
          "interpretation": "The satellite gives a conceptual interpretation or rephrasing of the nucleus, rather than mainly evaluating it. This relation is mononuclear and must use NS or SN.",
          "justify": "The satellite explains why the writer is justified in presenting or asking the reader to accept the nucleus. This relation is mononuclear and must use NS or SN.",
          "means": "The satellite describes the method or means by which the action in the nucleus is carried out or achieved. This relation is mononuclear and must use NS or SN.",
          "motivation": "The satellite increases the reader's desire or intention to perform the action in the nucleus. This relation is mononuclear and must use NS or SN.",
          "cause": "The satellite describes a cause of the event or state described in the nucleus. This relation is mononuclear and must use NS or SN.",
          "result": "The satellite describes an effect or result of the event or state described in the nucleus. This relation is mononuclear and must use NS or SN.",
          "otherwise": "The nucleus describes what holds or should happen if the situation in the satellite does not occur. This relation is mononuclear and must use NS or SN.",
          "preparation": "The satellite introduces or prepares the reader for the topic or proposition in the nucleus. This relation is mononuclear and must use NS or SN.",
          "purpose": "The satellite describes an intended, not yet realized goal that the action in the nucleus is meant to achieve. This relation is mononuclear and must use NS or SN.",
          "restatement": "The satellite re-expresses the nucleus with roughly comparable scope, but one span is more central than the other. This relation is mononuclear and must use NS or SN.",
          "solutionhood": "The nucleus provides a solution or answer to a problem, question, need, or request presented in the satellite. This relation is mononuclear and must use NS or SN.",
          "summary": "The satellite gives a shorter summary of the nucleus or the preceding discourse. This relation is mononuclear and must use NS or SN.",
          "unconditional": "The nucleus holds regardless of whether the situation described in the satellite occurs. This relation is mononuclear and must use NS or SN.",
          "unless": "The satellite gives an exception: the nucleus holds except when the situation described in the satellite occurs. This relation is mononuclear and must use NS or SN.",
          "unstated-relation": "The spans have a clear rhetorical relation, but none of the more specific labels in this inventory applies. This relation is mononuclear and must use NS or SN.",
          "evaluation-n": "The nucleus expresses an evaluation of the situation or proposition in the satellite. This relation is mononuclear and must use NS or SN.",
          "reason": "The satellite gives a subjective or intentional reason for the reader to accept the nucleus, rather than objective evidence about its truth. This relation is mononuclear and must use NS or SN.",
          "conjunction": "Both spans have equal rhetorical weight and jointly contribute to the same discourse purpose, often as an explicitly coordinated unit. This relation is multinuclear and must use NN.",
          "contrast": "Both spans have equal rhetorical weight and present comparable situations that differ in a relevant way. This relation is multinuclear and must use NN.",
          "disjunction": "Both spans have equal rhetorical weight and present alternatives, commonly signaled by an equivalent of 'or'. This relation is multinuclear and must use NN.",
          "joint": "Both spans have equal rhetorical weight and form a coherent unit, with no more specific multinuclear relation applying. This relation is multinuclear and must use NN.",
          "list": "Both spans have equal rhetorical weight and are parallel members of an enumeration without a temporal or causal ordering. This relation is multinuclear and must use NN.",
          "restatement-mn": "Both spans have equal rhetorical weight and one restates or rephrases the other without either being the nucleus. This relation is multinuclear and must use NN.",
          "sequence": "Both spans have equal rhetorical weight and are ordered as steps or events in a temporal or procedural sequence. This relation is multinuclear and must use NN."
        }
      },
      "nuclearity": {
        "type": "choice",
        "instructions": "Choose the nuclearity of the relation between the same ordered spans. NS means span A is the nucleus and span B is the satellite; SN means span A is the satellite and span B is the nucleus; NN means both spans are nuclei with equal rhetorical weight. Span A precedes span B.",
        "criteria": {
          "NS": "Span A is the nucleus and span B is the satellite.",
          "SN": "Span A is the satellite and span B is the nucleus.",
          "NN": "Both spans are nuclei with equal rhetorical weight."
        }
      }
    }

Run once after both questions are present. The TypeSafe quickstart says
multiple question types can be evaluated together in one request.

## Check the response

For this synthetic example, the expected relation is cause: heavy rain caused
the match to be abandoned. The expected nuclearity is NS: span A is the
nucleus and span B is the satellite. Inspect both selected labels and their
probabilities. This is only a smoke example; it does not measure benchmark
accuracy.

## What to do next

The Playground check confirms that Jev can receive the task and return both
typed decisions. It does not verify this repository's SDK integration, raw
response cache, prediction writer, or evaluation code.

The repository's included input row is also synthetic. Before running the
14-document benchmark, prepare local JSONL pair rows from the documents listed
in [the ArgMicrotexts task profile](argmicrotexts.md). Then follow the
[runner guide](cold-start.md). The repository's default runner uses
`OPENROUTER_API_KEY`; one request is sent per uncached input row and may incur
OpenRouter charges.
