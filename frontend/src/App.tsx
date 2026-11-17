import { AuthForm } from "./components/AuthForm";
import { Board } from "./components/Board";
import { GamePage } from "./components/GamePage";
import { useAuth } from "./auth/auth-context";
import type { Grid } from "./api/types";

// Декоративная доска на экране входа: сыгранная вничью партия.
const SHOWCASE: Grid = [
  [1, -1, 1],
  [0, -1, 0],
  [0, 1, 0],
];

export default function App() {
  const { status, user, logout } = useAuth();

  if (status === "loading") {
    return (
      <div className="page page-center">
        <p className="hint">Загрузка…</p>
      </div>
    );
  }

  if (status === "authenticated" && user !== null) {
    return <GamePage user={user} onLogout={logout} />;
  }

  return (
    <div className="page page-center">
      <main className="welcome">
        <h1 className="title">Крестики-нолики</h1>
        <div className="showcase" aria-hidden="true">
          <Board grid={SHOWCASE} />
        </div>
        <AuthForm />
      </main>
    </div>
  );
}
