import { useEffect, useRef, useState } from "react";
import type { GeneratedDeskView } from "../types/desk";
import { ASK_PROMPTS, askQwen, type AskReply } from "../lib/askDesk";

interface AskDeskProps {
  view: GeneratedDeskView;
}

export function AskDesk({ view }: AskDeskProps) {
  const [question, setQuestion] = useState(ASK_PROMPTS[0]);
  const [reply, setReply] = useState<AskReply | null>(null);
  const [thinking, setThinking] = useState(false);
  const [asked, setAsked] = useState("");
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => () => pending.current?.abort(), []);

  function submit(next?: string) {
    const q = (next ?? question).trim();
    if (!q) return;
    setQuestion(q);
    setAsked(q);
    setReply(null);
    setError(null);

    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setThinking(true);
    void askQwen(view, q, controller.signal).then((qwen) => {
      if (controller.signal.aborted) return;
      if ("reply" in qwen) setReply(qwen.reply);
      else setError(qwen.error);
      setThinking(false);
    });
  }

  return (
    <section className="panel-card ask-desk chapter" id="ask">
      <p className="eyebrow">Ask</p>
      <p className="section-hint">Ask Qwen about this desk</p>

      <div className="ask-prompts">
        {ASK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="ask-chip"
            onClick={() => submit(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>

      <form
        className="ask-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask the desk…"
          aria-label="Desk question"
        />
        <button type="submit" className="btn btn-dark">
          Ask
        </button>
      </form>

      {thinking ? <p className="ask-thinking">Asking Qwen…</p> : null}

      {error ? (
        <article className="ask-reply">
          <p className="ask-q">{asked}</p>
          <p className="ask-a">Qwen could not answer this one. Try again in a moment.</p>
          <p className="ask-cites">{error}</p>
        </article>
      ) : null}

      {reply ? (
        <article className="ask-reply">
          <p className="ask-q">{reply.question}</p>
          <p className="ask-a">{reply.answer}</p>
          <p className="ask-cites">
            Answered by Qwen ({reply.model ?? "Model Studio"})
          </p>
          <p className="ask-cites ask-source">from desk objects only</p>
        </article>
      ) : null}
    </section>
  );
}
