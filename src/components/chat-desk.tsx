import { useEffect, useRef, useState } from "react";
import { Check, Copy, RotateCcw, Send } from "lucide-react";
import { replyInDzongkha, type ChatTurn } from "@/lib/dzongkha.functions";

type Bubble = {
  id: string;
  role: "user" | "assistant";
  text: string;
  roman?: string;
  gloss?: string;
};

const STORAGE_KEY = "druk-kha-thread-v1";
const GUIDE_KEY = "druk-kha-guide-v1";

const STARTERS = [
  "Hello, how are you?",
  "Thank you for your help.",
  "What should I say when I meet someone in Thimphu?",
  "Tell me a short Bhutanese proverb.",
  "How do I ask for the price of this?",
];

function newId() {
  return crypto.randomUUID();
}

export function ChatDesk() {
  const [messages, setMessages] = useState<Bubble[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guide, setGuide] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Bubble[];
        if (Array.isArray(parsed)) setMessages(parsed.slice(-40));
      }
      const guideSaved = localStorage.getItem(GUIDE_KEY);
      if (guideSaved === "0") setGuide(false);
    } catch {
      /* ignore broken storage */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(GUIDE_KEY, guide ? "1" : "0");
  }, [guide, hydrated]);

  useEffect(() => {
    const node = scroller.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    setError(null);
    setDraft("");
    const userBubble: Bubble = { id: newId(), role: "user", text: trimmed };
    const next = [...messages, userBubble];
    setMessages(next);
    setPending(true);

    const turns: ChatTurn[] = next.slice(-8).map((message) => ({
      role: message.role,
      content: message.role === "assistant" ? message.text : message.text,
    }));

    try {
      const result = await replyInDzongkha({ data: { messages: turns } });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          text: result.dzongkha,
          roman: result.roman,
          gloss: result.gloss,
        },
      ]);
    } catch {
      setError("The reply did not come through. Try once more.");
    } finally {
      setPending(false);
      field.current?.focus();
    }
  }

  async function copyText(id: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId((current) => (current === id ? null : current)), 1600);
    } catch {
      setError("Could not copy that reply.");
    }
  }

  function clearThread() {
    setMessages([]);
    setError(null);
    setDraft("");
  }

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-ink">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-widest text-saffron uppercase">
              Bhutan
            </p>
            <h1 className="text-xl font-semibold tracking-tight text-balance sm:text-2xl">
              Druk Kha
            </h1>
          </div>
          <p className="font-dzongkha hidden text-right text-lg leading-snug text-ink sm:block">
            རྫོང་ཁ
          </p>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-5xl flex-1 grid-cols-1 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="hidden border-r border-line px-6 py-8 lg:block">
          <p className="text-sm leading-relaxed text-pretty text-muted">
            Write in English. The reply is Bhutanese Dzongkha, the national language of Bhutan —
            not Tibetan.
          </p>
          <ul className="mt-6 space-y-2">
            {STARTERS.map((starter) => (
              <li key={starter}>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void send(starter)}
                  className="w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-left text-sm leading-snug text-ink transition hover:border-saffron disabled:opacity-50"
                >
                  {starter}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="flex min-h-0 flex-col">
          <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-6">
            {messages.length === 0 && !pending ? (
              <EmptyState onPick={(value) => void send(value)} disabled={pending} />
            ) : null}

            {messages.map((message) =>
              message.role === "user" ? (
                <div key={message.id} className="flex justify-end">
                  <div className="max-w-lg rounded-2xl rounded-br-md bg-ink px-4 py-3 text-surface">
                    <p className="text-xs font-semibold tracking-widest text-saffron uppercase">
                      English
                    </p>
                    <p className="mt-1 text-pretty">{message.text}</p>
                  </div>
                </div>
              ) : (
                <article
                  key={message.id}
                  className="max-w-2xl rounded-2xl rounded-bl-md border border-line border-l-4 border-l-saffron bg-surface px-4 py-4 sm:px-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-semibold tracking-widest text-lacquer uppercase">
                      Dzongkha
                    </p>
                    <button
                      type="button"
                      onClick={() => void copyText(message.id, message.text)}
                      className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-muted hover:text-ink"
                      aria-label="Copy Dzongkha reply"
                    >
                      {copiedId === message.id ? (
                        <Check className="size-4" aria-hidden="true" />
                      ) : (
                        <Copy className="size-4" aria-hidden="true" />
                      )}
                      {copiedId === message.id ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <p className="font-dzongkha mt-2 text-2xl leading-relaxed text-pretty sm:text-3xl">
                    {message.text}
                  </p>
                  {guide && (message.roman || message.gloss) ? (
                    <div className="mt-3 space-y-1 border-t border-line pt-3 text-sm">
                      {message.roman ? (
                        <p className="text-pretty">
                          <span className="font-semibold text-muted">Say it </span>
                          {message.roman}
                        </p>
                      ) : null}
                      {message.gloss ? (
                        <p className="text-pretty text-muted">
                          <span className="font-semibold">Means </span>
                          {message.gloss}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              ),
            )}

            {pending ? (
              <p className="text-sm text-muted" role="status">
                Writing in Dzongkha…
              </p>
            ) : null}
          </div>

          <div className="border-t border-line bg-bg px-4 py-3 sm:px-6">
            {messages.length > 0 ? (
              <div className="mb-3 flex gap-2 overflow-x-auto lg:hidden">
              {STARTERS.slice(0, 3).map((starter) => (
                <button
                  key={starter}
                  type="button"
                  disabled={pending}
                  onClick={() => void send(starter)}
                  className="shrink-0 rounded-full border border-line bg-surface px-3 py-2 text-xs text-ink disabled:opacity-50"
                >
                  {starter}
                </button>
              ))}
            </div>
            ) : null}

            {error ? (
              <p className="mb-2 text-sm text-lacquer" role="alert">
                {error}
              </p>
            ) : null}

            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                void send(draft);
              }}
            >
              <label className="sr-only" htmlFor="english-input">
                Message in English
              </label>
              <textarea
                id="english-input"
                ref={field}
                rows={2}
                value={draft}
                maxLength={2000}
                placeholder="Write in English…"
                disabled={pending}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void send(draft);
                  }
                }}
                className="min-h-14 flex-1 resize-none rounded-2xl border border-line bg-surface px-4 py-3 text-base text-ink outline-none placeholder:text-muted focus:border-saffron"
              />
              <button
                type="submit"
                disabled={pending || draft.trim().length === 0}
                className="inline-flex size-12 shrink-0 items-center justify-center rounded-2xl bg-ink text-surface disabled:opacity-40"
                aria-label="Send"
              >
                <Send className="size-5" aria-hidden="true" />
              </button>
            </form>

            <div className="mt-2 flex items-center justify-between gap-3 text-xs text-muted">
              <button
                type="button"
                role="switch"
                aria-checked={guide}
                onClick={() => setGuide((value) => !value)}
                className="inline-flex min-h-11 items-center gap-2"
              >
                <span
                  className={
                    "relative h-5 w-9 rounded-full transition " +
                    (guide ? "bg-saffron" : "bg-line")
                  }
                  aria-hidden="true"
                >
                  <span
                    className={
                      "absolute top-0.5 size-4 rounded-full bg-surface transition " +
                      (guide ? "left-4" : "left-0.5")
                    }
                  />
                </span>
                Pronunciation and meaning
              </button>
              <button
                type="button"
                onClick={clearThread}
                disabled={messages.length === 0 || pending}
                className="inline-flex min-h-11 items-center gap-1.5 disabled:opacity-40"
              >
                <RotateCcw className="size-3.5" aria-hidden="true" />
                Clear
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function EmptyState({ onPick, disabled }: { onPick: (value: string) => void; disabled: boolean }) {
  return (
    <div className="mx-auto max-w-lg pt-8 sm:pt-16">
      <p className="font-dzongkha text-4xl leading-tight text-balance sm:text-5xl">ཀུ་ཟུ་བཟང་པོ།</p>
      <p className="mt-2 text-sm text-muted">Kuzu zangpo — hello.</p>
      <p className="mt-4 max-w-md text-pretty text-ink">
        Type anything in English. Druk Kha answers in Bhutanese Dzongkha, with a pronunciation and
        an English meaning underneath.
      </p>
      <div className="mt-6 flex flex-wrap gap-2 lg:hidden">
        {STARTERS.slice(0, 3).map((starter) => (
          <button
            key={starter}
            type="button"
            disabled={disabled}
            onClick={() => onPick(starter)}
            className="rounded-full border border-line bg-surface px-3 py-2 text-sm"
          >
            {starter}
          </button>
        ))}
      </div>
    </div>
  );
}
