import React from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="py-20 text-center space-y-4">
      <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h2 className="text-xl font-bold text-zinc-100">Page Not Found</h2>
      <p className="text-sm text-zinc-500 max-w-sm mx-auto">
        The requested route does not exist in this application.
      </p>
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-emerald-400 hover:text-emerald-300 font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
};
