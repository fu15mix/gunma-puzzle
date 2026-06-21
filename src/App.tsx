import { useEffect, useMemo, useState } from "react";
import PuzzleBoard from "./components/PuzzleBoard";
import { initialPieces, type Piece } from "./data/pieces";

type TimerStatus = "idle" | "running" | "finished";

type RankingEntry = {
  id: string;
  elapsedMs: number;
  playedAt: string;
};

const LEADERBOARD_KEY = "gunma-puzzle-leaderboard";
const MAX_RANKING_COUNT = 5;

function shufflePieces(pieces: Piece[]): Piece[] {
  const nextPieces = [...pieces];

  for (let index = nextPieces.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [nextPieces[index], nextPieces[randomIndex]] = [
      nextPieces[randomIndex],
      nextPieces[index],
    ];
  }

  return nextPieces;
}

function resetPieces(): Piece[] {
  return shufflePieces(initialPieces.map((piece) => ({ ...piece })));
}

function formatElapsed(elapsedMs: number): string {
  const totalSeconds = Math.floor(elapsedMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const tenths = Math.floor((elapsedMs % 1000) / 100);

  return `${minutes}:${String(seconds).padStart(2, "0")}.${tenths}`;
}

function loadLeaderboard(): RankingEntry[] {
  try {
    const rawEntries = window.localStorage.getItem(LEADERBOARD_KEY);
    if (!rawEntries) {
      return [];
    }

    const parsedEntries = JSON.parse(rawEntries);
    if (!Array.isArray(parsedEntries)) {
      return [];
    }

    return parsedEntries
      .filter(
        (entry): entry is RankingEntry =>
          typeof entry?.id === "string" &&
          typeof entry?.elapsedMs === "number" &&
          typeof entry?.playedAt === "string",
      )
      .sort((a, b) => a.elapsedMs - b.elapsedMs)
      .slice(0, MAX_RANKING_COUNT);
  } catch {
    return [];
  }
}

function saveLeaderboard(entries: RankingEntry[]) {
  try {
    window.localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(entries));
  } catch {
    // Private browsing or strict storage settings can block saving scores.
  }
}

function createResultId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export default function App() {
  const [pieces, setPieces] = useState<Piece[]>(() => resetPieces());
  const [timerStatus, setTimerStatus] = useState<TimerStatus>("idle");
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [leaderboard, setLeaderboard] = useState<RankingEntry[]>(() =>
    loadLeaderboard(),
  );
  const [latestResultId, setLatestResultId] = useState<string | null>(null);

  const placedCount = useMemo(
    () => pieces.filter((piece) => piece.placed).length,
    [pieces],
  );
  const isCleared = useMemo(
    () => pieces.every((piece) => piece.placed),
    [pieces],
  );
  const bestTime = leaderboard[0]?.elapsedMs ?? null;

  useEffect(() => {
    if (timerStatus !== "running" || startedAt === null) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAt);
    }, 100);

    return () => window.clearInterval(intervalId);
  }, [startedAt, timerStatus]);

  useEffect(() => {
    if (!isCleared || timerStatus !== "running" || startedAt === null) {
      return;
    }

    const finalElapsedMs = Date.now() - startedAt;
    const result: RankingEntry = {
      id: createResultId(),
      elapsedMs: finalElapsedMs,
      playedAt: new Date().toISOString(),
    };
    const nextLeaderboard = [...leaderboard, result]
      .sort((a, b) => a.elapsedMs - b.elapsedMs)
      .slice(0, MAX_RANKING_COUNT);

    setElapsedMs(finalElapsedMs);
    setTimerStatus("finished");
    setLatestResultId(result.id);
    setLeaderboard(nextLeaderboard);
    saveLeaderboard(nextLeaderboard);
  }, [isCleared, leaderboard, startedAt, timerStatus]);

  const handleGameStart = () => {
    if (timerStatus !== "idle") {
      return;
    }

    setStartedAt(Date.now());
    setElapsedMs(0);
    setTimerStatus("running");
    setLatestResultId(null);
  };

  const handleReset = () => {
    setPieces(resetPieces());
    setTimerStatus("idle");
    setStartedAt(null);
    setElapsedMs(0);
    setLatestResultId(null);
  };

  return (
    <main className="app">
      <section className="app-card">
        <header className="app-header">
          <div>
            <p className="eyebrow">こどもとあそべる Web パズル</p>
            <h1>ぐんま市町村パズル</h1>
          </div>

          <div className="status-panel">
            <p className="status-count timer-count">
              タイム <strong>{formatElapsed(elapsedMs)}</strong>
            </p>
            <p className="status-count best-count">
              ベスト{" "}
              <strong>
                {bestTime === null ? "--:--.-" : formatElapsed(bestTime)}
              </strong>
            </p>
            <p className="status-count">
              正解 <strong>{placedCount}</strong> / {pieces.length}
            </p>
            <button
              type="button"
              className="reset-button"
              onClick={handleReset}
            >
              リセット
            </button>
          </div>
        </header>

        {isCleared ? (
          <div className="clear-banner" aria-live="polite">
            クリア！ タイム {formatElapsed(elapsedMs)}
          </div>
        ) : null}

        <section className="ranking-panel" aria-label="タイム順位">
          <h2>タイム順位</h2>
          {leaderboard.length === 0 ? (
            <p className="ranking-empty">まだ記録なし</p>
          ) : (
            <ol className="ranking-list">
              {leaderboard.map((entry, index) => (
                <li
                  key={entry.id}
                  className={entry.id === latestResultId ? "is-latest" : ""}
                >
                  <span>{index + 1}位</span>
                  <strong>{formatElapsed(entry.elapsedMs)}</strong>
                </li>
              ))}
            </ol>
          )}
        </section>

        <PuzzleBoard
          pieces={pieces}
          onPiecesChange={setPieces}
          onGameStart={handleGameStart}
        />
      </section>
    </main>
  );
}
