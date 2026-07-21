import { useState } from "react";
import axios, { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { Rocket } from "lucide-react";
import { API_BASE } from "../types";
import { setOrganizerToken } from "../lib/auth";

const INPUT_CLASS =
  "w-full rounded-md border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-50 " +
  "placeholder:text-zinc-500 focus:border-teal-500 focus:outline-none " +
  "focus:ring-1 focus:ring-teal-500";

const LABEL_CLASS = "mb-1 block text-sm font-medium text-zinc-300";

export default function OrganizerLogin() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const path =
        mode === "login" ? "/api/auth/organizer/login" : "/api/auth/organizer/register";
      const body =
        mode === "login" ? { email, password } : { name, email, password };
      const res = await axios.post<{ access_token: string }>(
        `${API_BASE}${path}`,
        body,
      );
      setOrganizerToken(res.data.access_token);
      navigate("/admin");
    } catch (err) {
      const ax = err as AxiosError<{ detail?: unknown }>;
      const detail = ax.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Something went wrong. Is the API running on port 8000?",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Rocket className="h-6 w-6 text-teal-400" />
          <span className="text-xl font-semibold text-zinc-50">TruPitch</span>
        </div>

        <div className="rounded-lg border border-white/10 bg-zinc-900 p-6">
          <h1 className="mb-1 text-lg font-semibold text-zinc-50">
            {mode === "login" ? "Organizer sign in" : "Create organizer account"}
          </h1>
          <p className="mb-6 text-sm text-zinc-500">
            {mode === "login"
              ? "Sign in to manage your campaigns."
              : "Register to start running campaigns."}
          </p>

          {error && (
            <div className="mb-4 rounded-md border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label htmlFor="name" className={LABEL_CLASS}>
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>
            )}
            <div>
              <label htmlFor="email" className={LABEL_CLASS}>
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label htmlFor="password" className={LABEL_CLASS}>
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "At least 8 characters" : ""}
                className={INPUT_CLASS}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting
                ? "Please wait…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
            className="mt-4 w-full text-center text-sm text-zinc-500 hover:text-zinc-300"
          >
            {mode === "login"
              ? "Need an account? Register"
              : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
