import { useEffect, useRef, useState } from "react";
import { Check, Copy, MessageSquarePlus, Send, Trash2 } from "lucide-react";
import { replyInDzongkha, type ChatTurn } from "@/lib/dzongkha.functions";

type Bubble = {
  id: string;
  role: "user" | "assistant";
  text: string;
  roman?: string;
  gloss?: string;
};

type Chat = {
  id: string;
  title: string;
  updatedAt: number;
  messages: Bubble[];
};

const CHATS_KEY = "druk-kha-chats-v1";
const LEGACY_KEY = "druk-kha-thread-v1";
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

function titleFrom(messages: Bubble[], fallback = "New chat") {
  const first = messages.find((message) => message.role === "user")?.text.trim();
  if (!first) return fallback;
  return first.length > 42 ? `${first.slice(0, 42).trimEnd()}…` : first;
}

function readStore(): { chats: Chat[]; activeId: string | null } {
  try {
    const raw = localStorage.getItem(CHATS_KEY);
    if (raw) {
      const data = JSON.parse(raw) as { chats?: Chat[]; activeId?: string | null };
      const chats = Array.isArray(data.chats) ? data.chats.slice(0, 40) : [];
      const activeId =
        typeof data.activeId === "string" && chats.some((chat) => chat.id === data.activeId)
          ? data.activeId
          : (chats[0]?.id ?? null);
      return { chats, activeId };
    }
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy) {
      const parsed = JSON.parse(legacy) as Bubble[];
      localStorage.removeItem(LEGACY_KEY);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const id = newId();
        return {
          chats: [
            {
              id,
              title: titleFrom(parsed),
              updatedAt: Date.now(),
              messages: parsed.slice(-40),
            },
          ],
          activeId: id,
        };
      }
    }
  } catch {
    /* ignore broken storage */
  }
  return { chats: [], activeId: null };
}

export function ChatDesk() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guide, setGuide] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [listOpen, setListOpen] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);

  const messages = chats.find((chat) => chat.id === activeId)?.messages ?? [];

  useEffect(() => {
    const stored = readStore();
    setChats(stored.chats);
    setActiveId(stored.activeId);
    if (localStorage.getItem(GUIDE_KEY) === "0") setGuide(false);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(CHATS_KEY, JSON.stringify({ chats, activeId }));
  }, [chats, activeId, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(GUIDE_KEY, guide ? "1" : "0");
  }, [guide, hydrated]);

  useEffect(() => {
    const node = scroller.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  function putMessages(chatId: string, nextMessages: Bubble[], title?: string) {
    setChats((current) => {
      const found = current.find((chat) => chat.id === chatId);
      if (!found) return current;
      const next: Chat = {
        ...found,
        messages: nextMessages.slice(-40),
        title: title ?? titleFrom(nextMessages, found.title),
        updatedAt: Date.now(),
      };
      return [next, ...current.filter((chat) => chat.id !== chatId)];
    });
  }

  function startChat() {
    if (pending) return;
    if (messages.length === 0) {
      setListOpen(false);
      field.current?.focus();
      return;
    }
    setActiveId(null);
    setDraft("");
    setError(null);
    setListOpen(false);
    field.current?.focus();
  }

  function openChat(id: string) {
    if (pending || id === activeId) return;
    setActiveId(id);
    setDraft("");
    setError(null);
    setListOpen(false);
  }

  function removeChat(id: string) {
    if (pending) return;
    const next = chats.filter((chat) => chat.id !== id);
    setChats(next);
    if (id === activeId) {
      setActiveId(next[0]?.id ?? null);
      setDraft("");
      setError(null);
    }
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    setError(null);
    setDraft("");
    const userBubble: Bubble = { id: newId(), role: "user", text: trimmed };
    const existing = activeId && chats.some((chat) => chat.id === activeId) ? activeId : newId();
    const created = existing !== activeId;
    const prior = chats.find((chat) => chat.id === existing)?.messages ?? [];
    const withUser = [...prior, userBubble];
    if (created) {
      const chat: Chat = {
        id: existing,
        title: titleFrom(withUser),
        updatedAt: Date.now(),
        messages: withUser,
      };
      setChats((current) => [chat, ...current].slice(0, 40));
      setActiveId(existing);
    } else {
      putMessages(
        existing,
        withUser,
        prior.some((message) => message.role === "user") ? undefined : titleFrom(withUser),
      );
    }
    setPending(true);

    const turns: ChatTurn[] = withUser.slice(-8).map((message) => ({
      role: message.role,
      content: message.text,
    }));

    try {
      const result = await replyInDzongkha({ data: { messages: turns } });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      putMessages(existing, [
        ...withUser,
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

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-ink">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              className="inline-flex min-h-11 items-center rounded-lg px-2 text-sm font-medium lg:hidden"
              onClick={() => setListOpen((open) => !open)}
            >
              Chats
            </button>
            <div className="min-w-0">
              <p className="text-xs font-semibold tracking-widest text-saffron uppercase">Bhutan</p>
              <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Druk Kha</h1>
            </div>
          </div>
          <button
            type="button"
            onClick={startChat}
            disabled={pending}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-ink px-3 text-sm font-medium text-surface disabled:opacity-40"
          >
            <MessageSquarePlus className="size-4" aria-hidden="true" />
            New chat
          </button>
        </div>
      </header>

      <div className="mx-auto grid min-h-0 w-full max-w-5xl flex-1 grid-cols-1 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside
          className={
            (listOpen ? "block" : "hidden") +
            " border-b border-line px-4 py-4 lg:block lg:border-r lg:border-b-0 lg:px-4 lg:py-6"
          }
        >
          <p className="text-xs font-semibold tracking-widest text-muted uppercase">Saved chats</p>
          {chats.length === 0 ? (
            <p className="mt-3 text-sm text-muted">Your chats stay on this computer.</p>
          ) : (
            <ul className="mt-3 space-y-1">
              {chats.map((chat) => {
                const selected = chat.id === activeId;
                return (
                  <li key={chat.id} className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => openChat(chat.id)}
                      className={
                        "min-w-0 flex-1 truncate rounded-xl px-3 py-2.5 text-left text-sm disabled:opacity-50 " +
                        (selected ? "bg-ink text-surface" : "hover:bg-surface")
                      }
                    >
                      {chat.title}
                    </button>
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => removeChat(chat.id)}
                      className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg text-muted hover:text-lacquer disabled:opacity-40"
                      aria-label={`Delete ${chat.title}`}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
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
                    "relative h-5 w-9 rounded-full transition " + (guide ? "bg-saffron" : "bg-line")
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
              <p>{chats.length === 0 ? "Nothing saved yet" : `${chats.length} saved`}</p>
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
      <p className="font-dzongkha text-4xl leading-tight text-balance sm:text-5xl">
        སྐུ་གཟུགས་བཟང་པོ་ལགས།
      </p>
      <p className="mt-2 text-sm text-muted">Kuzuzangpo la — hello.</p>
      <p className="mt-4 max-w-md text-pretty text-ink">
        Type anything in English. Druk Kha answers in Bhutanese Dzongkha. Each conversation is
        saved on this computer until you delete it.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
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
