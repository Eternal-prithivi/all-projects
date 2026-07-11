import { Navigate, useSearchParams } from 'react-router-dom';

/** Legacy dashboard route — unified help hub at /help */
export default function SupportPage() {
  const [searchParams] = useSearchParams();
  const next = new URLSearchParams(searchParams);
  next.set('tab', 'tickets');
  const query = next.toString();
  return <Navigate to={`/help?${query}`} replace />;
}
