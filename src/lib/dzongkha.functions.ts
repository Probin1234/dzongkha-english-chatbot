import { createServerFn } from "@tanstack/react-start";

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type DzongkhaReply = {
  ok: true;
  dzongkha: string;
  roman: string;
  gloss: string;
};

export type DzongkhaError = {
  ok: false;
  error: string;
};

const SYSTEM = `You are Druk Kha, a conversational assistant. The user writes in English. You answer in spoken Bhutanese Dzongkha (རྫོང་ཁ), the national language of Bhutan — the language of Thimphu and Punakha, as Bhutanese people actually speak it.

This is NOT Tibetan. Tibetan script is only the alphabet. The words must be Dzongkha.

Never write these Tibetan forms:
- བཀའ་དྲིན་མེད། (that is Tibetan for "you're welcome" — forbidden)
- ཐུགས་རྗེ་ཆེ། (Tibetan "thank you" — forbidden)
- ཁྱེད་རང་ (Tibetan "you")
- ཡིན། / རེད། / ཡོད་རེད། / འདུག / ཡིན་པས། / ཡོད་པས། as the verb "to be"
- བདེ་པོ་ཡིན། for "I am fine"

Use these exact Bhutanese phrases whenever the meaning matches. Do not paraphrase them into Tibetan:

- Hello: སྐུ་གཟུགས་བཟང་པོ། — roman "Kuzu zangpo". Polite: སྐུ་གཟུགས་བཟང་པོ་ལགས། — "Kuzu zangpo la"
- How are you?: ཁྱོད་ག་དེ་སྦེ་ཡོད། — "Choe gadey bey yoe?"
- I am fine: ང་ལེགས་ཤོམ་སྦེ་ཡོད། — "Nga lekshom bey yoe"
- Thank you: བཀའ་དྲིན་ཆེ་ལགས། — "Kadrin chhe la"
- You're welcome (the reply when someone says thank you): རྗེམ་པ་ལེགས་སོ། — roman MUST be "Jembalaekso". Informal alternatives only if the user asks for a casual form: ཡ་ཡ། "Yaya" or ཁེ་མི། "Khemi". Never བཀའ་དྲིན་མེད།
- Please: ང་ལུ་གནང་། — "Nga lu nang"
- Yes: ཨིན། — "Inn". No: མེན། — "Men"
- Sorry: ཙིགཔ་མ་ཟ། — "Tsip maza"
- Goodbye: ལོག་ཤུལ་ལས་འཇལ་གེ། — "Lok shu ley jel gey"
- I / you: ང་ / ཁྱོད་. To-marker: ལུ་. Question particle: ག་ or མས་. Do-verb: འབད་. Manner: སྦེ་.

If the user says "thank you", answer with you're welcome: རྗེམ་པ་ལེགས་སོ། (Jembalaekso).
If they ask how to say you're welcome, the Dzongkha is རྗེམ་པ་ལེགས་སོ། and the roman is Jembalaekso.

Keep replies to one to four sentences. No English inside the Dzongkha except proper names.
"roman" is how a person in Bhutan says it aloud (Roman Dzongkha), not Wylie.
"gloss" is the English meaning of your reply only.

Return ONLY JSON: {"dzongkha":"...","roman":"...","gloss":"..."}`;

const JEMBA = {
  dzongkha: "རྗེམ་པ་ལེགས་སོ།",
  roman: "Jembalaekso",
  gloss: "You're welcome.",
};

const TIBETAN_MARKERS = [
  "བཀའ་དྲིན་མེད",
  "ཐུགས་རྗེ",
  "ཁྱེད་རང",
  "ཡིན་པས",
  "ཡོད་པས",
  "ཡོད་རེད",
  "བདེ་པོ་ཡིན",
];

function wantsJemba(text: string) {
  const t = text
    .trim()
    .toLowerCase()
    .replace(/[.!?]+$/g, "")
    .trim();
  if (/^(thanks|thank you|thank you so much|thanks a lot|many thanks)$/.test(t)) return true;
  if (/^(you'?re welcome|you are welcome)$/.test(t)) return true;
  return (
    /\b(how (do|to)|say|translate|dzongkha|mean)\b/.test(t) &&
    /you'?re welcome|you are welcome/.test(t)
  );
}

function hasTibetan(text: string) {
  return TIBETAN_MARKERS.some((marker) => text.includes(marker));
}

function cleanTurns(input: unknown): ChatTurn[] {
  if (!input || typeof input !== "object") {
    throw new Error("Write a message first.");
  }
  const raw = (input as { messages?: unknown }).messages;
  if (!Array.isArray(raw) || raw.length === 0) {
    throw new Error("Write a message first.");
  }
  const turns: ChatTurn[] = [];
  for (const item of raw.slice(-8)) {
    if (!item || typeof item !== "object") continue;
    const role = (item as { role?: unknown }).role;
    const content = (item as { content?: unknown }).content;
    if ((role !== "user" && role !== "assistant") || typeof content !== "string") continue;
    const text = content.trim().slice(0, 2000);
    if (!text) continue;
    turns.push({ role, content: text });
  }
  if (turns.length === 0 || turns[turns.length - 1]?.role !== "user") {
    throw new Error("Write a message first.");
  }
  return turns;
}

function parseReply(raw: string): { dzongkha: string; roman: string; gloss: string } {
  const trimmed = raw
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");
  try {
    const data = JSON.parse(trimmed) as Record<string, unknown>;
    const dzongkha = typeof data.dzongkha === "string" ? data.dzongkha.trim() : "";
    const roman = typeof data.roman === "string" ? data.roman.trim() : "";
    const gloss = typeof data.gloss === "string" ? data.gloss.trim() : "";
    if (dzongkha) return { dzongkha, roman, gloss };
  } catch {
    /* fall through */
  }
  return { dzongkha: trimmed, roman: "", gloss: "" };
}

export const replyInDzongkha = createServerFn({ method: "POST" })
  .validator((input: unknown) => ({ messages: cleanTurns(input) }))
  .handler(async ({ data }): Promise<DzongkhaReply | DzongkhaError> => {
    const lastUser = data.messages[data.messages.length - 1]?.content ?? "";
    if (wantsJemba(lastUser)) return { ok: true, ...JEMBA };

    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) {
      return { ok: false, error: "The language model is not available right now." };
    }

    const ask = (extra?: ChatTurn[]) =>
      fetch("https://api.x.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: "grok-4.5",
          temperature: 0.2,
          max_tokens: 450,
          response_format: { type: "json_object" },
          messages: [{ role: "system", content: SYSTEM }, ...data.messages, ...(extra ?? [])],
        }),
      });

    const res = await ask();
    if (!res.ok) {
      return { ok: false, error: `Could not write a reply (${res.status}). Try again.` };
    }

    const read = async (response: Response) => {
      const body = (await response.json()) as {
        choices?: { message?: { content?: string } }[];
      };
      return body.choices?.[0]?.message?.content ?? "";
    };

    let raw = await read(res);
    let parsed = parseReply(raw);
    if (hasTibetan(parsed.dzongkha)) {
      const retry = await ask([
        { role: "assistant", content: raw },
        {
          role: "user",
          content:
            "That was Tibetan, not Bhutanese Dzongkha. Rewrite the same answer. You're welcome is རྗེམ་པ་ལེགས་སོ། (Jembalaekso), never བཀའ་དྲིན་མེད།. Do not use ཁྱེད་རང་, ཐུགས་རྗེ་, or རེད།.",
        },
      ]);
      if (retry.ok) {
        raw = await read(retry);
        parsed = parseReply(raw);
      }
    }

    if (hasTibetan(parsed.dzongkha) && wantsJemba(lastUser)) {
      return { ok: true, ...JEMBA };
    }
    if (!parsed.dzongkha.trim()) {
      return { ok: false, error: "The reply came back empty. Try again." };
    }
    if (parsed.dzongkha.includes("བཀའ་དྲིན་མེད")) {
      return { ok: true, ...JEMBA };
    }
    return { ok: true, ...parsed };
  });
