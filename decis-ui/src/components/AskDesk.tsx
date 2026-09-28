import { useEffect, useRef, useState } from "react";
import type { GeneratedDeskView } from "../types/desk";
import { ASK_PROMPTS, askDesk, askQwen, type AskReply } from "../lib/askDesk";

interface AskDeskProps {
  view: GeneratedDeskView;
}

export function AskDesk({ view }: AskDeskProps) {
  const [question, setQuestion] = useState(ASK_PROMPTS[0]);
  const [reply, setReply] = useState<AskReply | null>(null);
  const [thinking, setThinking] = useState(false);
  const [qwenError, setQwenError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => () => pending.current?.abort(), []);

  function submit(next?: string) {
    const q = (next ?? question).trim();
    if (!q) return;
    setQuestion(q);
    // Deterministic answer first; Qwen replaces it only if it answers.
    setReply({ ...askDesk(view, q), source: "desk" });

    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setThinking(true);
    setQwenError(null);
    void askQwen(view, q, controller.signal).then((qwen) => {
      if (controller.signal.aborted) return;
      if ("reply" in qwen) setReply(qwen.reply);
      else setQwenError(qwen.error);
      setThinking(false);
    });
  }

  return (
    <section className="panel-card ask-desk chapter" id="ask">
      <p className="eyebrow">Ask</p>
      <p className="section-hint">Query the structured desk, with cites</p>

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

      {reply ? (
        <article className="ask-reply">
          <p className="ask-q">{reply.question}</p>
          <p className="ask-a">{reply.answer}</p>
          {reply.cites.length ? (
            <p className="ask-cites">Cites: {reply.cites.join(" · ")}</p>
          ) : null}
          <p className="ask-cites">
            {reply.source === "qwen"
              ? `Answered by Qwen (${reply.model ?? "Model Studio"}) from desk objects only`
              : thinking
                ? "Desk template · asking Qwen…"
                : qwenError
                  ? `Desk template · Qwen not used: ${qwenError}`
                  : "Desk template"}
          </p>
        </article>
      ) : null}
    </section>
  );
}
