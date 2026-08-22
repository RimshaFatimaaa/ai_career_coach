import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 text-ink">
      <Link href="/" className="text-sm text-copper">
        ← Atelier
      </Link>
      <h1 className="mt-6 font-display text-4xl">Privacy</h1>
      <p className="mt-4 text-sm leading-relaxed text-mist">
        AI Career Coach stores your profile, resumes, interview answers, and optional career memory so the product can
        remember you across sessions. You can export or delete this data from Settings at any time.
      </p>
      <h2 className="mt-8 font-display text-2xl">AI providers</h2>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        Model calls are made from our backend only. The MVP uses OpenAI (Chat Completions and embeddings) when an API
        key is configured. Prompts include your profile, pasted job descriptions, and interview answers so the model can
        coach you. We do not send provider API keys to the browser.
      </p>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        Whether OpenAI uses API data to train its models depends on your OpenAI account and their current policy. Check
        OpenAI’s data-usage terms for API customers. Do not paste secrets or other people’s private information into
        chats, resumes, or job descriptions.
      </p>
      <h2 className="mt-8 font-display text-2xl">What we do not do</h2>
      <ul className="mt-3 list-disc pl-5 text-sm text-mist">
        <li>We do not scrape job boards.</li>
        <li>Readiness and ATS scores are estimates for personal tracking, not hiring guarantees.</li>
        <li>Admins do not automatically receive private resume files.</li>
        <li>We do not store full card numbers or security codes. Paid plans keep only brand and last four digits.</li>
      </ul>
      <p className="mt-8 text-sm text-mist">
        See also the{" "}
        <Link href="/terms" className="text-copper">
          terms of service
        </Link>
        .
      </p>
    </div>
  );
}
