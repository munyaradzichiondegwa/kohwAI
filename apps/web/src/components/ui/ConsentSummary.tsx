/**
 * Plain-language summary shown wherever someone is asked to accept the Terms & Privacy Policy.
 * This summary is NOT the legal text: link the real documents with NEXT_PUBLIC_TERMS_URL / NEXT_PUBLIC_PRIVACY_URL
 * once they have been reviewed by a lawyer.
 */
const TERMS_URL = process.env.NEXT_PUBLIC_TERMS_URL;
const PRIVACY_URL = process.env.NEXT_PUBLIC_PRIVACY_URL;

export default function ConsentSummary() {
  return (
    <div className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-1.5">
      <p className="font-semibold text-gray-800">What you are agreeing to</p>
      <ul className="list-disc pl-4 space-y-1">
        <li>We keep your phone number, district and the reports, animals and listings you add, to run KohwAI for you.</li>
        <li>You will get <strong>SMS alerts</strong> for your district (drought, pests, disease). You can switch them off any time in Account.</li>
        <li>Your phone number is shown to buyers only if you tick “show my phone” on a listing.</li>
        <li>Community validators in your district see your reports with your number hidden.</li>
        <li>You can download or delete your data any time in Account. We do not sell your data.</li>
      </ul>
      <p>
        {TERMS_URL ? <a className="underline text-brand-green" href={TERMS_URL} target="_blank" rel="noreferrer">Terms of Use</a> : 'Full Terms of Use: available from your Agritex officer'}
        {' · '}
        {PRIVACY_URL ? <a className="underline text-brand-green" href={PRIVACY_URL} target="_blank" rel="noreferrer">Privacy Policy</a> : 'Privacy Policy: available from your Agritex officer'}
      </p>
    </div>
  );
}
