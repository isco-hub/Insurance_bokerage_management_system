import { Link } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="page">
      <div className="empty-state content-card not-found">
        <Compass size={36} />
        <h1>Page not found</h1>
        <p>The page you are looking for does not exist or has been moved.</p>
        <Link to="/dashboard" className="btn btn-primary">
          <ArrowLeft size={16} /> Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default NotFoundPage;
