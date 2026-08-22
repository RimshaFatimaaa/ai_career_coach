import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 text-ink">
      <Link href="/" className="text-sm text-copper">
        ← Atelier
      </Link>
      <h1 className="mt-6 font-display text-4xl">Terms of service</h1>
      <p className="mt-4 text-sm leading-relaxed text-mist">
        Atelier is an AI career coaching product. It helps you build a profile, generate resumes, and practise
        interviews. It is not a recruiter, employer, or job board, and it does not guarantee interviews or offers.
      </p>
      <h2 className="mt-8 font-display text-2xl">Your account</h2>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        You must provide accurate details and keep your password private. You are responsible for activity on your
        account. You can export or delete your data from Settings at any time.
      </p>
      <h2 className="mt-8 font-display text-2xl">Plans and payments</h2>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        Free, Pro, and Premium have different monthly limits. Upgrading to Pro or Premium requires a valid card. We
        validate the card and do not store the full card number or security code — only the brand and last four digits
        if the plan activates. If a payment processor such as Stripe is connected, charges are handled by that
        processor. Downgrading to Free requires your account password.
      </p>
      <h2 className="mt-8 font-display text-2xl">AI output</h2>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        Coaching, resumes, scores, and interview feedback are estimates for personal use. Do not treat them as hiring
        decisions or professional legal or immigration advice. Do not paste secrets or other people’s private
        information into the product.
      </p>
      <h2 className="mt-8 font-display text-2xl">Acceptable use</h2>
      <p className="mt-3 text-sm leading-relaxed text-mist">
        Do not use Atelier to impersonate others, fabricate credentials you then present as fact, attack the service, or
        scrape it. We may suspend accounts that abuse limits or harm other users.
      </p>
      <p className="mt-8 text-sm text-mist">
        See also the{" "}
        <Link href="/privacy" className="text-copper">
          privacy note
        </Link>
        .
      </p>
    </div>
  );
}
