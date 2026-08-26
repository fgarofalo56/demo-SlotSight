---
name: explain-floor
description: Ask the live Neon Palms floor a question through the MCP server
argument-hint: e.g. "which banks are fading?" or "is High Limit healthy?"
agent: Slot Analyst
tools: ['slotsight/*']
---

# Ask the floor

**${input:question:What do you want to know about the floor?}**

Answer using the `slotsight` MCP tools against the live database. Every number
you state must come from a tool call in this conversation.

## Get these right

**Compare to peers, not the floor.** `peer_index` compares like with like.
`floor_index` mostly re-renders the denomination column as a number — High Limit
reads 3.4× on it and 1.07× on peer index. Quote the first as evidence and you
have said something false.

**One weak window is not evidence.** Respect the `sustained` flag. Unsustained
means watch, not act.

**Hold far above par is a broken meter.** Never a star performer. Lead with the
fault.

**Talk in banks for anything about conversions.** Nobody swaps one unit out of
an eight-unit bank.

**Market data is synthetic.** Say so, briefly, when you cite it.

## Answer shape

Lead with the answer. Then the evidence. Then the recommendation, if one is
warranted — and say plainly if none is.

Name asset numbers and bank IDs. Always give the window. Keep it to three to six
sentences unless a table genuinely helps.
