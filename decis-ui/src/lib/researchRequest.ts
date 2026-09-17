const RESEARCH_INBOX = "iaacontact2026@gmail.com";

export type MailProvider = "gmail" | "outlook" | "default";

export interface ResearchRequestResult {
  ok: boolean;
  symbol: string;
  etaDays: number;
  inbox: string;
  mailed: boolean;
  at: string;
  provider: MailProvider;
}

function messageParts(symbol: string): { subject: string; body: string } {
  return {
    subject: `Decis research request: ${symbol}`,
    body: [
      `Please build a Decis research package for: ${symbol}`,
      "",
      "Expected turnaround: up to 3 days.",
      "Source: Decis Analysis desk UI",
    ].join("\n"),
  };
}

export function composeUrl(symbol: string, provider: MailProvider): string {
  const normalized = symbol.trim().toUpperCase().replace(/\s+/g, "");
  const { subject, body } = messageParts(normalized);
  const to = RESEARCH_INBOX;

  if (provider === "gmail") {
    return (
      "https://mail.google.com/mail/?view=cm&fs=1" +
      `&to=${encodeURIComponent(to)}` +
      `&su=${encodeURIComponent(subject)}` +
      `&body=${encodeURIComponent(body)}`
    );
  }

  if (provider === "outlook") {
    return (
      "https://outlook.office.com/mail/deeplink/compose" +
      `?to=${encodeURIComponent(to)}` +
      `&subject=${encodeURIComponent(subject)}` +
      `&body=${encodeURIComponent(body)}`
    );
  }

  return (
    `mailto:${to}` +
    `?subject=${encodeURIComponent(subject)}` +
    `&body=${encodeURIComponent(body)}`
  );
}

/** Open the chosen mail compose window — user hits Send from their account. */
export async function submitResearchRequest(
  symbol: string,
  provider: MailProvider,
): Promise<ResearchRequestResult> {
  const normalized = symbol.trim().toUpperCase().replace(/\s+/g, "");
  const url = composeUrl(normalized, provider);

  if (provider === "default") {
    window.location.href = url;
  } else {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return {
    ok: true,
    symbol: normalized,
    etaDays: 3,
    inbox: RESEARCH_INBOX,
    mailed: true,
    at: new Date().toISOString(),
    provider,
  };
}

export { RESEARCH_INBOX };

/** True when the requested symbol is already on the Focus rToken bar. */
export function isResearchSymbolReady(
  symbol: string,
  instruments: Array<{ ticker: string; token: string }>,
): boolean {
  const normalized = symbol.trim().toUpperCase().replace(/\s+/g, "");
  if (!normalized) return false;
  const tickers = new Set(instruments.map((item) => item.ticker.toUpperCase()));
  const tokens = new Set(instruments.map((item) => item.token.toUpperCase()));
  const bare = normalized.replace(/^R/, "").replace(/USDT$/, "");
  return (
    tickers.has(normalized) ||
    tokens.has(normalized) ||
    tokens.has(`R${normalized}USDT`) ||
    tokens.has(`R${bare}USDT`) ||
    tickers.has(bare)
  );
}
