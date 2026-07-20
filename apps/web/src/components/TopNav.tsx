import { Link } from "react-router-dom";
import { Rocket } from "lucide-react";

export default function TopNav() {
  return (
    <header className="border-b border-white/10 bg-zinc-950">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-teal-400" />
          <span className="text-lg font-semibold text-zinc-50">TruPitch</span>
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            to="/admin"
            className="text-sm font-medium text-zinc-400 hover:text-zinc-50"
          >
            Organizer Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}
